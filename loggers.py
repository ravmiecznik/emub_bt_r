"""
author: Rafal Miecznik
contact: ravmiecznk@gmail.com
"""
import logging, time, os, sys

def tstamp():
    ts = time.localtime()
    ts_ms = time.time()%60
    ts_ms = "{:.3f}".format(ts_ms).zfill(6)
    return "{:02d}:{:02d}:{}:".format(ts.tm_hour, ts.tm_min, ts_ms)

log_format = '[%(asctime)s %(filename)s:%(lineno)d in func:%(funcName)s thr:%(threadName)s]: %(levelname)s %(message)s'

def create_logger(name, log_path, format=log_format, log_level=logging.DEBUG, log_to_file=True):
    log_formatter = logging.Formatter(format)
    if log_to_file:
        log_file = '{}.log'.format(name)
        log_file = os.path.join(log_path, log_file)
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
