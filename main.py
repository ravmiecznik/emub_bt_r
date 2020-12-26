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
from io import BytesIO
from bin_handler import bin_repr
from random import randint
import sys
import filecmp
from setup_emubt import logger, info, debug, error, warn, EMU_BT_PATH, LOG_PATH, BIN_PATH
from loggers import create_logger
from panels import ControlPanel, EmulationPanel, BanksPanel, BinFilePanel
from emulator import Emulator
from PyQt4.Qt import PYQT_VERSION_STR
from PyQt4 import QtCore, QtGui
from PyQt4.QtCore import QMutex
from PyQt4.QtGui import QLabel
from PyQt4.QtCore import pyqtSignal, QEvent
from main_window import ColorProgressBar
from objects_with_help import HelpTip, GREEN_BACKGROUND_PUSHBUTTON, CheckBox
from gui_thread import thread_this_method, GuiThread, SignalThread
from bt_discover import bt_search
from console import Console
from call_tracker import method_call_track
from reflasher import Reflasher
from event_handler import EventHandler, to_signal, general_signal_factory
from message_handler import MessageSender, MessageReceiver, RxMessage, TxTimeout
from config_window import ConfigWindow, Config, ConfigSettings
from procedures import WritePackets, ReadSramProcedure, ReadBankProcedure
from test_module import TestInterface
from digidiag import DigiDiag, DigidiagWindow
import message_box
from plotter import Plotter
from bin_tracker import BinTracker
from auxiliary_module import MeanCalculator, WindowGeometry
if platform == "Linux":
    import queue
else:
    import Queue as queue
import sys, os, subprocess
import configparser
import time, struct
import textwrap
import traceback
from bin_handler import BinFilePacketGenerator, BinSenderInvalidBinSize
from set_pin_form import SetPinWindow
from banks_handler import BanksHandler
from freemem import FreeMemPlotter
from test_panel.test_panel import TestPanel

print "PYQT: {}".format(PYQT_VERSION_STR)

BACKGROUND = "background-color: rgb({},{},{})"
GREEN_STYLE_SHEET = BACKGROUND.format(154, 252, 41)
GREY_STYLE_SHEET = BACKGROUND.format(48, 53, 58)

SETTINGS_PATH = EMU_BT_PATH


def compare_bin_files(file1, file2, out=sys.stdout):
    with open(file1, 'rb') as f1, open(file2, 'rb') as f2:
        addr = 0
        f1_c, f2_c = f1.read(1), f2.read(1)
        while len(f1_c) and len(f2_c):
            if f1_c != f2_c:
                print >>out, "DIFF: ${:08X}: {:2X} != {:2X}".format(addr, ord(f1_c), ord(f2_c))
            f1_c, f2_c = f1.read(1), f2.read(1)
            addr += 1


class BinCompare:
    def __init__(self, file_1, file_2=None):
        self.__file_1 = file_1
        self.__file_2 = file_2

    def compare(self, file_2=None):
        if file_2 is not None:
            self.__file_2 = file_2
        if self.__file_2 is None:
            raise Exception("file_2 not provided")
        are_equal = filecmp.cmp(self.__file_1, self.__file_2, shallow=False)
        if not are_equal:
            diff = BytesIO()
            compare_bin_files(self.__file_1, self.__file_2, out=diff)
            diff.seek(0)
            return diff.read()
        else:
            return "Files are the same\n{}\n{}".format(self.__file_1, self.__file_2)


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


class SentMessageContainer():
    """
    A buffer with limited size to store sent messages threads
    It protects to destroy sent message thread while it is running
    """
    def __init__(self, size=20):
        self.container = size * [None]
        self.__index = 0
        self.__size = size


    def append(self, message_thread):
        for i, thread in enumerate(self.container):
            debug("{}: {}".format(i, thread))
            if not isinstance(thread, GuiThread):
                self.container[i] = message_thread
                debug("add new tx msg thread at index {}: {}".format(i, thread))
                return message_thread
            elif thread.isFinished() is True:
                debug("replace old tx msg thread at index {}: {}".format(i, thread))
                self.container[i] = message_thread
                return message_thread
        return None


@method_call_track
class MainWindow(QtGui.QMainWindow, ConfigSettings):
    help_tip_signal = pyqtSignal(object)
    gui_communication_signal = pyqtSignal(object)
    test_panel_text_append_signal = pyqtSignal(object)
    update_config_file_signal = pyqtSignal(object)
    insert_new_file_signal = pyqtSignal(object)
    set_banks_panel_bank_name_signal = pyqtSignal(object)
    config_window_apply_signal = pyqtSignal()
    general_signal = pyqtSignal(object)
    general_signal_args_kwargs = pyqtSignal(object, object, object)
    handle_rx_message_signal = pyqtSignal(object)
    set_pin_signal = pyqtSignal(object)
    #TODO: create a procedure which will examine timeout in rx/tx procedure, according to its output set timeouts in procedures and send messange, this should be perofremd once in first start of application
    def __init__(self, is_test=False):
        print 'PATH', EMU_BT_PATH
        self.sent_message_container = SentMessageContainer()
        self.mutex = QMutex()
        self.__response_time = 1    #big overhead for initial value
        self.__receive_data_period = 0.0001
        self.bank_in_use = None
        self.is_test = is_test
        self.config_path = SETTINGS_PATH
        if platform != 'Linux':
            self.config_path = self.config_path.replace('/', '\\')
        QtGui.QMainWindow.__init__(self)
        self.setWindowTitle("EMU BT")
        x_siz, y_siz = 600, 700

        #self.horizontalLayout = QtGui.QHBoxLayout()
        self.main_grid = QtGui.QGridLayout()
        self.main_grid.setSpacing(10)
        self.centralwidget = QtGui.QWidget(self)
        self.event_handler = EventHandler()
        general_signal_factory.signal = self.general_signal_args_kwargs
        SignalThread.general_signal = self.general_signal_args_kwargs

        self.last_bin_files_tag = "LAST BIN FILES"
        self.buttons_status_tag = "BUTTONS STATUS"

        self.setCentralWidget(self.centralwidget)

        self.help_text = QLabel(self.centralwidget, max_text_size=(x_siz/4.8, 4))
        self.help_text.setMaximumWidth(x_siz)
        self.help_text.raise_()

        self.update_config_file_signal.connect(self.update_config_file)
        self.config_window_apply_signal.connect(self.config_window_apply_slot)
        self.event_handler.message = self.gui_communication_signal.emit
        self.handle_rx_message_signal.connect(self.handle_rx_message)

        self.event_handler.add_event(self.update_config_file_signal.emit, self.update_config_file.__name__)
        self.event_handler.add_event(self.gui_communication_signal.emit, 'communicate')
        self.event_handler.add_event(self.command_line_slot)
        self.event_handler.add_event(to_signal(self.connect_button_slot))
        self.event_handler.add_event(to_signal(self.reflash_button_slot))
        self.event_handler.add_event(to_signal(self.discover_emu_bt_slot))
        self.event_handler.add_event(to_signal(self.estimate_response_time_slot))
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
        self.event_handler.add_event(to_signal(self.set_pin_button_slot))
        self.event_handler.add_event(to_signal(self.digidiag_show_event))
        self.event_handler.add_event(to_signal(self.digidiag_hide_event))
        self.event_handler.add_event(to_signal(self.test_sram_chip_slot))

        self.set_pin_signal.connect(self.set_pin_slot)
        ConfigSettings.__init__(self)

        self.control_panel = ControlPanel(self.centralwidget, event_handler=self.event_handler)

        #self.banks_panel = BanksPanel(self.centralwidget, event_handler=self.event_handler)
        # CONSOLE--------------------------------------------------------------------------------
        self.console = Console(self.centralwidget, event_handler=self.event_handler)
        # CONSOLE--------------------------------------------------------------------------------

        self.bin_file_panel = BinFilePanel(self.centralwidget, event_handler=self.event_handler,
                                           app_status_file=self.app_status_file, max_width=x_siz+10)

        # create discovery thread in init---------------------------------------------------------
        bt_device_to_search = 'EMUBT'
        self.discovery_thread = GuiThread(process=bt_search, args=(bt_device_to_search, self.event_handler),
                                          action_when_done=to_signal(self.discovery_thread_teardown))
        self.blink_discovery_btn()
        # create discovery thread in init---------------------------------------------------------

        self.digidiag_window = DigidiagWindow()

        self.gui_communication_signal.connect(self.console_communication_pipe_slot)
        self.setup_emulator()

        self.banks_handler = BanksHandler(self, self.general_signal_args_kwargs, message_sender=self.send_message,
                                          event_handler=self.event_handler)
        self.banks_panel = self.banks_handler.banks_panel
        self.connect_signals()

        self.progress_bar = ColorProgressBar(parent=self)

        # allow_read_sram = self.read_allow_read_sram_option()
        if is_test:
            allow_read_sram = True
        # self.emulation_panel = EmulationPanel(self.centralwidget, read_sram_allowed=allow_read_sram)
        self.emulation_panel = EmulationPanel(self.centralwidget)

        self.config_window = ConfigWindow(self.config_file_path, self.config_window_apply_signal)
        self.tx_packet_size = self.read_tx_packetsize()

        self.event_handler.add_event(to_signal(self.save_button_slot))

        if self.is_test == True:
            self.test_interface = TestInterface(self)
            self.control_panel.autoconnect_checkbox.setChecked(False)

        self.message_receiver = MessageReceiver(self.emulator.raw_buffer)
        self.rx_message_buffer = dict()

        self.create_threads()
        self.connect_button = self.control_panel.connect_button

        HelpTip.set_static_help_tip_slot_signal(self.help_tip_signal)
        #self.horizontalLayout.addWidget(self.bin_file_panel)

        self.main_grid.addWidget(self.control_panel,   0, 0, 2, 1)
        self.main_grid.addWidget(self.emulation_panel, 0, 2, 2, 1)
        self.main_grid.addWidget(self.banks_panel,     0, 4, 2, 1)
        self.main_grid.addWidget(self.bin_file_panel,  5, 0, 1, 6)
        self.main_grid.addWidget(self.console,         6, 0, 4, 6)
        self.main_grid.addWidget(self.help_text,      13, 0, 1, 6)
        self.centralwidget.setLayout(self.main_grid)

        self.raw_rx_buffer = self.emulator.raw_buffer
        self.rx_buffer = self.emulator.raw_buffer

        self.event_handler.add_event(to_signal(self.read_bank_button_slot), 'read_bank_button_slot')
        self.event_handler.add_event(to_signal(self.read_sram_button_slot), 'read_sram_button_slot')
        self.emulation_panel.set_event_handler(self.event_handler)

        self.freemem_plotter = FreeMemPlotter(self.message_sender)

        self.disable_objects_for_transmission_signal()
        self.load_last_status()
        self.__restore_digidiag = True
        if self.control_panel.autoconnect_checkbox.isChecked():
            self.connect_button_slot()
        self.enable_test_panel_checkbox = CheckBox("enable test panel", tip_msg="Enable test panel")
        self.enable_test_panel_checkbox.clicked.connect(self.enable_test_panel_checkbox_clicked_slot)
        self.enable_test_panel_checkbox.setStyleSheet(QtCore.QString("QCheckBox{color: red;}"))
        self.digidiag_slot()
        self.resize(x_siz, y_siz)
        self.show()

    def resizeEvent(self, event):
        self.bin_file_panel.combo_box.setFixedWidth(event.size().width()*0.7)

    def initUI(self):
        QtGui.QApplication.setStyle(QtGui.QStyleFactory.create('Cleanlooks'))

    def __send_message(self, m_id, body='NULL', timeout=0.3, re_tx=3):
        self.rx_buffer.flush()
        context = self.message_sender.send(m_id, body=body)
        time.sleep(timeout)
        while context not in self.rx_message_buffer and re_tx > 0:
            context = self.message_sender.send(m_id, body=body)
            re_tx -= 1
            debug("ReTx: {}, {}".format(MessageSender.ID.translate_id(m_id), re_tx))
            time.sleep(timeout)
        else:
            try:
                return self.rx_message_buffer[context].crc_check
            except KeyError:
                return None

    def estimate_response_time_slot(self):
        self.disable_objects_for_transmission_signal()
        self.estimate_response_time.set_delay(0)
        self.send_message(message_id=MessageSender.ID.dummy)
        time.sleep(0.5)
        self.estimate_response_time.start()

    @thread_this_method(delay=2)
    def estimate_response_time(self):
        num_of_checks = 16
        self.gui_communication_signal.emit("Response time was not calculated")
        self.gui_communication_signal.emit("Calculating response time...\n")
        self.disable_objects_for_transmission_signal()
        self.progress_bar.set_title("CHECKING RESPONSE TIME")
        to_signal(self.progress_bar.display).emit()
        timeout = 15     #maximum allowed timeout, if it is exceeded there must be something wrong about bluetooth connection
        mean = MeanCalculator()
        for i in xrange(num_of_checks):
            t0 = time.time()
            context = self.message_sender.send(MessageSender.ID.get_bank_packet, body=struct.pack('B', i))
            self.gui_communication_signal.emit("\n{}:{}".format(self.estimate_response_time, context))
            while context not in self.rx_message_buffer:
                time.sleep(0.1)
                if time.time() - t0 > timeout:
                    self.gui_communication_signal.emit("{}: timeout exceeded".format(self.estimate_response_time.__name__))
                    to_signal(self.progress_bar.hide)()
                    return
            self.progress_bar.set_val_signal.emit(int((float(num_of_checks)-i)/num_of_checks*100))
            mean.count(time.time() - t0)
            self.gui_communication_signal.emit(self.rx_message_buffer[context])
            self.gui_communication_signal.emit("Response time: {}\n".format(mean.calc()))
        mean_response_time = mean.calc() * 1.3

        self.gui_communication_signal.emit("\nMEAN RESPONSE TIME: {}".format(mean_response_time))
        Config(self.config_file_path).updade_config_file('APPSETTINGS', 'response_time', "{:.2f}".format(mean_response_time))
        self.__response_time = mean_response_time
        to_signal(self.progress_bar.hide).emit()
        self.enable_objects_after_transmission_signal()

    def estimate_rcv_chunk_size_for_emulator(self):
        timeout = 5
        max_tests = 2048
        old_chunk_size = self.emulator.get_rcv_chunk_size()
        self.plotter = Plotter(self, title="ESTIMATE RCV CHUNK SIZE", x_label="chunk size", y_label="time [ms]")
        self.plotter.set_max_x(max_tests + 10)
        self.plotter.show()
        self.progress_bar.set_title("Remaining...")
        to_signal(self.progress_bar.display).emit()

        def update_thread():
            for x in xrange(1, max_tests, 4):
                if self.plotter.isHidden():
                    self.gui_communication_signal.emit("Check chunk size terminated")
                    return
                tmean = MeanCalculator()
                chunk_size = x
                self.emulator.set_rcv_chunk_size(chunk_size)
                result_ok = True
                for _ in xrange(3):
                    t0 = time.time()
                    context = self.message_sender.send(MessageSender.ID.get_bank_packet, body=struct.pack('B', 1))
                    while context not in self.rx_message_buffer:
                        time.sleep(0.01)
                        if time.time() - t0 > timeout:
                            self.gui_communication_signal.emit("Chunk size check failed for: {}".format(x))
                            result_ok = False
                            break
                    time_elapsed = time.time() - t0
                    tmean.count(time_elapsed)
                self.progress_bar.set_val_signal.emit(int((float(max_tests) - x) / max_tests * 100))
                if result_ok:
                    self.plotter.update_plot_xy_signal.emit(chunk_size, tmean.calc()*1000)
            try:
                self.gui_communication_signal.emit("MAX: {}".format(self.plotter.get_max()))
                self.gui_communication_signal.emit("MIN: {}".format(self.plotter.get_min()))
            except ValueError:
                pass
            to_signal(self.progress_bar.hide)()
            self.emulator.set_rcv_chunk_size(old_chunk_size)
        self.tmp = GuiThread(update_thread)
        self.tmp.start()

    def send_message(self, message_id, body='NULL', timeout=None, re_tx=3):

        #set timeout according to estimated __response_time
        if timeout is None:
            timeout = self.__response_time

        #the container keeps the thread alive, otherwise it would be killed once this method exits
        message_thread = self.sent_message_container.append(
            GuiThread(self.__send_message, args=(message_id, body, timeout, re_tx))
        )
        if message_thread is None:
            self.gui_communication_signal.emit("TX message buffer overflow...")
            return None
        else:
            message_thread.start()
        return message_thread

    def set_pin_button_slot(self):
        """
        Opens pin setup window
        :return:
        """
        if self.emulator.connected:
            self.tmp = SetPinWindow(self.set_pin_signal)

    def set_pin_slot(self, pin):
        """
        Sends acutal pin
        :return:
        """
        self.message_sender.send(MessageSender.ID.set_pin, body=pin)

    def read_sram_button_slot(self):
        self.message_sender.send(MessageSender.ID.rxflush)
        self.read_sram = ReadSramProcedure(self, retx_timeout=self.__response_time)
        self.read_sram.read_thread.start()
        return self.read_sram.read_thread

    def read_bank_button_slot(self):
        #self.message_sender.send(MessageSender.ID.rxflush)
        self.read_bank = ReadBankProcedure(self, retx_timeout=self.__response_time)
        self.read_bank.read_thread.start()

    def save_button_slot(self):
        bin_path = self.bin_file_panel.get_current_file()
        try:
            bin_packets = BinFilePacketGenerator(bin_path, packet_size=self.tx_packet_size)
        except IOError as e:
            self.gui_communication_signal.emit("{}: {}".format(e.strerror, e.filename))
            raise e
        except BinSenderInvalidBinSize as e:
            self.gui_communication_signal.emit('{} {}'.format(e.__class__, e.message))
            self.combo_box.removeByStr(bin_path)
            self.bin_file_panel.update_app_status_file()
            message_box("This is not 27c256 bin image: {}".format(bin_path))
            raise e
        self.write_packets = WritePackets(self, bin_packets, retx_timeout=self.__response_time)
        self.write_packets.write_thread.start()
        return self.write_packets.write_thread

    def generate_random_bin(self):
        self.gui_communication_signal.emit("Generating random file")
        eeprom_size = 0x8000
        random_sram_image_path = os.path.join(BIN_PATH, "random.bin")
        with open(random_sram_image_path, 'wb') as f:
            for _ in range(eeprom_size):
                f.write(chr(randint(0, 255)))
        return random_sram_image_path

    def watch_thread(self, thread):
        while thread.isRunning():
            time.sleep(1)
            print thread.isRunning()
            print thread

    def test_sram_chip_slot(self):
        """
        Generate random bin file,
        Initiate bin compare object,
        upload random bin,
        trigger read_and_compare_random_sram_files
        :return:
        """
        random_image_path = self.generate_random_bin()
        self.bin_compare = BinCompare(random_image_path)
        self.bin_file_panel.insert_new_file(random_image_path)
        self.thread = self.save_button_slot()
        self.thread.action_when_done(self.read_and_compare_random_sram_files)

    def read_and_compare_random_sram_files(self):
        """
        trigger compare_random_sram_files
        bin_compare object was initialized before in test_sram_chip_slot
        trigger compare_random_sram_files
        :return:
        """
        time.sleep(0.5)
        self.read_thread = self.read_sram_button_slot()
        self.read_thread.action_when_done(self.compare_random_sram_files)

    def compare_random_sram_files(self):
        received_sram_file = self.bin_file_panel.get_current_file()
        diff = self.bin_compare.compare(received_sram_file)
        to_signal(self.test_panel.text_browser.clear)()
        self.general_signal_args_kwargs.emit(self.test_panel.text_browser.append, ("SRAM random test", ), {})
        self.test_panel_text_append_signal.emit(diff)

    def setup_emulator(self):
        self.port, self.address = self.read_emubt_port_address_config()
        rcv_chunk_size = self.read_emubt_rcv_chunk_size()
        self.emulator = Emulator(self.port, self.address, timeout=self.__receive_data_period/2, rcv_chunk_size=rcv_chunk_size)
        self.emulator.set_event_handler(self.event_handler)
        self.message_sender = MessageSender(self.emulator.send, self.emulator.raw_buffer)

    def config_window_apply_slot(self):
        """
        reload emulator related objects
        :return:
        """
        if not self.emulator.connected:
            self.setup_emulator()
            self.connection_thread = GuiThread(self.__connection_thread,
                                               action_when_done=to_signal(self.set_connection_status))
            self.recevive_emulator_data_thread = GuiThread(process=self.emulator.receive_data,
                                                           period=self.__receive_data_period)
        else:
            rcv_chunk_size = self.read_emubt_rcv_chunk_size()
            self.emulator.set_rcv_chunk_size(rcv_chunk_size)
        self.__response_time = float(self.config_window.config['APPSETTINGS']['response_time'].replace(',', '.'))
        self.tx_packet_size = self.read_tx_packetsize()



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


    @thread_this_method(period=0.1)
    def refresh_digidiag_display(self):
        self.digidiag_window.refresh()


    def get_raw_rx_buffer_slot(self):
        msg = self.message_receiver.get_message()
        if msg:
            self.handle_rx_message_signal.emit(msg)

    def handle_rx_message(self, msg):
        while msg:
            self.rx_message_buffer[msg.context] = msg
            banks = ['bank1set', 'bank2set', 'bank3set']
            if msg.id == RxMessage.RxId.txt:   #free text
                self.handle_rx_txt_message(msg.msg)
            elif msg.id == RxMessage.RxId.dbg:
                debug("Emulator: {}".format(msg.msg))
                debug("emulator debug: {}".format(msg.msg))
            elif msg.id == RxMessage.RxId.bank_name and 'bankname:' in msg.msg:
                bank_name = msg.msg.split(':')[1]
                self.set_banks_panel_bank_name_signal.emit(bank_name)
            elif msg.id == RxMessage.RxId.bank_in_use and msg.msg in banks:
                self.set_bank_in_use(banks.index(msg.msg))
            elif msg.id == RxMessage.RxId.dgframe:
                self.feed_digidiag(msg.msg)
            elif msg.id == RxMessage.RxId.pin_change_pending:
                self.gui_communication_signal.emit(msg.msg)
                self.gui_communication_signal.emit("   ")
                self.gui_communication_signal.emit("----------------------------------------------------------------------")
                self.gui_communication_signal.emit("            !!Going to disconnect to set the PIN!!")
                self.gui_communication_signal.emit("1) YOU NEED TO RESTART EMUBT BOARD (ignition off->2seconds->on)")
                self.gui_communication_signal.emit("2) AFTER BOARD WAS RESTARTED YOU NEED TO REMOVE EMUBT FROM YOUR SYSTEM")
                self.gui_communication_signal.emit("   AND CONNECT BACK, THE SYSTEM WILL PROMPT FOR NEW PIN")
                self.gui_communication_signal.emit("----------------------------------------------------------------------")
                self.gui_communication_signal.emit("   ")
                time.sleep(1)
                self.connect_button_slot()
            elif msg.id == RxMessage.RxId.banks_info:
                self.banks_handler.update_bank_info(msg)
            elif msg.id == RxMessage.RxId.freemem:
                self.freemem_plotter.update_xy(int(msg.msg))
            msg = self.message_receiver.get_message()



    def handle_rx_txt_message(self, txt_message):
        self.gui_communication_signal.emit("E: {}".format(txt_message))
        if txt_message == "bootloader3":
            self.reflash_app_slot()
        elif '!!!DEBUG VERSION!!!' in txt_message:
            self.show_enable_test_panel_checkbox()

    def digidiag_show_event(self):
        self.digiag_widget.show()
        self.digidiag_window.show()

    def digidiag_hide_event(self):
        self.digiag_widget.hide()
        self.digidiag_window.hide()

    def show_enable_test_panel_checkbox(self):
        config = configparser.ConfigParser()
        config.read(self.app_status_file)
        self.main_grid.addWidget(self.enable_test_panel_checkbox, 14, 0, 1, 6)
        if config[self.buttons_status_tag]['enable_test_panel'] == 'True':
            self.enable_test_panel_checkbox.setChecked(True)
            self.enable_test_panel_checkbox_clicked_slot()

    def enable_test_panel_checkbox_clicked_slot(self):
        if self.enable_test_panel_checkbox.isChecked():
            self.test_panel = TestPanel(self.event_handler, self.app_status_file)
            self.test_panel.show()
            self.test_panel_text_append_signal.connect(self.test_panel.text_append)
        elif hasattr(self, "test_panel") and self.test_panel.isVisible() and not self.enable_test_panel_checkbox.isChecked():
            self.test_panel.close()

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
                self.send_message(MessageSender.ID.set_bank_name, body=bank_name)
        except AttributeError:
            self.banks_panel.disable_active_button()
            self.send_message(MessageSender.ID.set_bank_name, body=bank_name, timeout=1.5)
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
            self.message_sender.send(m_id=MessageSender.ID.txt_message, body=cmd)

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
            self.event_handler.digidiag_show_event()
        elif cmd == "frames":
            self.digiag_widget.show()
        elif cmd == 'hsk':
            self.send_message(MessageSender.ID.handshake)
        elif cmd == 'd':
            self.message_sender.send(m_id=MessageSender.ID.disable_btlrd)
        elif cmd == 's':
            self.send_message(MessageSender.ID.set_bank_name, body='rafal')
        elif cmd == 'i':
            self.digidiag_slot()
        elif cmd == 'dfc':
            self.send_message(MessageSender.ID.dgf_code_check, timeout=1)
        elif cmd == 'check chunk size':
            self.estimate_rcv_chunk_size_for_emulator()
        elif cmd == 'enad':
            self.send_message(MessageSender.ID.digidag_enable)
        elif cmd == 'disd':
            self.send_message(MessageSender.ID.digidag_disable)
        elif cmd == 'tests':
            import unittest
            unittest.main()
            #TestEMUBT().run()
        elif cmd == 'wipebanks':
            self.message_sender.send(MessageSender.ID.wipe_banks)
        elif cmd == 'boots':
            self.message_sender.send(MessageSender.ID.bootloader_old)
        elif cmd == 'banksi':
            self.message_sender.send(MessageSender.ID.get_banks_info)
        elif cmd == "rstb":
            self.message_sender.send(MessageSender.ID.reset_banks_info)
        elif cmd == "freemem":
            self.freemem_plotter.show()
            self.freemem_plotter.freemem_request_thread.start()
        else:
            self.gui_communication_signal.emit("unsuported command")


    def reload_sram(self):
        self.send_message(MessageSender.ID.reload_sram)

    def send_help_cmd_slot(self):
        self.send_message(MessageSender.ID.handshake)

    def send_resetemu_slot(self):
        self.send_message(MessageSender.ID.reset)
        self.digiag_widget.frames = dict()

    def read_emubt_rcv_chunk_size(self):
        config = Config(self.config_file_path)
        try:
            rcv_chunk_size = int(config.read_config()['BLUETOOTH']['rcv_chunk_size'])
        except (KeyError, ValueError):
            config.updade_config_file('BLUETOOTH', 'rcv_chunk_size', '258')
            return self.read_emubt_rcv_chunk_size()
        return rcv_chunk_size

    def read_emubt_port_address_config(self):
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

    def read_calculated_response_time_config(self):
        config = configparser.ConfigParser()
        config.read(self.config_file_path)
        default_resp_time = 1
        try:
            response_time = float(config['APPSETTINGS']['response_time'].replace(',', '.'))
        except (KeyError, ValueError) as e:
            response_time = default_resp_time
        return response_time


    # def read_allow_read_sram_option(self):
    #     config = configparser.ConfigParser()
    #     config.read(self.config_file_path)
    #     try:
    #         allow = config['APPSETTINGS']['allow_read_sram'].upper()
    #         return allow == 'TRUE'
    #     except KeyError:
    #         return False

    def read_tx_packetsize(self):
        tx_packet_size = "{}".format(258 * 8)
        try:
            _tx_packet_size = self.config_window.config['APPSETTINGS']['tx_packet_size']
            allowed_values = ['{}'.format(256 * i) for i in xrange(8, 0, -1)]
            if _tx_packet_size in allowed_values:
                return int(_tx_packet_size)
        except KeyError:
            self.config_window.config['APPSETTINGS']['tx_packet_size'] = tx_packet_size
        return int(tx_packet_size)


    def reflash_button_slot(self):
        """
        handle_rx_message method will trigger reflasher window if bootloader3 txt repsonse received
        :return:
        """
        msg = "!!!WARNING!!!\n" \
              "You are about to upload new firmware to EMUBT board.\n" \
              "This is not about EEPROM emulation !!!\n" \
              "Are you sure you want to update the board ?\n"
        detailed_msg = "If you want to send binary file for emulation use UPLOAD button.\n" \
                       "Option you chosen writes new version of firmware to EMUBT board.\n" \
                       "You are going to upgrade EMUBT version."
        decision = message_box.message_box(msg=msg, detailed_msg=detailed_msg,
                                           buttons= message_box.Cancel | message_box.Yes, icon=message_box.Warning)
        if decision == "Yes":
            self.message = self.send_message(MessageSender.ID.bootloader, timeout=2, re_tx=0)

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
        self.reflasher = Reflasher(app_status_file=self.app_status_file, serial_connection=self.emulator)
        self.reflasher.show()

    def digidiag_slot(self):
        self.digiag_widget = DigiDiag()

    def feed_digidiag(self, frame):
        try:
            self.digiag_widget.feed_with_data(frame)
            self.digidiag_window.feed_data(frame)
            if len(self.digidiag_window.frames) > 3 and not self.refresh_digidiag_display.isRunning():
                self.refresh_digidiag_display.start()
        except AttributeError:
            traceback.print_exc()

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
        self.gui_communication_signal.emit("Updating config file:")
        for k in kwargs:
            self.gui_communication_signal.emit("{} {}".format(k, kwargs[k])),
        ConfigWindow(self.config_file_path,
                     apply_signal=self.config_window_apply_signal).update_config_file_BLUETOOTH(**kwargs)
        self.config_window = ConfigWindow(self.config_file_path,
                                          apply_signal=self.config_window_apply_signal)
        self.port, self.address = self.read_emubt_port_address_config()

    def connect_signals(self):
        self.help_tip_signal.connect(self.help_text.setText)
        self.general_signal.connect(self.general_signal_slot)
        self.general_signal_args_kwargs.connect(self.general_signal_slot_args_kwargs)
        self.disable_objects_for_transmission_signal = to_signal(self.__disable_objects_for_transmission)
        self.enable_objects_after_transmission_signal = to_signal(self.__enable_objects_after_transmission)
        self.insert_new_file_signal.connect(self.bin_file_panel.insert_new_file)
        self.set_banks_panel_bank_name_signal.connect(self.banks_panel.put_bank_name)

    def general_signal_slot_args_kwargs(self, object, args=(), kwargs={}):
        object(*args, **kwargs)

    #TODO: to be replaced by general_signal_slot_args_kwargs
    def general_signal_slot(self, object):
        object()

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
        self.refresh_digidiag_display()
        self.estimate_response_time()

    def set_connected(self):
        self.blink_connect_thread.terminate()
        self.connect_button.setText("disconnect")
        self.recevive_emulator_data_thread.start()
        self.recevive_emulator_data_thread.resume()
        self.enable_objects_after_transmission_signal()
        self.tmp_thread = GuiThread(process=to_signal(self.connect_button.set_green_style_sheet))
        self.tmp_thread.start()
        self.send_message(message_id=MessageSender.ID.get_bank_in_use)
        self.message_sender.send(MessageSender.ID.get_banks_info)
        self.__response_time = self.read_calculated_response_time_config()
        self.send_help_cmd_slot()

    def set_disconnected(self):
        self.disable_objects_for_transmission_signal()
        GuiThread.suspend_all_threads()
        self.connect_button.setText("Connect")
        self.connect_button.set_default_style_sheet()
        self.emulator.disconnect()

    def set_connection_status(self):
        if self.emulator.get_connection_status() == True:
            self.set_connected()
            #TODO: temporary
            #self.digiag_widget.show()
            #self.digidiag_window.show()
        else:
            self.set_disconnected()

    def connect_button_slot(self):
        if self.port is None and self.address is None:
            self.gui_communication_signal.emit("There is no configuration for EMUBT")
            self.gui_communication_signal.emit("Generating config file...")
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
        x_offset = -400
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
        """
        Thread for LIVE emulation
        :return:
        """
        max_msg_len = 256 * 8   #single packet size
        msg_body = ''
        bytes_cnt = 0
        while self.bin_tracker.diffs:
            msg_body += self.bin_tracker.diffs.popitem()
            bytes_cnt += 1
            if len(msg_body) >= max_msg_len - 3:
                break
        thread = self.send_message(message_id=MessageSender.ID.send_sram_bytes, body=msg_body, timeout=self.__response_time)
        while thread.returned() is None:
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
        config[self.last_bin_files_tag]['files'] = str(last_files_list)
        config[self.last_bin_files_tag]['browse_hist'] = self.bin_file_panel.last_browse_location

        config[self.buttons_status_tag]['reload sram checkbox'] = str(self.emulation_panel.reload_sram_checkbox.isChecked())
        config[self.buttons_status_tag]['auto open'] = str(self.emulation_panel.auto_open_checkbox.isChecked())
        config[self.buttons_status_tag]['autoconnect'] = str(self.control_panel.autoconnect_checkbox.isChecked())
        config[self.buttons_status_tag]['enable_test_panel'] = str(self.enable_test_panel_checkbox.isChecked())
        with open(self.app_status_file, 'w') as cf:
           config.write(cf)

    def closeEvent(self, event):
        if event.type() == QEvent.Close:
            self.close()

    def close(self):
            self.tear_down_main_app()
            app = QtGui.QApplication.instance()
            app.closeAllWindows()

    def destroyEvent(self, event):
        print "destroy"


def main(dev_version=False):
    import sys
    app = QtGui.QApplication(sys.argv)
    if platform == 'Windows':
        app.setStyle(QtGui.QStyleFactory.create('Cleanlooks'))
    myapp = MainWindow()
    window_icon = os.path.join('spec', 'icon.png')
    myapp.setWindowIcon(QtGui.QIcon(window_icon))
    app.setWindowIcon(QtGui.QIcon((window_icon)))
    #myapp.show()
    app.exec_()
    sys.exit()


if __name__ == "__main__":
    main(dev_version=True)
    #compare_bin_files('/home/rafal/EMU_BTR_FILES/DOWNLOADED/3MAP.bin', '/home/rafal/git/emu_bt_r/test_suite/RESOURCE/3MAP.bin')
