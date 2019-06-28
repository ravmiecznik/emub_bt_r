"""
author: Rafal Miecznik
contact: ravmiecznk@gmail.com
"""

import os
from io import BytesIO
from main_logger import error, warn, info, debug
from message_handler.crc import crc
import time, struct

class BinSenderFileNotPresent(Exception):
    pass

class BinSenderInvalidBinSize(Exception):
    pass

class PacketReceptionTimeout(Exception):
    pass

class CrcFail(Exception):
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
        self.tot_packests = len(self)
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


class BinReceiver(bytearray):
    """
    rx_buffer must have size at least 0x8000/SPMPAGESIZE/8
    """
    def __init__(self, rx_buffer, file_name, timeout=1):
        bytearray.__init__(self)
        self.__rx_buffer = rx_buffer
        self.__file_name = file_name
        self.__timeout = timeout
        self.__expected_data_amount = 0x8000
        self.__is_image_complete = False
        self.__timeout = 1
        self.__packet_size = 256 * 8 + 2 #plus CRC


    def __iter__(self):
        self.__init__(self.__rx_buffer, self.__file_name, self.__timeout)
        print 100*'#'
        print 10*'\n'
        print 100 * '#'
        return self


    def next(self):
        t0 = time.time()
        while self.__rx_buffer.available() < self.__packet_size:
            time.sleep(0.001)
            if time.time() - t0 > self.__timeout:
                raise PacketReceptionTimeout
        data_received = self.__rx_buffer.read()
        _crc = data_received[-2:]
        data_received = data_received[0:-2]
        print 'crc', _crc == crc(data_received)
        self += data_received
        if len(self) >= self.__expected_data_amount:
            template = 4 * "{:02X} "
            template = "{}  ".format(template)
            template = 4 * template
            index = 0
            line = self[index: index + 16]
            while line:
                print template.format(*list(line)),
                print '\t', line.replace('\n', ' ').replace('\r', ' ')
                index += 16
                line = self[index: index + 16]
            raise StopIteration
