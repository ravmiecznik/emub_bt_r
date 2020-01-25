"""
author: Rafal Miecznik
contact: ravmiecznk@gmail.com
"""

from message_handler.crc import crc
from io import BytesIO
from PyQt4 import QtCore, QtGui
from PyQt4.QtGui import QFileDialog
from PyQt4.QtCore import pyqtSignal
import os
import configparser
from main_window import ColorProgressBar
from gui_thread import SignalThread
from intel_hex_handler import intel_hex_parser
from gui_thread import GuiThread, thread_this_method
from event_handler import EventHandler, to_signal, general_signal_factory
import time
from setup_emubt import error, info, debug, warn
from loggers import create_logger, tstamp
from message_handler import MessageSender, MessageReceiver

stdout_log = create_logger("stdout")

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

        self.rx_message_buffer = dict() #this buffer wont't exceed number of maximum possible context ids in msg.id (0xffff)

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
        self.browse_button = QtGui.QPushButton("...")
        self.reflash_button = QtGui.QPushButton("REFLASH")
        self.cancel_button = QtGui.QPushButton("Cancel")
        self.browse_button.setMaximumSize(25, 25)
        self.browse_button.clicked.connect(self.select_file)
        self.reflash_button.clicked.connect(self.reflash)
        self.cancel_button.clicked.connect(self.close)

        #GRID
        mainGrid = QtGui.QGridLayout()
        mainGrid.setSpacing(10)
        mainGrid.addWidget(self.line_edit,      0, 0, 1, 5)
        mainGrid.addWidget(self.browse_button,  0, 5)
        mainGrid.addWidget(self.text_browser,   1, 0, 3, 5)
        mainGrid.addWidget(self.progress_bar,   4, 0, 1, 5)
        mainGrid.addWidget(self.cancel_button,  5, 0, 1, 1)
        mainGrid.addWidget(self.reflash_button, 5, 4, 1, 1)
        self.setLayout(mainGrid)

        self.resize(self.x_siz, self.y_siz)

    def get_raw_rx_buffer_slot(self):
        msg = self.message_receiver.get_message()
        if msg:
            self.rx_message_buffer[msg.context] = msg
        for context in self.rx_message_buffer:
            print "{}: {}".format(self.rx_message_buffer[context].context, self.rx_message_buffer[context].crc_check),
        print

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
        print "close"
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
            config[self.hex_file_path_tag] = {'path': file_path}
            with open(self.app_status_file, 'w') as cf:
                config.write(cf)
            self.last_hex_path = self.get_last_hex_file_path()
            self.line_edit.setText(self.last_hex_path)

    @thread_this_method()
    def increase_progress(self):
        for i in range(100):
            self.progress_bar.set_val_signal.emit(i)
            time.sleep(0.01)

    def reflash(self):
        self.progress_bar.setValue(0)
        self.increase_progress.start()





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