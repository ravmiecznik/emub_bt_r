"""
author: Rafal Miecznik
contact: ravmiecznk@gmail.com
"""
from main_logger import logger, info, debug, error, warn

class DummyEventHandler():
    def __init__(self):
        pass

    def attr_factory(self, attr):
        def print_attr():
            warn("{}: {}: not implemented".format(self.__class__, attr))
        return print_attr

    def __getattr__(self, item):
        return self.attr_factory(item)