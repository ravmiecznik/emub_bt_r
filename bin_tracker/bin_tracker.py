"""
author: Rafal Miecznik
contact: ravmiecznk@gmail.com
"""

from bin_handler import bin_repr

class BinTracker(file):

    def __init__(self, file_path):
        file.__init__(self, file_path, 'rb')

    def __repr__(self):
        return bin_repr(self)



