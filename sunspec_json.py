#!/usr/bin/env python3
from absl import app
from absl import flags
from operator import invert
from pathlib import Path
import datetime
import json
import logging
import os
import sunspec2
import sunspec2.device as device
import sunspec2.modbus.client as client
import sys
import trace
import tempfile
import time
import yaml
import zipfile
import random
import pdb

FLAGS = flags.FLAGS
flags.DEFINE_string("model_dir", None, "directory")


def main(argv):
  del argv

  FORMAT = '%(asctime)s [%(levelname)s] [%(threadName)s] %(message)s'
  logging.basicConfig(format=FORMAT, level=logging.DEBUG)

  config = {}
  with open(os.path.join(sys.path[0], "config.yaml")) as config_file:
    config = yaml.safe_load(config_file)

  with tempfile.TemporaryDirectory() as tempdir:
    logging.debug("Extracting sunspec models to %s", tempdir)
    zf = zipfile.ZipFile(os.path.join(sys.path[0], "sunspec-models.zip"))
    zf.extractall(tempdir)

    # Configure additional model def locations
    device.set_model_defs_path(
        [os.path.join(tempdir, "sunspec-models")] + device.get_model_defs_path())

    found_devices = {}

    model_dir_path = None
    if FLAGS.model_dir is not None:
      model_dir_path = Path(FLAGS.model_dir).expanduser().resolve()
      model_dir_path.mkdir(parents=True, exist_ok=True)
      logging.info("Saving Models to %s", model_dir_path)


    for device_id in config['sunspec']['devices']:
      for mbdev in device_id['modbus']:
          for link_id in mbdev['link_ids']:
            cn = client.SunSpecModbusClientDeviceTCP(
                slave_id=link_id, 
                ipaddr=device_id['ip'], 
                ipport=device_id['port'], 
                timeout=60
            )
            try:
              scan(cn)

              for model_id in config['sunspec']['models'][mbdev['model']]['models']:
                model = cn.models[model_id][0]
                read(model)
                fn = "output/{}-{}-{}.json".format(device_id['name'],link_id,model_id)
                logging.info("writing {}".format(fn))
                with open(fn,"w") as fd:
                  fd.write(model.get_json())
            except Exception as e:
              logging.error("Exception on read: {}".format(e))

def retry_with_backoff(retries = 5, backoff_in_seconds = 1):
    def rwb(f):
        def wrapper(*args, **kwargs):
          x = 0
          while True:
            try:
              return f(*args, **kwargs)
            except:
              if x == retries:
                raise

              sleep = (backoff_in_seconds * 2 ** x +
                       random.uniform(0, 1))
              logging.info("RWB fired, retry {}, sleep {}".format(x,sleep))
              time.sleep(sleep)
              x += 1
                
        return wrapper
    return rwb

@retry_with_backoff(retries=3)
def scan(device_id):
    logging.info("attempting scan of {}:{}-{}".format(device_id.ipaddr,device_id.ipport,device_id.slave_id))
    device_id.scan(full_model_read=False)

@retry_with_backoff(retries=3)
def read(model):
    model.read()


if __name__ == '__main__':
  app.run(main)
