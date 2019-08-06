"""
author: Rafal Miecznik
contact: ravmiecznk@gmail.com
"""

from PyQt4.QtCore import pyqtSignal
from event_handler import to_signal, general_signal_factory
import time

def check_with_timeout(timeout=5, expected_res=True):
    def wrapper(method):
        def caller(*args, **kwargs):
            result = method(*args, **kwargs)
            t0 = time.time()
            while result != expected_res:
                result = method(*args, **kwargs)
                time.sleep(0.1)
                if time.time() - t0 > timeout:
                    return False
            return result
        return caller
    return wrapper


class Container():
    pass

class TestInterface():

    def __init__(self, main_window):
        self.parent = main_window
        self.parent.insert_new_file_ti_signal.connect(self.parent.bin_file_panel.insert_new_file)
        self.parent.bank_in_use = None
        self.buttons = Container()
        self.buttons.bank1btn = self.parent.banks_panel.bank1pushButton
        self.buttons.bank2btn = self.parent.banks_panel.bank2pushButton
        self.buttons.bank3btn = self.parent.banks_panel.bank3pushButton
        self.buttons.save = self.parent.emulation_panel.store_to_flash_button
        self.buttons.read_bank = self.parent.emulation_panel.read_bank_button
        self.buttons.read_sram = self.parent.emulation_panel.read_sram_button

        #self.insert_new_file_signal.connect()

    @check_with_timeout(20)
    def is_send_data_succeeded(self):
        return self.parent.send_data_suceeded

    @check_with_timeout(20)
    def is_receive_data_succeeded(self):
        return self.parent.receive_data_suceeded

    def insert_new_file(self, file_path):
        self.parent.bin_file_panel.insert_new_file(file_path)

    def get_received_file_path(self):
        t0 = time.time()
        to_signal(self.parent.get_current_bin_file)()
        while time.time() - t0 < 2:
            try:
                return self.parent.current_bin_file
            except AttributeError:
                time.sleep(0.1)
        return self.parent.current_bin_file


    @check_with_timeout(2)
    def is_bank_in_use_set(self):
        return self.parent.bank_in_use != None

    def get_bank_in_use_testIF(self):
        return self.parent.bank_in_use

    @check_with_timeout(10)
    def is_connected(self):
        return self.parent.recevive_emulator_data_thread.isRunning()

    @check_with_timeout(1)
    def is_emulation_panel_unlocked(self):
        return self.parent.emulation_panel.isEnabled()

    def disconnect(self):
        self.parent.connect_button.clicked.emit(1)
        time.sleep(1)

    def click(self, clickable, wait=0.5):
        clickable.clicked.emit(1)
        time.sleep(wait)

    def put_new_bin_file_path(self, text):
        self.parent.insert_new_file_ti_signal.emit(text)

    def enter_bank_name(self, text):
        self.parent.banks_panel.bank_name_line_edit.setText(text)
        time.sleep(0.5)
        self.parent.banks_panel.bank_name_line_edit.returnPressed.emit()
        self.is_emulation_panel_unlocked()

    def get_bank_name(self):
        try:
            del self.parent.bank_name
        except AttributeError:
            pass
        to_signal(self.parent.get_bank_name)()
        t0 = time.time()
        while time.time() - t0 < 5:
            try:
                return self.parent.bank_name
            except AttributeError:
                time.sleep(0.1)
        return self.parent.bank_name
