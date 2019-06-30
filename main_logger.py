"""
author: Rafal Miecznik
contact: ravmiecznk@gmail.com
"""

import time, sys
import logging
import os

EMU_BT_PATH = '/home/rafal/EMU_BTR_FILES'
os.chdir(EMU_BT_PATH)
print os.getcwd()

if not os.path.exists(EMU_BT_PATH):
    print("Create emu bt directory: {}".format(EMU_BT_PATH))
    os.makedirs(EMU_BT_PATH)

def tstamp():
    ts = time.localtime()
    ts_ms = time.time()%60
    ts_ms = "{:.3f}".format(ts_ms).zfill(6)
    return "{:02d}:{:02d}:{}:".format(ts.tm_hour, ts.tm_min, ts_ms)

log_format = '[%(asctime)s %(filename)s:%(lineno)d in func:%(funcName)s thr:%(threadName)s]: %(levelname)s %(message)s'

def create_logger(name, format=log_format, log_level=logging.DEBUG, log_to_file=True):
    log_formatter = logging.Formatter(format)
    if log_to_file:
        log_file = '{}.log'.format(name)
        log_file = os.path.join(EMU_BT_PATH, log_file)
        with open(log_file, 'w') as lf:
            lf.write('')
        handler = logging.FileHandler(log_file)
    else:
        handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(log_formatter)

    logger = logging.getLogger(name)
    logger.setLevel(log_level)
    logger.addHandler(handler)
    return logger

class ExceptionLogger():
    def __init__(self, name='main_exceptions'):
        log_format = '[%(asctime)s]: %(levelname)s %(message)s'
        logger_name = name
        self.exception_logger = create_logger(logger_name, log_format, log_to_file=True)

    def write(self, msg):
        self.exception_logger.error(msg)

logger = create_logger("emu_bt", log_format)

info = logger.info
debug = logger.debug
error = logger.error
warn = logger.warn


if __name__ == "__main__":
    pass