"""
author: Rafal Miecznik
contact: ravmiecznk@gmail.com
"""

import unittest
import sys
from PyQt4.QtGui import QApplication, QWidget
from PyQt4.QtCore import pyqtSignal, QEvent
import threading
from main import TestInterface
import time
import inspect
import os
import configparser
from gui_thread import GuiThread

DOWNLOADED = 'DOWNLOADED'
APP_STATUS_FILE = 'app_status.sts'
FILE_LIST_TAG = "LAST BIN FILES"

def clean_downloaded_files():
    files = os.listdir(DOWNLOADED)
    for f in files:
        f = os.path.join(DOWNLOADED, f)
        print "removing: {}".format(f)
        os.remove(f)

def clean_app_status_files_list():
    print("Clean latest files list")
    config = configparser.ConfigParser()
    config.read(APP_STATUS_FILE)
    config[FILE_LIST_TAG] = {
        'files': '[]',
        'browse_hist': ''
    }
    #check it later
    # config[self.buttons_status_tag] = {
    #     'reload sram checkbox': self.emulation_panel.reload_sram_checkbox.isChecked(),
    #     'auto open': self.emulation_panel.auto_open_checkbox.isChecked(),
    #     'autoconnect': self.control_panel.autoconnect_checkbox.isChecked(),
    # }
    with open(APP_STATUS_FILE, 'w') as cf:
        config.write(cf)

class TestQApplication(unittest.TestCase):

    def wait_for(self, event, timeout=5, period=0.1):
        """
        callable even
        :param event: callable, maybe expression in lambda or any callable which returns True/Flase
        :param timeout:
        :return:
        """
        t0 = time.time()
        while time.time() - t0 < timeout:
            if event():
                return
            time.sleep(period)
        try:
            msg = "Timeout {} for event: {}".format(timeout, inspect.getsource(event))
        except TypeError:
            msg = "Timeout {} for event: {}".format(timeout, event.__name__)
        assert False, msg

    def run(self, *args, **kwargs):
        t0 = time.time()
        max_timeout = 10
        while self.main_window.is_connected() != "disconnect":
            time.sleep(0.5)
            if time.time() - t0 > max_timeout:
                self.fail("Connection timeout")
        unittest.TestCase.run(self, *args, **kwargs)

    def test_if_connected(self):
        """
        connect button text turns to 'disconnect' when connected
        :return:
        """
        assert self.main_window.is_connected() == "disconnect"

    def test_read_sram(self):
        # TODO:
        #upload file
        self.main_window.bin_file_panel.combo_box.clear()
        self.main_window.bin_file_panel.combo_box.clearEditText()
        self.main_window.read_sram_button_slot()
        self.wait_for(
            lambda :os.path.isfile(str(self.main_window.bin_file_panel.combo_box.currentText())),
            timeout=10, period=1
        )
        #TODO:
        #compare file

    @classmethod
    def setUpClass(cls):
        clean_downloaded_files()
        clean_app_status_files_list()

    @classmethod
    def tearDownClass(cls):
        cls.main_window.disconnect()
        while cls.main_window.is_connected() != "Connect":
            time.sleep(0.5)
        time.sleep(1)
        cls.main_window.close()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_window = TestInterface(is_test=True)
    main_window.show()

    main_window.connect_button.clicked.emit(1)

    TestQApplication.test_if = main_window.test_interface
    TestQApplication.main_window = main_window
    TestQApplication.main_app = app
    #testRunner = HtmlTestRunner.HTMLTestRunner(output='html_report', report_name="EMUBT_test", add_timestamp=False)
    #thread = threading.Thread(target=unittest.main, kwargs={'verbosity': 2, 'testRunner': testRunner})
    thread = threading.Thread(target=unittest.main, kwargs={'verbosity': 2})
    thread.start()
    app.exec_()
    sys.exit()