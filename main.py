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

def dupa(*args):
    print args
    print 'dupa'

@method_call_track
class MainWindow(QtGui.QMainWindow):
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
        self.event_handler.add_event(to_signal(self.store_to_flash_button_slot))
        #self.event_handler.add_event(to_signal(self.get_emu_rx_buffer_slot))
        self.event_handler.add_event(to_signal(self.get_raw_rx_buffer_slot))
        self.event_handler.add_event(to_signal(self.send_help_cmd_slot))
        self.event_handler.add_event(to_signal(self.send_resetemu_slot))

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
        #Message.default_negative_signal = dupa

        self.resize(x_siz, y_siz)
        self.connect_button_slot()

    def initUI(self):
        QtGui.QApplication.setStyle(QtGui.QStyleFactory.create('Cleanlooks'))
        self.show()

    def get_raw_rx_buffer_slot(self):
        debug("raw_rx_buffer: {}".format(self.emulator.raw_buffer.read()))

    def lost_connection_slot(self):
        self.gui_communication_signal.emit("LOST BT CONNECTION")
        self.set_disconnected()

    def command_line_slot(self, command):
        self.console.command_line.clear()
        self.message_handler.send(str(command))

    def send_help_cmd_slot(self):
        Message('help')
        #self.message_handler.send('help')

    def send_resetemu_slot(self):
        self.message_handler.send('resetemu')

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
        debug("Try to enable bootloader in default mode")
        Message('run_bootloader', positive_signal=to_signal(self.reflash_app_slot),
                negative_signal=to_signal(self.check_if_bootloader_already_active), timeout=0.5)


###Make another object from this
    def store_to_flash_button_slot(self):
        self.t0 = time.time()
        bin_path = self.bin_file_panel.get_current_file()
        try:
            self.bin_sender = BinSender(bin_path)
            Message('rxflush', positive_signal=to_signal(self.send_data_packet.start),
                    negative_signal=self.console_msg_factory("rxflush failed"))
        except IOError as e:
            self.gui_communication_signal.emit("{}: {}".format(e.strerror, e.filename))
            raise e
        except BinSenderInvalidBinSize as e:
            self.gui_communication_signal.emit('{} {}'.format(e.__class__, e.message))
            raise e

    @thread_this_method(alias='write_flash_slot')
    def write_flash_slot(self):
        positive_signal = to_signal(self.write_flash_slot.start) if self.bin_sender.packets_get != 15 else to_signal(
            self.get_writing_stats.start)

        Message(struct.pack('H', self.bin_sender.packets_get) + next(self.bin_sender), positive_signal=positive_signal, id=1)

        #Message(struct.pack('H', self.bin_sender.packets_get) + next(self.bin_sender), positive_signal=positive_signal, id=1)
        self.gui_communication_signal.emit("MSG sent: {}".format(self.bin_sender.packets_get))
        #Message('wr', positive_signal=to_signal(self.send_data_packet.start),
        #        negative_signal=to_signal(self.console_msg_factory("SAVE operation failed. Check error log")))

    @thread_this_method()
    def send_data_packet(self):
        positive_signal = to_signal(self.send_data_packet.start) if self.bin_sender.packets_get != 15 else to_signal(self.get_writing_stats.start)
        Message(struct.pack('H', self.bin_sender.packets_get) + next(self.bin_sender), positive_signal=positive_signal, negative_signal=to_signal(self.console_msg_factory("SAVE operation failed. Check error log")), id=1)
        self.gui_communication_signal.emit("MSG sent: {}".format(self.bin_sender.packets_get))

    @thread_this_method()
    def get_writing_stats(self):
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
        self.connection_thread.suspend_all_threads()
        self.recevive_emulator_data_thread.resume()
        self.emulator.rx_buffer.read()
        current_position_and_size = WindowGeometry(self)
        x_pos = current_position_and_size.get_position_to_the_right()
        self.reflasher = Reflasher(self.app_status_file, self.emulator, signal_on_close=to_signal(self.reflash_window_close_slot))
        x_offset = 15
        y_offset = 100
        self.reflasher.setGeometry(x_pos + x_offset, current_position_and_size.pos_y + y_offset, self.reflasher.x_siz, self.reflasher.y_siz)
        self.reflasher.show()

    def reflash_window_close_slot(self):
        print "reflasher close signal"
        self.setEnabled(True)
        self.connection_thread.resume_all_threads()
        #Message('disable_bootloader')
        Message('handshake', positive_signal=to_signal(GuiThread(Message, args=('disable_bootloader',)).start))

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

    def create_threads(self):
        self.write_flash_slot()
        self.send_data_packet()
        self.get_writing_stats()
        self.blink_discovery_btn.on_terminate = self.control_panel.discover_button.set_default_style_sheet

        self.blink_connect_btn()
        #self.blink_connect_btn.on_terminate = self.control_panel.connect_button.set_default_style_sheet
        #self.discovery_thread_teardown()

        self.connection_thread()
        self.connection_thread.action_when_done = to_signal(self.set_connection_status)

        self.recevive_emulator_data_thread = GuiThread(process=self.emulator.receive_data, period=0.001)

    def set_connected(self):
        self.connect_button.setText("disconnect")
        self.connect_button.set_green_style_sheet()
        self.recevive_emulator_data_thread.start()
        #TODO tmp
        #self.reflash_button_slot()

    def set_disconnected(self):
        self.blink_connect_btn.kill_all_threads()
        #self.recevive_emulator_data_thread.kill()
        self.connect_button.setText("Connect")
        self.connect_button.set_default_style_sheet()
        self.emulator.disconnect()

    def set_connection_status(self):
        self.blink_connect_btn.kill()
        if self.emulator.get_connection_status() == True:
            self.set_connected()
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
                pass
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
