"""
author: Rafal Miecznik
contact: ravmiecznk@gmail.com
"""

from bin_handler import bin_repr
from my_gui_thread import GuiThread, thread_this_method
from io import BytesIO
import os
import struct
import time

class BinFile(BytesIO):
    def __init__(self, *args, **kwargs):
        BytesIO.__init__(self, *args, **kwargs)
        self.seek(0)

    def __str__(self):
        return bin_repr(self)

class DiffAddrByte(dict):
    def popitem(self):
        addr, byte = dict.popitem(self)
        return struct.pack('H', addr) + byte

class BinTracker(file):

    def __init__(self, file_path, event_handler, blink_signal = lambda: None):
        file.__init__(self, file_path, 'rb')
        self.file_path = file_path
        self.current_file_state = BinFile(self.read())
        self.__mtime = os.path.getmtime(self.file_path)
        self.event_handler = event_handler
        self.track_file()
        self.diffs = DiffAddrByte()
        self.pages_modified = set()
        self.page_size = 256 * 8
        self.blink_signal = blink_signal

    def start(self):
        self.track_file.start()

    def stop(self):
        self.track_file.terminate()

    def __del__(self):
        self.stop()

    def resume(self):
        self.track_file.resume()

    @thread_this_method(period=0.5)
    def track_file(self):
        if self.__mtime != os.path.getmtime(self.file_path):
            self.__mtime = os.path.getmtime(self.file_path)
            self.file_changed_procedure()
        if self.diffs:
            self.track_file.suspend()
            self.event_handler.emulation_diffs_present_slot.emit()
        self.blink_signal()

    def check_diffs(self):
        addr = 0
        self.seek(0)
        self.current_file_state.seek(0)
        for a, b in zip(self.current_file_state.read(), self.read()):
            if a != b:
                self.diffs[addr] = b
                page_modified = addr/self.page_size
                self.pages_modified.add(page_modified)
            addr += 1
        self.seek(0)
        self.current_file_state = BinFile(self.read())

    def file_changed_procedure(self):
        self.check_diffs()


    def __str__(self):
        return bin_repr(self)



