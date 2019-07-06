"""
author: Rafal Miecznik
contact: ravmiecznk@gmail.com
"""

from bin_handler import bin_repr
from my_gui_thread import GuiThread, thread_this_method
from io import BytesIO
import os


class BinFile(BytesIO):
    def __init__(self, *args, **kwargs):
        BytesIO.__init__(self, *args, **kwargs)
        self.seek(0)

    def __repr__(self):
        return bin_repr(self)


class BinTracker(file):

    def __init__(self, file_path):
        file.__init__(self, file_path, 'rb')
        self.file_path = file_path
        self.current_file_state = BinFile(self.read())
        self.__mtime = os.path.getmtime(self.file_path)
        self.track_file().start()


    @thread_this_method(period=0.5)
    def track_file(self):
        if self.__mtime != os.path.getmtime(self.file_path):
            self.__mtime = os.path.getmtime(self.file_path)
            self.file_changed_procedure()

    def check_diffs(self):
        addr = 0
        self.seek(0)
        self.current_file_state.seek(0)
        for a, b in zip(self.current_file_state.read(), self.read()):
            if a != b:
                print "{:04X}: {:02X} -> {:02X} | {} - {}".format(addr, ord(a), ord(b), a, b)
            addr += 1
        print
        self.seek(0)
        self.current_file_state = BinFile(self.read())

    def file_changed_procedure(self):
        self.check_diffs()


    def __repr__(self):
        return bin_repr(self)



