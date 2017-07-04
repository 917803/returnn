

from __future__ import print_function

import numpy
import sys
import os
import tornado.web
from tornado.ioloop import IOLoop
from tornado import gen
import Engine
import hashlib
import Config
import json
from Log import log
import urllib
import datetime
from GeneratingDataset import StaticDataset
from Device import Device, get_num_devices, TheanoFlags, getDevicesInitArgs
import time
from EngineTask import ClassificationTaskThread
from tornado.concurrent import run_on_executor
from concurrent.futures import ThreadPoolExecutor


_engines = {}
_devices = {}
_classify_cache = {}


class Server:

    def __init__(self, global_config):
        """
            :type devices: list[Device.Device]
        """
    
        application = tornado.web.Application([
          (r"/classify", ClassifyHandler),
          (r"/loadconfig", ConfigHandler)
        ], debug=True)
        
        application.listen(int(global_config.value('port', '3033')))
        
        print("Starting server on port: " + global_config.value('port', '3033'), file=log.v3)
        IOLoop.instance().start()


class ClassifyHandler(tornado.web.RequestHandler):
    
    MAX_WORKERS = 4
    executor = ThreadPoolExecutor(max_workers=MAX_WORKERS)
    
    @run_on_executor
    def classification_task(self, network, devices, data, batches):
        #This will be executed in `executor` pool
        td = ClassificationTaskThread(network, devices, data, batches)
        td.join()
        return td

    @tornado.web.asynchronous
    @tornado.gen.coroutine
    def post(self, *args, **kwargs):
        #TODO: Make this batch over a specific time period
    
        params = json.loads(self.request.body)
        output_dim = {}
        ret = {}
        
        #first get meta data
        engine_hash = params['engine_hash']
        
        print('Received engine hash: ', engine_hash, file=log.v4)
        
        #delete unneccessary stuff so that the rest works
        del params['engine_hash']
        
        #load in engine and hash
        engine = _engines[engine_hash]
        network = engine.network
        devices = _devices[engine_hash]
        
        hash_engine = hashlib.new('ripemd160')
        hash_engine.update(json.dumps(params) + engine_hash)
        hash_temp = hash_engine.hexdigest()
        
        #process the data
        for k in params:
            try:
                params[k] = numpy.asarray(params[k], dtype='float32')
                if k != 'data':
                  output_dim[k] = network.n_out[k]  # = [network.n_in,2] if k == 'data' else network.n_out[k]
            except Exception:
                if k != 'data' and not k in network.n_out:
                    ret['error'] = 'unknown target: %s' % k
                else:
                    ret['error'] = 'unable to convert %s to an array from value %s' % (k, str(params[k]))
                break
        if not 'error' in ret:
            try:
                data = StaticDataset(data=[params], output_dim=output_dim)
                data.init_seq_order()
            except Exception:
                ret['error'] = 'Dataset server error'
                self.write(ret)
                pass
            else:
                batches = data.generate_batches(recurrent_net=network.recurrent,
                                                batch_size=sys.maxsize, max_seqs=1)
                if not hash_temp in _classify_cache:
                    print('Starting classification', file=log.v3)
                    #if we haven't yet processed this exact request, and saved it in the cache
                    _classify_cache[hash_temp] = yield self.classification_task(network=network,
                                                                                devices=devices,
                                                                                data=data, batches=batches)

                ret = {'result':
                     {k: _classify_cache[hash_temp].result[k].tolist() for k in _classify_cache[hash_temp].result}}
        
        print("Finished processing classification with ID: ", hash_temp, file=log.v4)
        
        self.write(ret)
        

    
    

#EXAMPLE: curl -H "Content-Type: application/json" -X POST -d '{"new_config_url":"file:///home/nikita/Desktop/returnn-experiments-master/mnist-beginners/config/ff_3l_sgd.config"}' http://localhost:3033/loadconfig
class ConfigHandler(tornado.web.RequestHandler):

    def get(self):
        pass
    
    #not async and blocking, as it is a critical operation
    def post(self, *args, **kwargs):

        #TODO: Add cleanup of old unused engines
    
        data = json.loads(self.request.body)
    
        #for d in data:
        #  print('Data: ', d, file=log.v3)
    
        print('Received new config for new engine', file=log.v3)
    
        #Overview: create engine, download full config, create hash, and add it to the main list
        
        # generate ID
        hash_engine = hashlib.new('ripemd160')
        hash_engine.update(json.dumps(args) + str(datetime.datetime.now()))
        hash_temp = hash_engine.hexdigest()

        # download new config file
        urlmanager = urllib.URLopener()
        config_file = str(datetime.datetime.now()) + ".config"
        urlmanager.retrieve(data["new_config_url"], config_file)
        
        # load and setup config
        config = Config.Config()
        config.load_file(config_file)
        config.set(key='task', value='daemon') #assume we're currently using only for online classification
        
        #load devices
        _devices[hash_temp] = self.init_devices(config=config)
        
        #load engine
        new_engine = Engine.Engine(_devices[hash_temp])
        new_engine.init_network_from_config(config=config)
        _engines[hash_temp] = new_engine
        
        print("Finished loading in, server running. Currently number of active engines: ", len(_engines), file=log.v3)
        
        self.write(hash_temp)
    
    
    def init_devices(self, config):
        
        #very basic and hacky
        #TODO: make this closer to rnn.py version, as in make it a function in rnn.py which isn't bound to the local vars of rnn.py (?)
        
        oldDeviceConfig = ",".join(config.list('device', ['default']))
        if "device" in TheanoFlags:
          # This is important because Theano likely already has initialized that device.
          config.set("device", TheanoFlags["device"])
          print("Devices: Use %s via THEANO_FLAGS instead of %s." % \
                (TheanoFlags["device"], oldDeviceConfig), file=log.v4)
        devArgs = getDevicesInitArgs(config)
        assert len(devArgs) > 0
        devices = [Device(**kwargs) for kwargs in devArgs]
        for device in devices:
          while not device.initialized:
            time.sleep(0.25)
        if devices[0].blocking:
          print("Devices: Used in blocking / single proc mode.", file=log.v4)
        else:
          print("Devices: Used in multiprocessing mode.", file=log.v4)
        return devices

#TODO: implement training handler








