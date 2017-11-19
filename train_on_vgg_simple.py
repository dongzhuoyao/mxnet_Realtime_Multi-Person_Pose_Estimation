#encoding=utf-8

'''
Created on Nov 18, 2017

@author: kohill
'''
from __future__ import print_function
from modelCPM import *
from config.config import config
from log import log_init
import logging
log_init("vgg.log")
import mxnet as mx
from pprint import pprint

def get_module(prefix ,
               batch_size = 24, 
               start_epoch = 0,
               reinit = False,
               gpus = [4,7]):
    sym = poseSymbol()
    if reinit:        
        _,args_vgg,auxes_vgg = mx.model.load_checkpoint("/data1/yks/models/vgg19/vgg19" , epoch=0)
        args = {}
        auxes = {}
        for ikey in config.TRAIN.vggparams:
            args[ikey] = args_vgg[ikey]
    else:
        _,args,auxes = mx.model.load_checkpoint(prefix , epoch=start_epoch)        
    model = mx.mod.Module(symbol=sym, context=[mx.gpu(g) for g in gpus],
                                  label_names=['heatmaplabel',
                                 'partaffinityglabel',
                                 'heatweight',
                                 'vecweight']
                          )
    model.bind(data_shapes=[('data', (batch_size, 3, 368, 368))], label_shapes=[
                            ('heatmaplabel', (batch_size, 19, 46, 46)),
                            ('partaffinityglabel', (batch_size, 38, 46, 46)),
                            ('heatweight', (batch_size, 19, 46, 46)),
                            ('vecweight', (batch_size, 38, 46, 46))])
    model.init_params(arg_params=args, aux_params=auxes, allow_missing=True,allow_extra = True)
    return model
def train(cmodel,train_data,begin_epoch,end_epoch,batch_size,save_prefix,single_train_count = 4,ndataset = 99,val_data_batch = None):
    cmodel.init_optimizer(optimizer='sgd', 
                        optimizer_params=(('learning_rate', 0.00004 ), )
                          )     
    for n_data_wheel in range(ndataset):  
        cmodel.save_checkpoint(save_prefix + "final", n_data_wheel)
        train_data.reset()
        for nbatch,data_batch in enumerate(train_data):
            current_batch = begin_epoch + nbatch
            logging.info("{0}/{1}-{2}".format(n_data_wheel,ndataset,nbatch))
            if current_batch >= end_epoch:
                print("info: finish training.")
                return
            if nbatch % 100 == 0:
                cmodel.save_checkpoint(save_prefix, current_batch)
                print ("save_checkpoint finished")
            if nbatch % 10 != 0:
                for _ in range(single_train_count):
                    cmodel.forward(data_batch, is_train=True) 
                    cmodel.backward()  
                    cmodel.update()
            else:
                cmodel.forward(data_batch, is_train=True)       # compute predictions  
                prediction=cmodel.get_outputs()
                print(current_batch,end_epoch)
                for i in range(len(prediction)):
                    loss = mx.nd.sum(prediction[i]).asnumpy()[0]
                    print(loss,end = " ")
                print("")
                for _ in range(single_train_count):
                    cmodel.forward(data_batch, is_train=True) 
                    cmodel.backward()  
                    cmodel.update()        
                cmodel.forward(data_batch, is_train=True)       # compute predictions  
                prediction=cmodel.get_outputs()
                for i in range(len(prediction)):
                    loss = mx.nd.sum(prediction[i]).asnumpy()[0]
                    print(loss,end = " ")
                if val_data_batch:
                    cmodel.forward(val_data_batch, is_train=False) 
                    prediction=cmodel.get_outputs()
                    for i in range(len(prediction)):
                        loss = mx.nd.sum(prediction[i]).asnumpy()[0]
                        print(loss,end = " ")
                print("")

if __name__ == '__main__':
    from multi_core_prefetch_iter import PrefetchIter
    start_epoch = 9900
    batch_size = 10
    number_classes = 36#A-Z,0-9
    save_prefix = "model/vggpose"
    cmodel = get_module(save_prefix,
                        batch_size = batch_size,
                        start_epoch=start_epoch,
                        reinit=False)
    

    cocodata = cocoIterweightBatch('pose_io/data.json',
                                   'data', (batch_size, 3, 368,368),
                                   ['heatmaplabel','partaffinityglabel','heatweight','vecweight'],
                                   [(batch_size, 19, 46, 46), (batch_size, 38, 46, 46),
                                    (batch_size, 19, 46, 46), (batch_size, 38, 46, 46)],
                                   batch_size
                                 )
    #cocodata.cur_batch = start_epoch * batch_size
#     val_iter = cocoIterweightBatch('pose_io/data.json',
#                                    'data', (batch_size, 3, 368,368),
#                                    ['heatmaplabel','partaffinityglabel','heatweight','vecweight'],
#                                    [(batch_size, 19, 46, 46), (batch_size, 38, 46, 46),
#                                     (batch_size, 19, 46, 46), (batch_size, 38, 46, 46)],
#                                    batch_size
#                                  )
#     val_iter.reset()
#     val_data_batch = iter(val_iter).__next__()
    train(cmodel, PrefetchIter( cocodata), start_epoch, 99999, batch_size, save_prefix, 1,99,None)
    
