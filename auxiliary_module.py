"""
author: Rafal Miecznik
contact: ravmiecznk@gmail.com
"""

from setup_emubt import info, debug, error, warn

def null_function(*args, **kwargs):
    debug("args: {}, kwargs: {}".format(args, kwargs))


class Uint16(int):
    def __init__(self, value, **kwargs):
        int.__init__(self, value % 0xffff, **kwargs)

    def __new__(self, value, **kwargs):
        obj = int.__new__(self, value % 0xffff, **kwargs)
        return obj

    def __add__(self, other):
        return Uint16(int.__add__(self, other))

    def __sub__(self, other):
        return Uint16(int.__sub__(self, other))

    def __mul__(self, other):
        return Uint16(int.__mul__(self, other))

    def __div__(self, other):
        return Uint16(int.__div__(self, other))

if __name__ == "__main__":
    i = Uint16(0xfffd)
    i += 1
    i *= 67
    print i