#!/usr/bin/python
"""
author: Rafal Miecznik
contact: ravmiecznk@gmail.com
"""
#from pygame.time import delay

import platform
platform = platform.system()
# print platform
# if platform != 'Linux':
#     import qdarkstyle

import traceback
from main_logger import logger, info, debug, error, warn, EMU_BT_PATH, ExceptionLogger
from panels import ControlPanel, EmulationPanel, BanksPanel, BinFilePanel
from emulator import Emulator
from PyQt4 import QtCore, QtGui
from PyQt4.QtGui import QLabel
from PyQt4.QtCore import pyqtSignal, QEvent
from objects_with_help import HelpTip
from my_gui_thread import GuiThread, thread_this_method
from bt_discover import bt_search
from console import Console
from call_tracker import method_call_track
from reflasher import Reflasher
from event_handler import EventHandler, to_signal, general_signal_factory
from message_handler import MessageHandler, Message
from config_window import ConfigWindow
from bin_handler import BinSender, BinSenderInvalidBinSize
from banks_porcedures import BanksProcedures

import struct

import sys, os
import configparser
import time
import textwrap

BACKGROUND = "background-color: rgb({},{},{})"
GREEN_STYLE_SHEET = BACKGROUND.format(154,252,41)
GREY_STYLE_SHEET = BACKGROUND.format(48,53,58)

SETTINGS_PATH = EMU_BT_PATH

class WindowGeometry(object):
    def __init__(self, QtGuiobject):
        self.pos_x = QtGuiobject.x()
        self.pos_y = QtGuiobject.y()
        self.height = QtGuiobject.height()
        self.width = QtGuiobject.width()

    def get_position_to_the_right(self):
        pos_x = self.width + self.pos_x
        return pos_x

    def __call__(self):
        return self.pos_x, self.pos_y, self.width, self.height


def compare_bin_files(file1, file2):
    with open(file1, 'rb') as f1, open(file2, 'rb') as f2:
        cnt = 0
        for a in f1.read():
            b = f2.read(1)
            if a != b:
                print "DIFF at {:X}: {:2X} - {:2X}".format(cnt, ord(a), ord(b))
                raw_input('any key')
            else:
                print "{:2X} - {:2X}".format(ord(a), ord(b))
            cnt += 1

class QLabel(QLabel):
    """
    Wrapped QLabel with line wrapping
    """
    def __init__(self, *args, **kwargs):
        self._max_line_len, self._max_lines = kwargs.pop('max_text_size', (None, None)) #tuple line_len, lines_no
        QtGui.QLabel.__init__(self, *args, **kwargs)

    def setText(self, qstring):
        string = self.wrap_lines(qstring)
        QtGui.QLabel.setText(self, string)

    def wrap_lines(self, qstring):
        if self._max_line_len and self._max_lines:
            string = str(qstring)
            max_size = self._max_line_len * self._max_lines
            if len(string) > max_size:
                string = string[0:max_size] + "..."
                warn("{} exceeded max size {}, will be cut".format(string, max_size))
        return textwrap.fill(string, self._max_line_len)



@method_call_track
class MainWindow(QtGui.QMainWindow, BanksProcedures):
    help_tip_signal = pyqtSignal(object)
    gui_communication_signal = pyqtSignal(object)
    update_config_file_signal = pyqtSignal(object)

    #general signal may be used to send functions, can be implemented as dict
    general_signal = pyqtSignal(object)


    def __init__(self):
        QtGui.QMainWindow.__init__(self)
        #super(MainWindow, self).__init__()
        self.setWindowTitle("EMU BT")
        x_siz, y_siz = 500, 700
        mainGrid = QtGui.QGridLayout()
        mainGrid.setSpacing(10)
        self.centralwidget = QtGui.QWidget(self)
        self.event_handler = EventHandler()
        general_signal_factory.signal = self.general_signal
        #self.set_connection_status_signal = general_signal_factory(self.set_connection_status)


        self.setCentralWidget(self.centralwidget)

        self.help_text = QLabel(self.centralwidget, max_text_size=(x_siz/4.8, 4))
        self.help_text.raise_()
        self.connect_signals()


        self.update_config_file_signal.connect(self.update_config_file)
        self.event_handler.message = self.gui_communication_signal.emit
        self.event_handler.add_event(self.update_config_file_signal.emit, self.update_config_file.__name__)
        self.event_handler.add_event(self.gui_communication_signal.emit, 'communicate')
        self.event_handler.add_event(self.command_line_slot)
        self.event_handler.add_event(to_signal(self.connect_button_slot))
        self.event_handler.add_event(to_signal(self.reflash_button_slot))
        self.event_handler.add_event(to_signal(self.discover_emu_bt_slot))
        self.event_handler.add_event(to_signal(self.lost_connection_slot))
        self.event_handler.add_event(to_signal(self.config_button_slot))
        self.event_handler.add_event(to_signal(self.digidiag_on_slot))
        self.event_handler.add_event(to_signal(self.store_to_flash_button_slot))
        #self.event_handler.add_event(to_signal(self.get_emu_rx_buffer_slot))
        self.event_handler.add_event(to_signal(self.get_raw_rx_buffer_slot))
        self.event_handler.add_event(to_signal(self.send_help_cmd_slot))
        self.event_handler.add_event(to_signal(self.send_resetemu_slot))
        self.event_handler.add_event(to_signal(self.bank1set_slot))
        self.event_handler.add_event(to_signal(self.bank2set_slot))
        self.event_handler.add_event(to_signal(self.bank3set_slot))
        self.event_handler.add_event(to_signal(self.set_bank_name))
        self.event_handler.add_event(to_signal(self.bank_name_line_edit_event))
        self.event_handler.add_event(to_signal(self.bank_name_line_focus_out_event))

        self.__config_path = SETTINGS_PATH
        self.config_file_path = os.path.join(self.__config_path, 'emubt.cnf')
        self.app_status_file = os.path.join(self.__config_path, 'app_status.sts')

        self.control_panel = ControlPanel(self.centralwidget, event_handler=self.event_handler)
        self.emulation_panel = EmulationPanel(self.centralwidget, self.event_handler)
        self.banks_panel = BanksPanel(self.centralwidget, event_handler=self.event_handler)
        # CONSOLE--------------------------------------------------------------------------------
        self.console = Console(self.centralwidget, event_handler=self.event_handler)
        # self.console = Console(self.centralwidget, scroll_pressed_slot=self.scroll_pressed_slot,
        #                        console_select_text_slot=self.console_select_text_slot, event_handler=self.event_handler)
        # self.command_line = self.console.command_line
        # self.console_text_browser = self.console.console_text_browser
        # CONSOLE--------------------------------------------------------------------------------
        self.bin_file_panel = BinFilePanel(self.centralwidget, event_handler=self.event_handler, app_status_file=self.app_status_file)

        #create discovery thread in init---------------------------------------------------------
        bt_device_to_search = 'EMUBT'
        self.discovery_thread = GuiThread(process=bt_search, args=(bt_device_to_search, self.event_handler),
                                          action_when_done=to_signal(self.discovery_thread_teardown))
        self.blink_discovery_btn()
        # create discovery thread in init---------------------------------------------------------


        self.port, self.address = self.read_emubt_config()
        self.emulator = Emulator(self.port, self.address, timeout=0.1)
        self.emulator.set_event_handler(self.event_handler)

        self.message_handler = MessageHandler(self.emulator, self.event_handler,)

        self.create_threads()
        self.connect_button = self.control_panel.connect_button

        HelpTip.set_static_help_tip_slot_signal(self.help_tip_signal)

        mainGrid.addWidget(self.control_panel,   0, 0, 2, 1)
        mainGrid.addWidget(self.emulation_panel, 0, 2, 2, 1)
        mainGrid.addWidget(self.banks_panel,     0, 4, 2, 1)
        mainGrid.addWidget(self.bin_file_panel,  5, 0, 1, 6)
        mainGrid.addWidget(self.console,         6, 0, 6, 6)
        mainGrid.addWidget(self.help_text,      13, 0, 1, 6)
        self.centralwidget.setLayout(mainGrid)

        Message.default_negative_signal = self.console_msg_factory("command failed")

        self.resize(x_siz, y_siz)
        self.disable_objects_for_transmission()
        self.connect_button_slot()

    def initUI(self):
        QtGui.QApplication.setStyle(QtGui.QStyleFactory.create('Cleanlooks'))
        self.show()

    def digidiag_on_slot(self):
        Message('digidiag_on')

    def get_raw_rx_buffer_slot(self):
        self.emulator_event_handler()
        raw_data = self.emulator.raw_buffer.read()
        debug("raw_rx_buffer: {}".format(raw_data))



    def emulator_event_handler(self):
        """
        Handles random emulator output
        :return:
        """
        welcome_msg = 'BT EEPROM EMULATOR R'
        if welcome_msg in self.emulator.raw_buffer:
            Message('digidiag_off', positive_signal=lambda :None)

    def lost_connection_slot(self):
        self.gui_communication_signal.emit("LOST BT CONNECTION")
        self.set_disconnected()

    def command_line_slot(self, command):
        self.console.command_line.clear()
        cmd = str(command)
        if cmd[0:2] == 'E:':
            self.handle_E_command(cmd.split('E:')[1])
        else:
            self.message_handler.send(cmd)

    def handle_E_command(self, cmd):
        cnt = 0
        tot_mem = 0
        if cmd == 'gui threads':
            for thread in GuiThread.threads_dict:
                for thread_id in thread:
                    self.gui_communication_signal.emit("{}  {} id {}".format(GuiThread.__name__, thread, thread_id))
                    tot_mem += sys.getsizeof(thread_id)
                    cnt += 1
            self.gui_communication_signal.emit("Total threads: {}".format(cnt))
            self.gui_communication_signal.emit("Total mem: {}".format(tot_mem))
            self.gui_communication_signal.emit("Total dict mem: {}".format(sys.getsizeof(GuiThread.threads_dict)))
        if cmd == 'kill threads':
            GuiThread.kill_all_threads()
            self.recevive_emulator_data_thread.start()
            self.console.console_text_browser.clear()
        else:
            self.gui_communication_signal.emit("unsuported command")

    def send_help_cmd_slot(self):
        Message('help')
        #self.message_handler.send('help')

    def send_resetemu_slot(self):
        Message('resetemu')
        GuiThread(to_signal(self.get_bank_in_use), delay=1).start()
        #GuiThread(Message, args=('digidiag_off',), delay=0.5).start()
        #Message('digidiag_off', resp_positive='digidiag 0')

    def read_emubt_config(self):
        config = configparser.ConfigParser()
        config.read(self.config_file_path)
        try:
            port = config['BLUETOOTH']['bt_device_port']
            address = config['BLUETOOTH']['bt_device_address']
            info("Emulator config: port:{}, address:{}".format(port, address))
            if not port or not address:
                raise KeyError
            return port, address
        except KeyError:
            self.gui_communication_signal.emit("No BLUETOOTH config in: {}, or file not present".format(self.config_file_path))
            self.gui_communication_signal.emit("Trying autodiscovery")
            self.discover_emu_bt_slot()
            return None, None

    def reflash_button_slot(self):
        debug("Check if bootloader already active")
        self.emulator.rx_buffer.flush()
        Message('run_bootloader\n', create_header=False, resp_positive='BOOTLOADER',
                positive_signal=to_signal(self.reflash_app_slot),
                negative_signal=to_signal(self.activate_bootloader), timeout=0.2, max_retx=2)

    def activate_bootloader(self):
        debug("Try to enable bootloader in default mode")
        Message('run_bootloader', positive_signal=to_signal(self.reflash_app_slot),
                negative_signal=to_signal(self.bootloader_activation_fail), timeout=0.5)


    def disable_objects_for_transmission(self):
        self.emulation_panel.setDisabled(True)
        self.banks_panel.setDisabled(True)
        self.control_panel.reflash_button.setDisabled(True)

    def enable_objects_after_transmission(self):
        self.emulation_panel.setDisabled(False)
        self.banks_panel.setDisabled(False)
        self.control_panel.reflash_button.setDisabled(False)
        self.banks_panel.bank1pushButton.setDisabled(False)
        self.banks_panel.bank2pushButton.setDisabled(False)
        self.banks_panel.bank3pushButton.setDisabled(False)

###Make another object from this
    def store_to_flash_button_slot(self):
        self.t0 = time.time()
        bin_path = self.bin_file_panel.get_current_file()
        if bin_path:
            try:
                self.bin_sender = BinSender(bin_path)
                #self._tmp_file = open(os.path.join(EMU_BT_PATH, 'tmp.bin'), 'wb')
                Message('rxflush', positive_signal=to_signal(self.send_data_packet.start),
                        negative_signal=self.console_msg_factory("rxflush failed"))
            except IOError as e:
                self.gui_communication_signal.emit("{}: {}".format(e.strerror, e.filename))
                raise e
            except BinSenderInvalidBinSize as e:
                self.gui_communication_signal.emit('{} {}'.format(e.__class__, e.message))
                raise e

    @thread_this_method()
    def send_data_packet(self):
        if not self.blink_save_btn.isRunning():
            self.blink_save_btn.start()
        to_signal(self.disable_objects_for_transmission)()
        try:
            next_packet = next(self.bin_sender)
        except StopIteration:
            self.get_writing_stats.start()
            return
        Message(struct.pack('H', self.bin_sender.packets_get - 1) + next_packet, id=Message.ID.write_to_page,
                positive_signal=to_signal(self.send_data_packet_on_ack), negative_signal=to_signal(self.send_data_packet_teardown_on_fail))

    def send_data_packet_on_ack(self):
        try:
            progress = 100*self.bin_sender.packets_get/self.bin_sender.tot_packests
        except ZeroDivisionError:
            progress = 0
        to_signal(self.console.console_text_browser.clear)()
        self.gui_communication_signal.emit("\n\nUpdating: {}%".format(progress))
        self.send_data_packet.start()

    def send_data_packet_teardown_on_fail(self):
        self.blink_save_btn.kill()
        self.gui_communication_signal.emit("SAVE operation failed. Check error log")
        to_signal(self.enable_objects_after_transmission)()

    @thread_this_method()
    def get_writing_stats(self):
        to_signal(self.enable_objects_after_transmission)()
        self.blink_save_btn.kill()
        self.gui_communication_signal.emit("DONE in time {}".format(time.time() - self.t0))
        Message("writingtime")

    def console_msg_factory(self, msg):
        def wrapper(*args):
            self.gui_communication_signal.emit(msg)
        return wrapper
###Make another object from this

    def check_if_bootloader_already_active(self):
        debug("Check if bootloader already active")
        self.emulator.rx_buffer.flush()
        Message('run_bootloader\n', create_header=False, resp_positive='BOOTLOADER', positive_signal=to_signal(self.reflash_app_slot),
                negative_signal=to_signal(self.bootloader_activation_fail), timeout=0.5)

    def bootloader_activation_fail(self):
        self.gui_communication_signal.emit("Bootloader activation failed")

    def reflash_app_slot(self):
        self.setEnabled(False)
        GuiThread.kill_all_threads()
        self.recevive_emulator_data_thread.start()
        self.emulator.rx_buffer.read()
        current_position_and_size = WindowGeometry(self)
        x_pos = current_position_and_size.get_position_to_the_right()
        self.reflasher = Reflasher(self.app_status_file, self.emulator, signal_on_close=to_signal(self.reflash_window_close_slot))
        x_offset = 15
        y_offset = 100
        self.reflasher.setGeometry(x_pos + x_offset, current_position_and_size.pos_y + y_offset, self.reflasher.x_siz, self.reflasher.y_siz)
        self.reflasher.show()

    def reflash_window_close_slot(self):
        self.setEnabled(True)
        GuiThread.resume_all_threads()
        Message('disable_bootloader')

    def update_config_file(self, kwargs):
        self.gui_communication_signal.emit("Updating:")
        for k in kwargs:
            self.gui_communication_signal.emit("{} {}".format(k, kwargs[k])),
        ConfigWindow(self.config_file_path).update_config_file(**kwargs)
        self.port, self.address = self.read_emubt_config()

    def connect_signals(self):
        self.help_tip_signal.connect(self.help_text.setText)
        self.gui_communication_signal.connect(self.console_communication_pipe_slot)
        self.general_signal.connect(self.general_signal_slot)

    def general_signal_slot(self, object):
        object()
        return
        try:
            object()
        except TypeError:
            error("{}:{} cant be executed in {}".format(type(object), object.__name__,  self.general_signal_slot.__name__))

    def console_communication_pipe_slot(self, msg):
        self.console.communication_pipe_slot(msg)

    @thread_this_method()
    def connection_thread(self):
        self.blink_connect_btn.start()
        self.emulator.connect(self.port, self.address)

    @thread_this_method(period=0.5)
    def blink_discovery_btn(self):
        to_signal(self.control_panel.discover_button.blink)()
        #self.control_panel.discover_button.blink()

    @thread_this_method(period=0.5)
    def blink_connect_btn(self):
        to_signal(self.control_panel.connect_button.blink)()

    @thread_this_method(period=0.4)
    def blink_save_btn(self):
        to_signal(self.emulation_panel.store_to_flash_button.blink)()

    def create_threads(self):
        #self.write_flash_slot()
        self.send_data_packet()
        self.get_writing_stats()
        self.blink_discovery_btn.on_terminate = to_signal(self.control_panel.discover_button.set_default_style_sheet)

        self.blink_connect_btn()

        self.blink_save_btn()
        self.blink_save_btn.on_terminate = to_signal(self.emulation_panel.store_to_flash_button.set_default_style_sheet)

        self.read_bank_info()

        #self.blink_connect_btn.on_terminate = self.control_panel.connect_button.set_default_style_sheet
        #self.discovery_thread_teardown()

        self.connection_thread()
        self.connection_thread.action_when_done = to_signal(self.set_connection_status)

        self.recevive_emulator_data_thread = GuiThread(process=self.emulator.receive_data, period=0.001)

    def set_connected(self):
        self.connect_button.setText("disconnect")
        self.connect_button.set_green_style_sheet()
        self.recevive_emulator_data_thread.start()
        self.get_bank_in_use()
        self.enable_objects_after_transmission()
        #TODO tmp
        #self.reflash_button_slot()

    def set_disconnected(self):
        GuiThread.kill_all_threads()
        #self.recevive_emulator_data_thread.kill()
        self.connect_button.setText("Connect")
        self.connect_button.set_default_style_sheet()
        self.emulator.disconnect()

    def set_connection_status(self):
        #self.blink_connect_btn.kill()
        self.blink_connect_btn.kill()
        if self.emulator.get_connection_status() == True:
            self.set_connected()
            GuiThread(Message, args=('digidiag_off',), delay=0.5).start()
        else:
            self.set_disconnected()

    def connect_button_slot(self):
        if self.port is None and self.address is None:
            self.gui_communication_signal.emit("There is no configuration for EMUBT")
            return
        if not self.emulator.connected:
            if not self.connection_thread.isRunning():
                self.connection_thread.start()
            else:
                print 'stop connecting'
                self.connection_thread.kill()
                self.recevive_emulator_data_thread.kill()
                self.emulator.disconnect()
                self.set_connection_status()
        else:
            self.recevive_emulator_data_thread.kill()
            self.emulator.disconnect()
            self.set_connection_status()

    def config_button_slot(self):
        self.config_window = ConfigWindow(self.config_file_path)
        x_offset = 15
        y_offset = 100
        current_position_and_size = WindowGeometry(self)
        x_pos = current_position_and_size.get_position_to_the_right()
        self.config_window.setGeometry(x_pos + x_offset, current_position_and_size.pos_y + y_offset, self.config_window.x_siz, self.config_window.y_siz)
        self.config_window.show()

    def positive_resp(self):
        self.gui_communication_signal.emit("HURRA")

    def negative_signal(self):
        self.gui_communication_signal.emit("SHIT")

    def discovery_thread_teardown(self):
        self.blink_discovery_btn.kill()

    def discover_emu_bt_slot(self):
        try:
            if self.emulator.get_connection_status() == False:
                if not self.discovery_thread.isRunning():
                    self.discovery_thread.start()
                    self.blink_discovery_btn.start()
                else:
                    self.help_text.setText("Discovery process already running")
            else:
                self.help_text.setText("Can't do it when connected")
        except:
            self.blink_discovery_btn.start()
            self.discovery_thread.start()


    def tear_down(self):
        print "tear down"
        self.bin_file_panel.update_app_status_file()

    def closeEvent(self, event):
        if event.type() == QEvent.Close:
            self.tear_down()

    def destroyEvent(self, event):
        print "destroy"

def main():

    app = QtGui.QApplication(sys.argv)
    myapp = MainWindow()
    if platform == 'Windows':
        app.setStyle(QtGui.QStyleFactory.create('Cleanlooks'))
    #for i in QtGui.QStyleFactory.keys():
    #    print i
    myapp.show()
    app.exec_()
    sys.exit()
    sys.stdout = STDOUT

if __name__ == "__main__":
    exception_logger = ExceptionLogger()
    main()
    # try:
    #     main()
    # except Exception as E:
    #     print "Catched: {}".format(E)
    #     traceback.print_exc(file=exception_logger)
    #     raise E
