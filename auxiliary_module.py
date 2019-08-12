"""
author: Rafal Miecznik
contact: ravmiecznk@gmail.com
"""

from setup_emubt import info, debug, error, warn

def null_function(*args, **kwargs):
    debug("args: {}, kwargs: {}".format(args, kwargs))