#!/usr/bin/python
"""
author: Rafal Miecznik
contact: ravmiecznk@gmail.com
created: 26.12.2020$
"""

from PyQt4 import QtGui
from objects_with_help import PushButton, CheckBox
from PyQt4.QtGui import QTextBrowser
import configparser

READ_SRAM_BTN_TIP           = "SRAM: this memory is visible to your ECU. This button will get its content." \
                            "\nBut beware that during read process Emulator is not accessible to ECU" \
                            "\nEmulation will stop"

TEST_SRAM_BTN_TIP           = "Perform test for write/read of random data for SRAM memory"

class TestPanel(QtGui.QWidget):
    def __init__(self, event_handler, app_status_file_path):
        QtGui.QWidget.__init__(self)
        self.buttons_status_tag = "BUTTONS STATUS"
        self.app_status_file_path = app_status_file_path
        self.event_handler = event_handler
        self.setWindowTitle("TEST PANEL")
        self.x_siz, self.y_siz = 600, 400

        self.read_sram_button = PushButton("READ SRAM", tip_msg=READ_SRAM_BTN_TIP)
        self.read_sram_button.clicked.connect(self.event_handler.read_sram_button_slot)

        self.test_sram_button = PushButton("TEST SRAM", tip_msg=TEST_SRAM_BTN_TIP)
        self.test_sram_button.clicked.connect(self.event_handler.test_sram_chip_slot)

        self.text_browser = QTextBrowser()

        self.digidiag_on_checkbox = CheckBox("Show dididiag data panels", tip_msg="Enable digidiag")
        self.digidiag_on_checkbox.clicked.connect(self.show_digidiag)
        config = configparser.ConfigParser()
        config.read(self.app_status_file_path)
        try:
            if config[self.buttons_status_tag]['digidiag_show'] == 'True':
                self.digidiag_on_checkbox.setChecked(True)
                self.show_digidiag()
        except KeyError:
            pass
        mainGrid = QtGui.QGridLayout()
        mainGrid.setSpacing(10)
        mainGrid.addWidget(self.read_sram_button,      0, 0)
        mainGrid.addWidget(self.test_sram_button,      0, 1)
        mainGrid.addWidget(self.digidiag_on_checkbox,  1, 0)
        mainGrid.addWidget(self.text_browser,          2, 0, 10, 2)
        self.setLayout(mainGrid)
        self.resize(self.x_siz, self.y_siz)

    def show_digidiag(self):
        if self.digidiag_on_checkbox.isChecked():
            self.event_handler.digidiag_show_event()
        else:
            self.event_handler.digidiag_hide_event()

    def update_app_status(self):
        config = configparser.ConfigParser()
        config.read(self.app_status_file_path)
        config[self.buttons_status_tag]['digidiag_show'] = str(self.digidiag_on_checkbox.isChecked())
        with open(self.app_status_file_path, 'w') as cf:
           config.write(cf)

    def text_append(self, text):
        self.text_browser.append(text)

    def closeEvent(self, event):
        self.event_handler.digidiag_hide_event()
        self.update_app_status()