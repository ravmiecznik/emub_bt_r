#!/usr/bin/python
"""
author: Rafal Miecznik
contact: ravmiecznk@gmail.com
"""


import platform
platform = platform.system()
# print platform
# if platform != 'Linux':
#     import qdarkstyle


from collections import namedtuple
from setup_emubt import logger, info, debug, error, warn, EMU_BT_PATH, LOG_PATH
from panels import ControlPanel, EmulationPanel, BanksPanel, BinFilePanel
from emulator import Emulator
from PyQt4 import QtCore, QtGui
from PyQt4.QtGui import QLabel
from PyQt4.QtCore import pyqtSignal, QEvent
from main_window import ColorProgressBar
from objects_with_help import HelpTip
from gui_thread import thread_this_method, GuiThread, SignalThread
from bt_discover import bt_search
from console import Console
from call_tracker import method_call_track
from reflasher import Reflasher
from event_handler import EventHandler, to_signal, general_signal_factory
from message_handler import MessageSender, MessageReceiver, RxMessage, TxTimeout
from config_window import ConfigWindow, ConfigSettings
from procedures import WritePackets, ReadSramProcedure, ReadBankProcedure
from test_module import TestInterface
from digidiag import DigiDiag
from message_box import message_box
from bin_tracker import BinTracker
import sys, os, subprocess
import configparser
import time
import textwrap
from bin_handler import BinFilePacketGenerator, BinSenderInvalidBinSize


BACKGROUND = "background-color: rgb({},{},{})"
GREEN_STYLE_SHEET = BACKGROUND.format(154, 252, 41)
GREY_STYLE_SHEET = BACKGROUND.format(48, 53, 58)

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
class MainWindow(QtGui.QMainWindow, ConfigSettings):
    help_tip_signal = pyqtSignal(object)
    gui_communication_signal = pyqtSignal(object)
    update_config_file_signal = pyqtSignal(object)
    insert_new_file_signal = pyqtSignal(object)
    set_banks_panel_bank_name_signal = pyqtSignal(object)
    config_window_apply_signal = pyqtSignal()
    general_signal = pyqtSignal(object)

    def __init__(self, is_test=False):
        print 'PATH', EMU_BT_PATH
        self.__receive_data_period = 0.01
        self.bank_in_use = None
        self.is_test = is_test
        self.config_path = SETTINGS_PATH
        if platform != 'Linux':
            self.config_path = self.config_path.replace('/', '\\')
        QtGui.QMainWindow.__init__(self)
        self.setWindowTitle("EMU BT")
        x_siz, y_siz = 500, 700
        main_grid = QtGui.QGridLayout()
        main_grid.setSpacing(10)
        self.centralwidget = QtGui.QWidget(self)
        self.event_handler = EventHandler()
        general_signal_factory.signal = self.general_signal
        SignalThread.general_signal = self.general_signal

        self.last_bin_files_tag = "LAST BIN FILES"
        self.buttons_status_tag = "BUTTONS STATUS"

        self.setCentralWidget(self.centralwidget)

        self.help_text = QLabel(self.centralwidget, max_text_size=(x_siz/4.8, 4))
        self.help_text.raise_()

        self.update_config_file_signal.connect(self.update_config_file)
        self.config_window_apply_signal.connect(self.config_window_apply_slot)
        self.event_handler.message = self.gui_communication_signal.emit
        self.event_handler.add_event(self.update_config_file_signal.emit, self.update_config_file.__name__)
        self.event_handler.add_event(self.gui_communication_signal.emit, 'communicate')
        self.event_handler.add_event(self.command_line_slot)
        self.event_handler.add_event(to_signal(self.connect_button_slot))
        self.event_handler.add_event(to_signal(self.reflash_button_slot))
        self.event_handler.add_event(to_signal(self.discover_emu_bt_slot))
        self.event_handler.add_event(to_signal(self.lost_connection_slot))
        self.event_handler.add_event(to_signal(self.config_button_slot))
        self.event_handler.add_event(to_signal(self.emulate_button_slot))
        self.event_handler.add_event(to_signal(self.get_raw_rx_buffer_slot))
        self.event_handler.add_event(to_signal(self.send_help_cmd_slot))
        self.event_handler.add_event(to_signal(self.send_resetemu_slot))
        self.event_handler.add_event(to_signal(self.bank1set_slot))
        self.event_handler.add_event(to_signal(self.bank2set_slot))
        self.event_handler.add_event(to_signal(self.bank3set_slot))
        self.event_handler.add_event(to_signal(self.set_bank_name))
        self.event_handler.add_event(to_signal(self.bank_name_line_edit_event))
        self.event_handler.add_event(to_signal(self.bank_name_line_focus_out_event))
        self.event_handler.add_event(to_signal(self.emulation_diffs_present_slot))
        self.event_handler.add_event(to_signal(self.open_bin_file))

        ConfigSettings.__init__(self)

        self.control_panel = ControlPanel(self.centralwidget, event_handler=self.event_handler)
        self.banks_panel = BanksPanel(self.centralwidget, event_handler=self.event_handler)
        # CONSOLE--------------------------------------------------------------------------------
        self.console = Console(self.centralwidget, event_handler=self.event_handler)
        # CONSOLE--------------------------------------------------------------------------------

        self.bin_file_panel = BinFilePanel(self.centralwidget, event_handler=self.event_handler, app_status_file=self.app_status_file)

        # create discovery thread in init---------------------------------------------------------
        bt_device_to_search = 'EMUBT'
        self.discovery_thread = GuiThread(process=bt_search, args=(bt_device_to_search, self.event_handler),
                                          action_when_done=to_signal(self.discovery_thread_teardown))
        self.blink_discovery_btn()
        # create discovery thread in init---------------------------------------------------------

        self.connect_signals()
        self.setup_emulator()

        self.progress_bar = ColorProgressBar(parent=self)

        allow_read_sram = self.read_allow_read_sram_option()
        if is_test:
            allow_read_sram = True
        self.emulation_panel = EmulationPanel(self.centralwidget, read_sram_allowed=allow_read_sram)

        self.event_handler.add_event(to_signal(self.save_button_slot))

        if self.is_test == True:
            self.test_interface = TestInterface(self)
            self.control_panel.autoconnect_checkbox.setChecked(False)

        self.message_receiver = MessageReceiver(self.emulator.raw_buffer)
        self.rx_message_buffer = dict()

        self.create_threads()
        self.connect_button = self.control_panel.connect_button

        HelpTip.set_static_help_tip_slot_signal(self.help_tip_signal)

        main_grid.addWidget(self.control_panel,   0, 0, 2, 1)
        main_grid.addWidget(self.emulation_panel, 0, 2, 2, 1)
        main_grid.addWidget(self.banks_panel,     0, 4, 2, 1)
        main_grid.addWidget(self.bin_file_panel,  5, 0, 1, 6)
        main_grid.addWidget(self.console,         6, 0, 6, 6)
        main_grid.addWidget(self.help_text,      13, 0, 1, 6)
        self.centralwidget.setLayout(main_grid)

        self.raw_rx_buffer = self.emulator.raw_buffer
        self.rx_buffer = self.emulator.raw_buffer

        self.event_handler.add_event(to_signal(self.read_bank_button_slot), 'read_bank_button_slot')
        self.event_handler.add_event(to_signal(self.read_sram_button_slot), 'read_sram_button_slot')
        self.emulation_panel.set_event_handler(self.event_handler)

        self.resize(x_siz, y_siz)
        self.disable_objects_for_transmission_signal()
        self.load_last_status()
        self.__restore_digidiag = True
        if self.control_panel.autoconnect_checkbox.isChecked():
            self.connect_button_slot()
        self.digidiag_slot()

    def initUI(self):
        QtGui.QApplication.setStyle(QtGui.QStyleFactory.create('Cleanlooks'))

    def __send_message(self, m_id, body='NULL', timeout=0.3):
        self.message_handler.send(m_id=MessageSender.ID.rxflush, body=body)
        time.sleep(0.1)
        re_tx = 3
        self.message_handler.send(MessageSender.ID.rxflush)
        self.rx_buffer.flush()
        context = self.message_handler.send(m_id)
        while context not in self.rx_message_buffer and re_tx >= 0:
            context = self.message_handler.send(m_id, body=body)
            re_tx -= 1
            debug("ReTx: {}".format(MessageSender.ID.translate_id(m_id)))
            time.sleep(timeout)
        else:
            try:
                return self.rx_message_buffer[context].crc_check
            except KeyError:
                return None

    def send_message(self, message_id, body='NULL', timeout=0.3):
        self.send_message_thread = GuiThread(self.__send_message, args=(message_id, body, timeout))
        self.send_message_thread.start()
        return self.send_message_thread.returned

    def read_sram_button_slot(self):
        self.message_handler.send(MessageSender.ID.rxflush)
        self.read_sram = ReadSramProcedure(self)
        self.read_sram.read_thread.start()

    def read_bank_button_slot(self):
        self.message_handler.send(MessageSender.ID.rxflush)
        self.read_sram = ReadBankProcedure(self)
        self.read_sram.read_thread.start()

    def save_button_slot(self):
        bin_path = self.bin_file_panel.get_current_file()
        try:
            bin_packets = BinFilePacketGenerator(bin_path)
        except IOError as e:
            self.gui_communication_signal.emit("{}: {}".format(e.strerror, e.filename))
            raise e
        except BinSenderInvalidBinSize as e:
            self.gui_communication_signal.emit('{} {}'.format(e.__class__, e.message))
            self.combo_box.removeByStr(bin_path)
            self.bin_file_panel.update_app_status_file()
            message_box("This is not 27c256 bin image: {}".format(bin_path))
            raise e
        self.write_packets = WritePackets(self, bin_packets)
        self.write_packets.write_thread.start()

    def setup_emulator(self):
        self.port, self.address = self.read_emubt_config()
        self.emulator = Emulator(self.port, self.address, timeout=self.__receive_data_period/2)
        self.emulator.set_event_handler(self.event_handler)
        self.message_handler = MessageSender(self.emulator.send, self.emulator.raw_buffer)

    def config_window_apply_slot(self):
        """
        reload emulator related objects
        :return:
        """
        self.setup_emulator()
        self.connection_thread = GuiThread(self.__connection_thread,
                                           action_when_done=to_signal(self.set_connection_status))
        self.recevive_emulator_data_thread = GuiThread(process=self.emulator.receive_data,
                                                       period=self.__receive_data_period)

    def get_current_bin_file(self):
        self.current_bin_file = self.bin_file_panel.get_current_file()

    def get_bank_name(self):
        self.bank_name = self.banks_panel.bank_name_line_edit.text()

    def open_bin_file(self):
        config = configparser.ConfigParser()
        config.read(self.config_file_path)
        editor = config['EDITORS']['bin_editor']
        try:
            self.editor_subrpocess.kill()
        except AttributeError:
            pass
        self.editor_subrpocess = subprocess.Popen([editor, self.bin_file_panel.get_current_file()])

    def get_raw_rx_buffer_slot(self):
        banks = ['bank1set', 'bank2set', 'bank3set']
        cnt = 0
        t0 = time.time()
        msg = self.message_receiver.get_message()
        while msg:
            if msg.id == RxMessage.rx_id_tuple.index('txt'):   #free text
                self.gui_communication_signal.emit("E: {}".format(msg.msg))
            elif msg.id == RxMessage.rx_id_tuple.index('ack') and msg.msg in banks:
                self.set_bank_in_use(banks.index(msg.msg))
            elif msg.id == RxMessage.rx_id_tuple.index('ack') and 'bankname:' in msg.msg:
                self.set_banks_panel_bank_name_signal.emit(msg.msg.split(':')[1])
            elif msg.id == RxMessage.rx_id_tuple.index('dgframe'):
                #self.digidag_frames[ord(msg.msg[1])] = msg.msg
                self.feed_digidiag(msg.msg)
                #self.gui_communication_signal.emit((10*' {:02X}').format(*[ord(i) for i in msg.msg]))
            self.rx_message_buffer[msg.context] = msg
            msg = self.message_receiver.get_message()
            if time.time() - t0 > 1:
                debug('guard periodic break')
                break
            cnt += 1

    # BANKS PROCEDURES
    def bank1set_slot(self):
        self.bank_set_slot(0)

    def bank2set_slot(self):
        self.bank_set_slot(1)

    def bank3set_slot(self):
        self.bank_set_slot(2)

    def bank_set_slot(self, bank_num):
        msg_id = [MessageSender.ID.bank1_set,MessageSender.ID.bank2_set, MessageSender.ID.bank3_set][bank_num]
        self.send_message(message_id=msg_id)

    def set_bank_in_use(self, bank_no):
        self.banks_panel.set_active_button(bank_no)

    def set_bank_name(self, bank_name=None):
        if bank_name is None:
            bank_name = str(self.banks_panel.get_bank_name_text())
        bank_name = bank_name[0:self.banks_panel.bank_name_max_len]
        # don't update bank name if not changed
        try:
            if self.__tmp_bank_name != bank_name:
                self.banks_panel.disable_active_button()
                self.send_message(MessageSender.ID.set_bank_name, body=bank_name, timeout=0.5)
        except AttributeError:
            self.banks_panel.disable_active_button()
            self.send_message(MessageSender.ID.set_bank_name, body=bank_name, timeout=0.5)
        self.__tmp_bank_name = bank_name[0:self.banks_panel.bank_name_max_len]

    def bank_name_line_focus_out_event(self):
        self.enable_objects_after_transmission_signal()
        self.set_bank_name()

    def bank_name_line_edit_event(self):
        self.emulation_panel.setDisabled(True)
        self.banks_panel.bank1pushButton.setDisabled(True)
        self.banks_panel.bank2pushButton.setDisabled(True)
        self.banks_panel.bank3pushButton.setDisabled(True)
        self.control_panel.reflash_button.setDisabled(True)

    @thread_this_method(period=3)
    def heartbeat(self):
        if self.emulator.connected:
            print self.heartbeat.__name__
            self.send_message(message_id=MessageSender.ID.dummy)
        return

    def lost_connection_slot(self):
        self.gui_communication_signal.emit("LOST BT CONNECTION")
        self.set_disconnected()

    def command_line_slot(self, command):
        self.console.command_line.clear()
        cmd = str(command)
        if cmd[0:2] == 'E:':
            self.handle_command(cmd.split('E:')[1])
        elif self.emulation_panel.isEnabled():
            self.message_handler.send(m_id=MessageSender.ID.txt_message, body=cmd)

    def handle_command(self, cmd):
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
        elif cmd == 'kill threads':
            GuiThread.suspend_all_threads()
            self.recevive_emulator_data_thread.start()
            self.console.console_text_browser.clear()
        elif cmd == 'digidiag_on':
            self.digidiag_on_slot()
        elif cmd == 'hsk':
            self.message_handler.send(id=MessageSender.ID.handshake)
        elif cmd == 'd':
            self.message_handler.send(m_id=MessageSender.ID.disable_btlrd)
        elif cmd == 's':
            self.send_message(MessageSender.ID.set_bank_name, body='rafal')
        elif cmd == 'i':
            self.digidiag_slot()
        else:
            self.gui_communication_signal.emit("unsuported command")

    def reload_sram(self):
        self.send_message(MessageSender.ID.reload_sram)

    def send_help_cmd_slot(self):
        self.send_message(MessageSender.ID.handshake)

    def send_resetemu_slot(self):
        self.send_message(MessageSender.ID.reset)

    def read_emubt_config(self):
        config = configparser.ConfigParser()
        config.read(self.config_file_path)
        try:
            port = config['BLUETOOTH']['bt_device_port']
            address = config['BLUETOOTH']['bt_device_address']
            if ':' not in address:
                address = ':'.join([a+b for a, b in zip(address[::2], address[1::2])])
            info("Emulator config: port:{}, address:{}".format(port, address))
            if not port or not address:
                raise KeyError
            return port, address
        except KeyError:
            self.gui_communication_signal.emit("No BLUETOOTH config in: {}, or file not present".format(self.config_file_path))
            self.gui_communication_signal.emit("Trying autodiscovery")
            self.discover_emu_bt_slot()
            return None, None

    def read_allow_read_sram_option(self):
        config = configparser.ConfigParser()
        config.read(self.config_file_path)
        try:
            allow = config['APPSETTINGS']['allow_read_sram'].upper()
            return allow == 'TRUE'
        except KeyError:
            return False

    def reflash_button_slot(self):
        debug("Check if bootloader already active")
        self.emulator.raw_buffer.flush()
        self.message_handler.send(m_id=MessageSender.ID.bootloader)
        t0 = time.time()
        while ('BOOTLOADER' not in self.rx_buffer) and ('command unknown' not in self.rx_buffer):
            time.sleep(0.01)
            if time.time() - t0 > 1:
                print 'break', ('BOOTLOADER' not in self.rx_buffer) and ('command unknown:' not in self.rx_buffer)
                break
        else:
            to_signal(self.reflash_app_slot)()

    def console_msg_factory(self, msg):
        def wrapper(*args):
            self.gui_communication_signal.emit(msg)
        return wrapper

    def bootloader_activation_fail(self):
        self.gui_communication_signal.emit("Bootloader activation failed")

    def suspend_all_threads_bt_rx_thread(self):
        GuiThread.suspend_all_threads()
        self.recevive_emulator_data_thread.resume()

    def reflash_app_slot(self):
        """
        Will call and display new reflasher window
        :return:
        """
        self.setEnabled(False)
        self.suspend_all_threads_bt_rx_thread()
        self.recevive_emulator_data_thread.start()
        self.emulator.raw_buffer.read()
        current_position_and_size = WindowGeometry(self)
        x_pos = current_position_and_size.get_position_to_the_right()
        self.reflasher = Reflasher(self.app_status_file, self.emulator, receive_data_thread=self.recevive_emulator_data_thread, signal_on_close=to_signal(self.reflash_window_close_slot), message_handler=self.message_handler)
        x_offset = -400
        y_offset = 100
        self.reflasher.setGeometry(x_pos + x_offset, current_position_and_size.pos_y + y_offset, self.reflasher.x_siz, self.reflasher.y_siz)
        self.reflasher.show()

    def digidiag_slot(self):
        self.digiag_widget = DigiDiag()
        self.digiag_widget.show()

    def feed_digidiag(self, frame):
        try:
            self.digiag_widget.feed_with_data(frame)
        except AttributeError:
            pass

    def reflash_window_close_slot(self):
        self.setEnabled(True)
        GuiThread.resume_all_threads()
        self.send_message(MessageSender.ID.disable_btlrd)

    def __disable_objects_for_transmission(self):
        self.emulation_panel.setDisabled(True)
        self.banks_panel.setDisabled(True)
        self.control_panel.reflash_button.setDisabled(True)
        self.console.reset_button.setDisabled(True)
        self.console.help_button.setDisabled(True)
        self.bin_file_panel.combo_box.clearFocus()

    def __enable_objects_after_transmission(self):
        self.emulation_panel.setDisabled(False)
        self.banks_panel.setDisabled(False)
        self.control_panel.reflash_button.setDisabled(False)
        self.banks_panel.bank1pushButton.setDisabled(False)
        self.banks_panel.bank2pushButton.setDisabled(False)
        self.banks_panel.bank3pushButton.setDisabled(False)
        self.console.reset_button.setDisabled(False)
        self.console.help_button.setDisabled(False)

    def update_config_file(self, kwargs):
        self.gui_communication_signal.emit("Updating:")
        for k in kwargs:
            self.gui_communication_signal.emit("{} {}".format(k, kwargs[k])),
        ConfigWindow(self.config_file_path, apply_signal=self.config_window_apply_signal).update_config_file(**kwargs)
        self.port, self.address = self.read_emubt_config()

    def connect_signals(self):
        self.help_tip_signal.connect(self.help_text.setText)
        self.gui_communication_signal.connect(self.console_communication_pipe_slot)
        self.general_signal.connect(self.general_signal_slot)
        self.disable_objects_for_transmission_signal = to_signal(self.__disable_objects_for_transmission)
        self.enable_objects_after_transmission_signal = to_signal(self.__enable_objects_after_transmission)
        self.insert_new_file_signal.connect(self.bin_file_panel.insert_new_file)
        self.set_banks_panel_bank_name_signal.connect(self.banks_panel.put_bank_name)

    def general_signal_slot(self, object):
        object()
        return

    def console_communication_pipe_slot(self, msg):
        self.console.communication_pipe_slot(msg)

    def __connection_thread(self):
        self.blink_connect_thread = GuiThread(to_signal(self.control_panel.connect_button.blink), period=0.5)
        self.blink_connect_thread.start()
        self.emulator.connect(self.port, self.address)

    @thread_this_method(period=0.5)
    def blink_discovery_btn(self):
        to_signal(self.control_panel.discover_button.blink)()

    @thread_this_method(period=0.5)
    def blink_connect_btn(self):
        print 'blink'
        to_signal(self.control_panel.connect_button.blink)()

    def create_threads(self):
        """
        By calling all methods decorated by "thread_this_method" the GuiThread constructor is called.
        "thread_this_method" returns wrapped GuiThread class object so it needs to be called to return
        a GuiThread instance. It is here where method becomes a thread.
        :return:
        """
        self.blink_discovery_btn.on_terminate = to_signal(self.control_panel.discover_button.set_default_style_sheet)
        self.blink_connect_btn()
        self.connection_thread = GuiThread(self.__connection_thread,
                                           action_when_done=to_signal(self.set_connection_status))
        self.recevive_emulator_data_thread = GuiThread(process=self.emulator.receive_data, period=0.1, trace=None)
        self.heartbeat()
        self.send_sram_bytes()

    def set_connected(self):
        self.blink_connect_thread.terminate()
        self.connect_button.setText("disconnect")
        self.recevive_emulator_data_thread.start()
        self.recevive_emulator_data_thread.resume()
        self.enable_objects_after_transmission_signal()
        self.tmp_thread = GuiThread(process=to_signal(self.connect_button.set_green_style_sheet))
        self.tmp_thread.start()
        self.send_message(message_id=MessageSender.ID.get_bank_in_use)

    def set_disconnected(self):
        self.disable_objects_for_transmission_signal()
        GuiThread.suspend_all_threads()
        self.connect_button.setText("Connect")
        self.connect_button.set_default_style_sheet()
        self.emulator.disconnect()

    def set_connection_status(self):
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
                self.connection_thread = GuiThread(self.__connection_thread,
                                                   action_when_done=to_signal(self.set_connection_status))
                self.connection_thread.start()
            else:
                self.blink_connect_thread.terminate()
                self.connection_thread.kill()
                self.recevive_emulator_data_thread.suspend()
                self.emulator.disconnect()
                self.set_connection_status()
        else:
            self.recevive_emulator_data_thread.suspend()
            self.emulator.disconnect()
            self.set_connection_status()

    def config_button_slot(self):
        self.config_window = ConfigWindow(self.config_file_path, self.config_window_apply_signal)
        x_offset = 15
        y_offset = 100
        current_position_and_size = WindowGeometry(self)
        x_pos = current_position_and_size.get_position_to_the_right()
        self.config_window.setGeometry(x_pos + x_offset, current_position_and_size.pos_y + y_offset, self.config_window.x_siz, self.config_window.y_siz)
        self.config_window.show()

    def discovery_thread_teardown(self):
        self.blink_discovery_btn.terminate()
        self.control_panel.discover_button.set_default_style_sheet()

    def discover_emu_bt_slot(self):
        """
        It covers two cases:
        -when discovery is triggered by button
        -when discovery is triggered when there is no BT config available
        why there is try except clause and if/else inside it
        :return:
        """
        def start_discovery():
            self.discovery_thread.start()
            self.blink_discovery_btn.start()
        try:
            if self.emulator.get_connection_status() == False:
                if not self.discovery_thread.isRunning():
                    start_discovery()
                else:
                    self.help_text.setText("Discovery process already running")
            else:
                self.help_text.setText("Can't do it when connected")
        except AttributeError:
            start_discovery()

    def emulate_button_slot(self):
        self.cnt = 0
        try:
            if self.bin_tracker.track_file.isRunning():
                self.bin_tracker.track_file.terminate()
                to_signal(self.emulation_panel.emulate_button.set_default_style_sheet)()
                return
        except AttributeError:
            pass
        bin_path = self.bin_file_panel.get_current_file()
        self.bin_tracker = BinTracker(bin_path, self.event_handler, to_signal(self.emulation_panel.emulate_button.blink))
        self.bin_tracker.start()

    def emulation_diffs_present_slot(self):
        self.send_sram_bytes.start()

    @thread_this_method()
    def send_sram_bytes(self):
        max_msg_len = 256 * 8   #single packet size
        msg_body = ''
        bytes_cnt = 0
        while self.bin_tracker.diffs:
            msg_body += self.bin_tracker.diffs.popitem()
            bytes_cnt += 1
            if len(msg_body) >= max_msg_len - 3:
                break
        result = self.send_message(message_id=MessageSender.ID.send_sram_bytes, body=msg_body, timeout=1)
        while result() is None:
            time.sleep(0.001)
        self.bin_tracker.resume()

    def tear_down_main_app(self):
        self.update_app_status_file()

    def load_last_status(self):
        config = configparser.ConfigParser()
        config.read(self.app_status_file)
        try:
            last_files = eval(config[self.last_bin_files_tag]['files'])
            self.last_browse_location = config[self.last_bin_files_tag]['browse_hist']
            self.bin_file_panel.combo_box.insertItems(0, last_files)
            if config[self.buttons_status_tag]['reload sram checkbox'] == 'True':
                self.emulation_panel.reload_sram_checkbox.setChecked(True)
            if config[self.buttons_status_tag]['auto open'] == 'True':
                self.emulation_panel.auto_open_checkbox.setChecked(True)
            if config[self.buttons_status_tag]['autoconnect'] == 'True':
                self.control_panel.autoconnect_checkbox.setChecked(True)
        except KeyError:
            pass

    def update_app_status_file(self):
        debug("Updating latest files list")
        last_files_list = self.bin_file_panel.combo_box.getItems()
        config = configparser.ConfigParser()
        config.read(self.app_status_file)
        config[self.last_bin_files_tag] = {
            'files': last_files_list,
            'browse_hist': self.bin_file_panel.last_browse_location
        }
        config[self.buttons_status_tag] = {
            'reload sram checkbox': self.emulation_panel.reload_sram_checkbox.isChecked(),
            'auto open': self.emulation_panel.auto_open_checkbox.isChecked(),
            'autoconnect': self.control_panel.autoconnect_checkbox.isChecked(),
        }
        with open(self.app_status_file, 'w') as cf:
           config.write(cf)

    def closeEvent(self, event):
        if event.type() == QEvent.Close:
            self.tear_down_main_app()
            app = QtGui.QApplication.instance()
            app.closeAllWindows()

    def destroyEvent(self, event):
        print "destroy"


def main(dev_version=False):
    import sys, os
    _stdout = sys.stdout
    _stderr = sys.stderr
    with open(os.path.join(LOG_PATH, 'stdout.txt'), 'w', buffering=16) as stdout, open(os.path.join(LOG_PATH, 'stderr.txt'), 'w', buffering=16) as stderr:
        if dev_version == False:
            sys.stderr = stderr
            sys.stdout = stdout
        app = QtGui.QApplication(sys.argv)
        if platform == 'Windows':
            app.setStyle(QtGui.QStyleFactory.create('Cleanlooks'))
        myapp = MainWindow()
        #myapp.setWindowIcon(QtGui.QIcon(os.path.join('spec', 'icon.ico')))
        myapp.setWindowIcon(QtGui.QIcon('icon.png'))
        #app.setWindowIcon(QtGui.QIcon(os.path.join('spec', 'icon.ico')))
        app.setWindowIcon(QtGui.QIcon(('icon.png')))
        myapp.show()
        app.exec_()
        sys.exit()
        sys.stdout = _stdout
        sys.stderr = _stderr

if __name__ == "__main__":
    main(dev_version=True)
