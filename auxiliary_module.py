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


class MeanCalculator():
    def __init__(self):
        self.__val = float(0)
        self.__cnt = 0

    def count(self, val):
        self.__val += val
        self.__cnt += 1

    def calc(self):
        try:
            return self.__val/self.__cnt
        except ZeroDivisionError:
            return 0

    def __add__(self, other):
        self.count(other)
        return self

    def __repr__(self):
        return "Mean {}".format(self.calc())

if __name__ == "__main__":
    c = MeanCalculator()
    c += 1
    c += 2
    print c