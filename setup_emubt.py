"""
author: Rafal Miecznik
contact: ravmiecznk@gmail.com
"""

import time, sys
import logging
import os
from PyQt4 import QtGui

setup_file = 'emu_bt.stp'

def browse_for_directory():
    app = QtGui.QApplication(sys.argv)
    emu_bt_path = QtGui.QFileDialog.getExistingDirectory(None, 'Select directory')
    open(setup_file, 'w').write(str(emu_bt_path))
    sys.exit(app.exec_())


try:
    EMU_BT_PATH = open(setup_file, 'r').read().strip()
    if not os.path.isdir(EMU_BT_PATH):
        browse_for_directory()
except IOError:
    print browse_for_directory()

LOG_PATH = os.path.join(EMU_BT_PATH, 'DBG')
BIN_PATH = os.path.join(EMU_BT_PATH, 'DOWNLOADED')


if not os.path.exists(LOG_PATH):
    os.makedirs(LOG_PATH)

if not os.path.exists(BIN_PATH):
    os.makedirs(BIN_PATH)

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
        log_file = os.path.join(LOG_PATH, log_file)
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