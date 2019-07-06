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


#class BinSender(BytesIO):
class BinSender(file):
    """
    BinHanlder: handle binary file sending (storing)
    """
    def __init__(self, bin_file, packet_size=256 * 8, expected_size = 0x8000, init_from_buffer=False, crc_attach = False):
        file.__init__(self, bin_file, 'rb')
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
        return bin_repr(self)


class BinReceiver(bytearray):
    """
    rx_buffer must have size at least 0x8000/SPMPAGESIZE/8
    """
    def __init__(self, rx_buffer, timeout=1):
        bytearray.__init__(self)
        self.__rx_buffer = rx_buffer
        self.__timeout = timeout
        self.__expected_data_amount = 0x8000
        self.__is_image_complete = False
        self.__timeout = 1
        self.__packet_size = 256 * 8 + 2 #plus CRC

    def wait_for_packet(self):
        t0 = time.time()
        while self.__rx_buffer.available() < self.__packet_size:
            time.sleep(0.0001)
            if time.time() - t0 > self.__timeout:
                self.__rx_buffer.flush()
                return False
        return True

    def receive_packet(self):
        if self.wait_for_packet():
            data_received = self.__rx_buffer.read(self.__packet_size)
            _crc = data_received[-2:]
            data_received = data_received[0:-2]
            crc_result = _crc == crc(data_received)
            if not crc_result:
                debug("CRC check fail")
                self.__append = False
                raise ReceptionFail
            else:
                self += data_received
                if len(self) >= self.__expected_data_amount:
                    return False
                return True
        else:
            debug("Wait for packet timeout")
            raise ReceptionFail
        self.__rx_buffer.flush()


    def __str__(self):
        template = 4 * "{:02X} "
        template = "{}  ".format(template)
        template = 4 * template
        index = 0
        _str = ''
        line = self[index: index + 16]
        while line:
            _str += "{:04X}:  ".format(index) + template.format(*list(line))
            _str += '\t' + line.replace('\n', ' ').replace('\r', ' ') + '\n'
            index += 16
            line = self[index: index + 16]
        return str(_str)

    def save_bin(self, file_path):
        with open(file_path, 'wb') as f:
            f.write(self)

    def save_hex(self, file_path):
        with open(file_path, 'wb') as f:
            f.write(str(self))

    def reset(self):
        self.__init__(self.__rx_buffer, self.__timeout)

