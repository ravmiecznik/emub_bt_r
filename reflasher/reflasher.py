"""
author: Rafal Miecznik
contact: ravmiecznk@gmail.com
"""

from message_handler.crc import crc
from message_handler import Message
from io import BytesIO
from PyQt4 import QtCore, QtGui
from PyQt4.QtGui import QFileDialog
from PyQt4.QtCore import pyqtSignal
import os
import configparser
from intel_hex_handler import intel_hex_parser
from my_gui_thread import GuiThread, thread_this_method
from event_handler import EventHandler, to_signal
import time
from setup_emubt import error, info, debug, warn
from call_tracker import method_call_track

class TextBrowserInSubWindow(QtGui.QTextBrowser):
    append_sig = pyqtSignal(object, object)
    def __init__(self):
        QtGui.QTextBrowser.__init__(self)
        self.append_sig.connect(QtGui.QTextBrowser.append)

    def append(self, string):
        self.append_sig.emit(self, string)

#@method_call_track
class Reflasher(QtGui.QWidget):
    def __init__(self, app_status_file, emulator, signal_on_close=None):
        QtGui.QWidget.__init__(self)
        self.setWindowTitle("REFLASH")
        self.x_siz, self.y_siz = 400, 200
        mainGrid = QtGui.QGridLayout()
        mainGrid.setSpacing(10)
        self.emulator = emulator
        self.signal_on_close = signal_on_close
        self.app_status_file = app_status_file
        self.line_edit = QtGui.QLineEdit()
        self.browse_button = QtGui.QPushButton("...")
        self.reflash_button = QtGui.QPushButton("REFLASH")
        self.cancel_button = QtGui.QPushButton("Cancel")
        self.browse_button.setMaximumSize(25, 25)
        self.text_browser = TextBrowserInSubWindow()
        font = QtGui.QFont('Courier New', 8)
        self.text_browser.setFont(font)
        #self.text_browser.setFontPointSize(9)
        self.hex_file_path_tag = 'FLASH_HEX_FILE'
        self.browse_button.clicked.connect(to_signal(self.select_file))
        self.reflash_button.clicked.connect(to_signal(self.reflash))
        self.cancel_button.clicked.connect(to_signal(self.close))
        mainGrid.addWidget(self.line_edit,      0, 0, 1, 5)
        mainGrid.addWidget(self.browse_button,  0, 5)
        mainGrid.addWidget(self.text_browser,   1, 0, 4, 5)
        mainGrid.addWidget(self.cancel_button,  5, 0, 1, 1)
        mainGrid.addWidget(self.reflash_button, 5, 4, 1, 1)
        self.flash_succeeded = False
        self.rx_buffer = self.emulator.rx_buffer
        self.setLayout(mainGrid)
        self.last_hex_path = self.get_last_hex_file_path()
        line_edit_text = self.last_hex_path if self.last_hex_path else "SELECT HEX FILE: press button---->"
        self.line_edit.setText(line_edit_text)
        self.configure_event_handler()
        self.send_bin_image_thread()
        self.check_if_bootloader_ready()
        self.check_if_bootloader_ready.start()
        self.get_packetsize()
        self.resize(self.x_siz, self.y_siz)
        self.reflash_button.setDisabled(True)

    @thread_this_method()
    def check_if_bootloader_ready(self, timeout=2):
        self.text_browser.append("Checking bootloader...")
        self.send("run_bootloader")
        t0 = time.time()
        while time.time() - t0 < timeout:
            time.sleep(0.2)
            if 'BOOTLOADER' in self.rx_buffer:
                debug("bootloader ready")
                self.rx_buffer.flush()
                self.get_packetsize.start()
                return True
        warn('Bootloader activation failed. Rxbuffer contetnt: "{}"'.format(self.rx_buffer.read()))
        return False

    def send(self, cmd):
        self.emulator.send(cmd + '\n')

    @thread_this_method(delay=0.1)
    def get_packetsize(self, timeout=2):
        self.get_packetsize_max_retx = 1
        t0 = time.time()
        self.rx_buffer.flush()
        self.send('packetsize')
        content = self.rx_buffer.peek()
        eot = chr(10) + chr(13)         #end of transmission
        while eot not in content:
            time.sleep(0.1)
            if time.time() - t0 > timeout:
                self.text_browser.append("Timeout in {}".format(self.get_packetsize.__name__))
                return False
            content = self.rx_buffer.peek()
        packetsize = self.rx_buffer.read()
        try:
            self.packetsize = int(packetsize[0: packetsize.index(eot)])
            self.reflash_button.setDisabled(False)
            self.text_browser.append("Packetsize: {}".format(self.packetsize))
            self.text_browser.append("Bootloader ready")
        except ValueError:
            if self.get_packetsize_max_retx == 1:
                self.get_packetsize.start()
                self.get_packetsize_max_retx -= 1
                return
            self.text_browser.append("It looks like connection is bad, can't continue")
            self._prepare_to_quit()

    def configure_event_handler(self):
        """
        Replace old event handler in emulator with temporary event handler for reflasher
        After exit old event handler is restored
        :return:
        """
        #configure new event handler
        self.old_event_handler = self.emulator.event_handler
        self.reflasher_event_handler = EventHandler()
        #self.reflasher_event_handler.add_event(to_signal(lambda:None), "get_emu_rx_buffer_slot")
        #self.reflasher_event_handler.add_event(to_signal(lambda: None), "get_raw_rx_buffer_slot")
        self.emulator.set_event_handler(self.reflasher_event_handler)


    def close(self):
        QtGui.QWidget.close(self)


    def __close(self):
        #if not self.flash_succeeded:
        #    self.send('run_main_app')
        self.emulator.rx_buffer.read()
        self.emulator.set_event_handler(self.old_event_handler)
        self.signal_on_close()

    def closeEvent(self, event):
        self.__close()
        event.accept()

    def get_last_hex_file_path(self):
        config = configparser.ConfigParser()
        config.read(self.app_status_file)

        try:
            path = config[self.hex_file_path_tag]['path']
            return path
        except KeyError:
            return ''

    def select_file(self):
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

    def reflash(self):
        self.rx_buffer.flush()
        self.bin_image = self.parse_hex_file()[0]
        self.bin_size = len(self.bin_image)
        self.bin_image = self.bin_image + '\xEE'*(self.packetsize - (self.bin_size%self.packetsize))   #pad image
        self.bin_size = len(self.bin_image)
        self.expected_version = self._find_version_of_hex_to_reflash(self.bin_image)
        if not self.expected_version:
            self.text_browser.append("This file is not EMU BT hex file")
            self.text_browser.append("Can't continue")
            self.send('run_main_app')
            return
        self.resize(self.x_siz, self.y_siz + 100)
        self.send('write_p:{size} {addr}'.format(addr=0, size=len(self.bin_image)))
        if self.wait_for_resp("ready"):
           self.send_bin_image_thread.start()

    def wait_for_resp(self, resp, nresp='nak', timeout=2):
        t0 = time.time()
        while time.time() - t0 < timeout:
            _resp = self.rx_buffer.peek().strip()
            if _resp[0:len(resp)] == resp:
                self.rx_buffer.flush()
                return True
            elif _resp[0:len(nresp)] == nresp:
                return False
            time.sleep(0.1)
        _resp = self.rx_buffer.read()
        self.text_browser.append("Timeout waiting for '{}' signal, got {}".format(resp, _resp))
        return 'dtx'

    def _poor_condition_msg(self):
        self.text_browser.append("Connection condition may be poor")
        self.text_browser.append("Try again from closer distance")

    @thread_this_method()
    #TODO: add ack verification
    def send_bin_image_thread(self):
        bin_image = BytesIO()
        bin_image.write(self.bin_image)
        bin_image.seek(0)
        packet = bin_image.read(self.packetsize)
        num_of_packets = self.bin_size/self.packetsize
        max_retx = 3
        bytes_total = 0
        while packet:
            bytes_total += len(packet)
            self.text_browser.append("send packet {} of len {}, remaining bytes: {}".format(num_of_packets, len(packet), self.bin_size-bytes_total))
            crc_sum = crc(packet)
            self.emulator.send(packet + crc_sum)
            resp = self.wait_for_resp("ack")
            if resp == 'dtx':
                self.text_browser.append("Got unexpected response\nquitting")
                self._poor_condition_msg()
                return
            while resp == False:
                self.text_browser.append("Packet nacked, trying retx: {}".format(max_retx))
                crc_sum = crc(packet)
                self.emulator.send(packet + crc_sum)
                resp = self.wait_for_resp("ack")
                max_retx -= 1
                if max_retx == 0:
                    self.text_browser.append("Flashing failed")
                    self._poor_condition_msg()
                    return
                time.sleep(0.1)
            max_retx = 5
            packet = bin_image.read(self.packetsize)
            num_of_packets -= 1
        self.send('run_main_app')
        self.text_browser.append("DONE")
        self.verify_version()

    def _prepare_to_quit(self):
        self.reflash_button.setDisabled(True)
        self.cancel_button.setText("CLOSE")
        self.cancel_button.setFocus(True)

    def verify_version(self):
        self.text_browser.append("Check if reflash suceeded")
        time.sleep(1)
        self.rx_buffer.flush()
        Message('digidiag_off', positive_signal=to_signal(self.__get_version))

    def __get_version(self):
        Message(id=Message.ID.rxflush, positive_signal=to_signal(self.get_version))

    def get_version(self):
        Message('version')
        if self.wait_for_resp(self.expected_version, timeout=1):
            self.text_browser.append("Found installed version: {}".format(self.expected_version))
            self.text_browser.append("Reflashing OK")
            self.text_browser.append("You can close Reflasher window")
            self.flash_succeeded = True
            self._prepare_to_quit()
        else:
            self.text_browser.append("Reflash FAIL, bootloader will remain active after reset")


    def _find_version_of_hex_to_reflash(self, bin_file):
        str_len = len("Version:R0.00")
        version_location = bin_file.find("Version:R")
        if version_location > 1:
            new_version = bin_file[version_location:version_location+str_len]
            self.text_browser.append("Version of new software: {}".format(new_version))
            return new_version

    def parse_hex_file(self):
        if not os.path.isfile(self.line_edit.text()):
            self.select_file()
        with open(self.line_edit.text()) as hex_file:
            hex_lines = hex_file.readlines()
            bin_segments = intel_hex_parser(hex_lines, self.text_browser.append)
        return bin_segments



if __name__ == "__main__":
    import sys
    app = QtGui.QApplication(sys.argv)
    myapp = Reflasher('app_status.sts', None)
    myapp.show()
    app.exec_()
    # myapp.safe_close()
    sys.exit()
    sys.stdout = STDOUT