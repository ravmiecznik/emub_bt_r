"""
author: Rafal Miecznik
contact: ravmiecznk@gmail.com
"""

import os
from io import BytesIO
from setup_emubt import error, warn, info, debug
from message_handler.crc import crc
import time, struct


class BinSenderFileNotPresent(Exception):
    pass


class BinSenderInvalidBinSize(Exception):
    pass


class BinSenderIOPacketSize(Exception):
    pass


class PacketReceptionTimeout(Exception):
    pass


class ReceptionFail(Exception):
    pass


def bin_repr(file_obj):
    """
    :param file_obj: file like object
    :return: string representation
    """
    tell = file_obj.tell()
    file_obj.seek(0)
    col_size = 16
    repr = ''
    cnt = 0
    hex_line_template = col_size/4 * ( (4*' {:02X}') + '  ')
    hex_line = file_obj.read(col_size)
    while hex_line:
        repr += '{:08X}: '.format(cnt)
        repr += hex_line_template.format(*map(ord, hex_line))
        repr += '\n'
        hex_line = file_obj.read(col_size)
        cnt += col_size
    file_obj.seek(tell)
    return repr


class BinFilePacketGeneratorAbstract():
    """
    Abstaract class to create target BinFilePacketGenerator
    """

    def __len__(self):
        tell = self.tell()
        self.seek(0)
        l = len(self.read())
        self.seek(tell)
        return l/self.packet_size

    def __iter__(self):
        self.seek(0)
        return self

    def __getitem__(self, item):
        tell = self.tell()
        self.seek(item * self.packet_size)
        itemget = self.read(self.packet_size)
        self.seek(tell)
        return itemget

    def next(self):
        packet = self.read(self.packet_size)
        if packet:
            self.packets_get += 1
            ret = packet + crc(packet) if self.crc_attach else packet
            return ret
        else:
            raise StopIteration

    def __repr__(self):
        return bin_repr(self)


class BinFilePacketGenerator(BinFilePacketGeneratorAbstract, file):
    """
    Provides iteration protocol for binary file packets
    """
    def __init__(self, bin_file, packet_size=256*8, expected_size=0x8000, crc_attach=False):
        file.__init__(self, bin_file, 'rb')
        self.bin_path = bin_file
        self.packet_size = packet_size
        self.crc_attach = crc_attach
        self.packets_get = 0
        self.packets_amount = len(self)
        if expected_size/self.packet_size and len(self) != expected_size/self.packet_size:
            raise BinSenderInvalidBinSize("Size not match 0x{:X} != 0x{:X}".format(len(self), expected_size/self.packet_size))


class BinFilePacketGeneratorBytesIO(BinFilePacketGeneratorAbstract, BytesIO):
    """
    This is in memory container
    May be used to store nacked packets due to this each written packet size must be checked
    """
    def __init__(self, bytes='', packet_size=256*8, crc_attach=False):
        BytesIO.__init__(self, bytes)
        self.packet_size = packet_size
        self.packets_get = 0
        self.crc_attach = crc_attach

    def write(self, bytes):
        if len(bytes) != self.packet_size:
            raise BinSenderIOPacketSize
        self.write(bytes)


class BinReceiver(dict):
    def __init__(self, packet_size=256*8, expected_size=0x8000):
        self.__packets_num = expected_size/packet_size
        dict.__init__(self, {k: None for k in range(self.__packets_num)})

    def get(self):
        bin_content = ''
        packets = sorted(self.keys())
        for p in packets:
            bin_content += self[p]
        return bin_content

    def __nonzero__(self):
        return all(self.values())



if __name__ == "__main__":
    bs = BinFilePacketGenerator(r'/home/rafal/EMU_BTR_FILES/DOWNLOADED/reveived_bank2.bin')
    bsio = BinFilePacketGeneratorBytesIO(bs[12] + bs[15])
    for i in bsio:
        print BinFilePacketGeneratorBytesIO(i)
        print 20 * '-'