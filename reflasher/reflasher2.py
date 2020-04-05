"""
author: Rafal Miecznik
contact: ravmiecznk@gmail.com
"""

from PyQt4 import QtCore, QtGui
from PyQt4.QtGui import QFileDialog
from PyQt4.QtCore import pyqtSignal
import os
import configparser
from main_window import ColorProgressBar
from intel_hex_handler import intel_hex_parser
from gui_thread import thread_this_method
from event_handler import EventHandler, to_signal, general_signal_factory
import time
from loggers import create_logger, tstamp
from message_handler import MessageSender, MessageReceiver, RxMessage
import struct

stdout_log = create_logger("stdout")
PACKET_SIZE = 256*8

cwd = os.getcwd()
BROWSE_ICON = os.path.join(cwd, 'spec', 'browse.png')
print BROWSE_ICON

class TextBrowserInSubWindow(QtGui.QTextBrowser):
    append_sig = pyqtSignal(object, object)
    def __init__(self):
        QtGui.QTextBrowser.__init__(self)
        self.append_sig.connect(QtGui.QTextBrowser.append)

    def append(self, string):
        self.append_sig.emit(self, string)


class DummyEmulator:
    pass


class Reflasher(QtGui.QWidget):
    #def __init__(self, app_status_file, emulator, receive_data_thread=None, signal_on_close=None, message_sender=None):
    def __init__(self, app_status_file, emulator, receive_data_thread=None, signal_on_close=None):
        QtGui.QWidget.__init__(self)
        self.setWindowTitle("REFLASH")
        self.x_siz, self.y_siz = 600, 400
        self.reflash()

        self.rx_message_buffer = dict() #this buffer wont't exceed number of maximum possible context ids in msg.id (0xffff)
        self.packets = {}

        self.app_status_file = app_status_file
        self.last_hex_path = self.get_last_hex_file_path()
        self.flash_succeeded = False

        #INHERITED EMULATOR OBJECT
        self.emulator = emulator
        self.rx_buffer = self.emulator.raw_buffer
        self.set_event_handler()
        self.message_sender = MessageSender(self.emulator.send, self.rx_buffer)
        self.message_receiver = MessageReceiver(self.rx_buffer)

        #TEXT DISPLAY
        self.line_edit = QtGui.QLineEdit()
        self.text_browser = TextBrowserInSubWindow()
        self.progress_bar = ColorProgressBar(parent=self)
        font = QtGui.QFont('Courier New', 8)
        self.text_browser.setFont(font)
        self.text_browser.setFontPointSize(9)
        line_edit_text = self.last_hex_path if self.last_hex_path else "SELECT HEX FILE: press button---->"
        self.line_edit.setText(line_edit_text)

        self.text_browser.append("!WARNING!")
        self.text_browser.append("You are going to upload new firmware to EMUBT\n")

        #BUTTONS
        self.browse_button = QtGui.QPushButton()
        self.browse_button.setToolTip("Select file")
        self.browse_button.setMinimumWidth(100)

        self.browse_button.setIcon(QtGui.QIcon(BROWSE_ICON))
        self.reflash_button = QtGui.QPushButton("REFLASH")
        self.cancel_button = QtGui.QPushButton("Cancel")
        self.browse_button.setMaximumSize(25, 25)
        self.browse_button.clicked.connect(self.select_file)
        self.reflash_button.clicked.connect(self.check_selected_file)
        self.cancel_button.clicked.connect(self.close)

        #GRID
        mainGrid = QtGui.QGridLayout()
        mainGrid.setSpacing(10)
        mainGrid.addWidget(self.line_edit,      0, 0, 1, 5)
        mainGrid.addWidget(self.browse_button,  0, 5)
        mainGrid.addWidget(self.text_browser,   1, 0, 3, 6)
        mainGrid.addWidget(self.progress_bar,   4, 0, 1, 6)
        mainGrid.addWidget(self.cancel_button,  5, 0, 1, 1)
        mainGrid.addWidget(self.reflash_button, 5, 5, 1, 1)
        self.setLayout(mainGrid)
        self.__expected_version = None
        self.resize(self.x_siz, self.y_siz)

    def _find_version_of_hex_to_reflash(self, bin_file):
        version_strings = ["Version:R", "Version:V"]    #support variety alternative version strings
                                                        #returns first matching string
        for s in version_strings:
            version_location_pos = bin_file.find(s)
            version_location_pos_end = bin_file.find("\n", version_location_pos)
            if version_location_pos > 1:
                new_version = bin_file[version_location_pos:version_location_pos_end-1]
                return new_version

    def get_raw_rx_buffer_slot(self):
        """
        This slot is triggered by data reception object whenever new data is present in rx buffer
        :return:
        """
        msg = self.message_receiver.get_message()
        if msg:
            self.rx_message_buffer[msg.context] = msg
            if msg.id == RxMessage.RxId.txt:
                self.text_browser.append("E: {}".format(msg.msg))
                if self.__expected_version and self.__expected_version in msg.msg:
                    self.text_browser.append("\nReflashing done\nYou can close Reflasher window")
                    self.cancel_button.setText("CLOSE")

    def set_event_handler(self):
        self.old_eventhandler = self.emulator.event_handler
        self.reflasher_event_handler = EventHandler()
        self.reflasher_event_handler.add_event(self.get_raw_rx_buffer_slot)
        self.emulator.set_event_handler(self.reflasher_event_handler)

    def restore_old_event_handler(self):
        self.emulator.set_event_handler(self.old_eventhandler)

    def get_last_hex_file_path(self):
        config = configparser.ConfigParser()
        config.read(self.app_status_file)

        try:
            path = config['FLASH_HEX_FILE']['path']
            return path
        except KeyError:
            return ''

    def closeEvent(self, event):
        self.restore_old_event_handler()
        QtGui.QWidget.close(self)
        event.accept()


    def select_file(self):
        print 'select'
        start_dir = os.path.dirname(self.last_hex_path)
        file_path = QFileDialog.getOpenFileName(self, 'Select hex file',
                                                start_dir, "hex files (*.hex *.HEX)")
        if os.path.isfile(file_path):
            config = configparser.ConfigParser()
            config.read(self.app_status_file)
            config['FLASH_HEX_FILE'] = {'path': file_path}
            with open(self.app_status_file, 'w') as cf:
                config.write(cf)
            self.last_hex_path = self.get_last_hex_file_path()
            self.line_edit.setText(self.last_hex_path)


    def check_selected_file(self):
        try:
            file_path = self.line_edit.text()
            with open(file_path) as hex_file:
                hex_lines = hex_file.readlines()
                bin_segments = intel_hex_parser(hex_lines, self.text_browser.append)
                start_address = 0
                self.text_browser.append("Reflash with:\n{}\n".format(file_path))
                self.__expected_version = self._find_version_of_hex_to_reflash(bin_segments[start_address])
                self.text_browser.append("Version of new software: {}".format(self.__expected_version))
                self.bin_segments_to_packets(bin_segments[start_address])
                self.reflash.start()
        except IOError:
            self.text_browser.append("File not present or faulty:\n{}".format(file_path))


    def bin_segments_to_packets(self, bin_segments):
        cnt = 0
        for i in xrange(0, len(bin_segments), PACKET_SIZE):
            self.packets[cnt] = bin_segments[i:i+PACKET_SIZE]
            cnt += 1
        return self.packets

    @thread_this_method()
    def reflash(self):
        timeout = 30
        rxtimeout = 2
        self.progress_bar.set_val_signal.emit(0)
        num_of_packets = len(self.packets)
        t0 = time.time()
        context_to_packet_index_map = {}
        while self.packets:
            packet_index = self.packets.keys()[0]
            context = self.message_sender.send(MessageSender.ID.write_to_page, body=struct.pack('H', packet_index) + self.packets[packet_index])
            context_to_packet_index_map[context] = packet_index
            _t0 = time.time()
            while context not in self.rx_message_buffer:
                time.sleep(0.1)
                if time.time() - _t0 > rxtimeout:
                    break
            else:
                if self.rx_message_buffer[context].id == RxMessage.RxId.ack:
                    __packet_index = context_to_packet_index_map[context]
                    self.packets.pop(__packet_index)
                else:
                    self.text_browser.append("nack")
                self.progress_bar.set_val_signal.emit(100*float(num_of_packets-len(self.packets))/num_of_packets)
            if time.time() - t0 > timeout:
                self.text_browser.append("REFLASHING FAILED")
                return
        self.text_browser.append("REFLASHING FINISHED")
        self.text_browser.append("VERYFYING")
        self.text_browser.append("{}".format(time.time()-t0))
        self.message_sender.send(MessageSender.ID.run_main_app_btl)





if __name__ == "__main__":
    import sys
    dummy_emulator = DummyEmulator()
    dummy_emulator.raw_buffer = lambda x:x
    app = QtGui.QApplication(sys.argv)
    myapp = Reflasher('app_status.sts', emulator=dummy_emulator)
    myapp.show()
    app.exec_()
    # myapp.safe_close()
    sys.exit()
    sys.stdout = STDOUT