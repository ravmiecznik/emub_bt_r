"""
author: Rafal Miecznik
contact: ravmiecznk@gmail.com
"""

import os
from io import BytesIO
from main_logger import error, warn, info, debug
from message_handler.crc import crc

class BinSenderFileNotPresent(Exception):
    pass

class BinSenderInvalidBinSize(Exception):
    pass

#class BinSender(BytesIO):
class BinSender(file):
    """
    BinHanlder: handle binary file sending (storing)
    """
    def __init__(self, bin_file, packet_size=256 * 8, expected_size = 0x8000, init_from_buffer=False, crc_attach = False):
#        if not init_from_buffer:
#            with open(bin_file, 'rb') as f:
#                BytesIO.__init__(self, f.read())
#        elif init_from_buffer:
#            BytesIO.__init__(self, bin_file)
        file.__init__(self, bin_file, 'rb')
        self.col_size = 16
        self.packet_size = packet_size
        self.crc_attach = crc_attach
        self.packets_get = 0
        if expected_size/self.packet_size and len(self) != expected_size/self.packet_size:
            raise BinSenderInvalidBinSize("Size not match 0x{:X} != 0x{:X}".format(len(self), expected_size/self.packet_size))


    def __len__(self):
        tell = self.tell()
        self.seek(0)
        l = len(self.read())
        self.seek(tell)
        return l/self.packet_size

    def __iter__(self):
        self.seek(0)
        return self

    def next(self):
        packet = self.read(self.packet_size)
        if packet:
            self.packets_get += 1
            ret = packet + crc(packet) if self.crc_attach else packet
            return ret
        else:
            raise StopIteration

    def __repr__(self):
        repr=''
        cnt = 0
        hex_line = self.read(self.col_size)
        while hex_line:
            repr += '{:08X}: '.format(cnt)
            for h in hex_line:
                repr += ' {:02X}'.format(ord(h))
            repr += '\n'
            hex_line = self.read(self.col_size)
            cnt += self.col_size
        return repr
