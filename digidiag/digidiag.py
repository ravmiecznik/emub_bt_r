"""
author: Rafal Miecznik
contact: ravmiecznk@gmail.com
"""

from circ_io_buffer import CircIoBuffer
import time

class DigidiagTimeout(Exception):
    pass


class DigiFrames(dict):
    def __str__(self):
        o = ''
        for frame_id in sorted(self.keys(), reverse=True):
            o += ('{:02X}: ' + 8*' {:02X}' + '\n').format(frame_id, *self[frame_id])
        return o


class DigidagReceiver():
    def __init__(self, raw_rx_buffer):
        self.digidiag_buffer = DigiFrames()
        self.raw_buffer = raw_rx_buffer
        self.id = 0xff
        self.frame_size = 8
        self.__timeout = 1
        self.__frames_received = 0

    def clear_stats(self):
        self.__frames_received = 0

    def frames_received(self):
        return self.__frames_received

    def catch_frame(self, id):
        _id = chr(id)
        t0 = time.time()
        header = '\xf5' + _id
        while header not in self.raw_buffer:
            time.sleep(0.01)
            if time.time() - t0 > self.__timeout:
                raise DigidiagTimeout(self.digidiag_buffer)
        self.raw_buffer.flush_until(header)
        self.digidiag_buffer[id] = [ord(i) for i in self.raw_buffer.read(self.frame_size).ljust(8, '0')]
        self.id -= 1
        self.__frames_received += 1
        if self.id == 0xF9:
            self.id = 0xFF


    def start(self):
        while True:
            self.catch_frame(self.id)






if __name__ == "__main__":
    c = CircIoBuffer(byte_size=2)
    c.write('ab')
    c.write('c')
    print 'ab' in c