"""
author: Rafal Miecznik
contact: ravmiecznk@gmail.com
"""
import sys
sys.path.append('../')
import unittest
from PyQt4.QtGui import QApplication, QWidget
from PyQt4.QtCore import pyqtSignal, QEvent
import threading
from main import TestInterface
import time
import inspect
import os
import configparser
from event_handler import to_signal
from gui_thread import GuiThread

DOWNLOADED = 'DOWNLOADED'
APP_STATUS_FILE = 'app_status.sts'
FILE_LIST_TAG = "LAST BIN FILES"
RESOURCE = 'RESOURCE'

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


def wait_for(event, timeout=5, period=0.1):
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

class TestQApplication(unittest.TestCase):

    def test_if_connected(self):
        """
        connect button text turns to 'disconnect' when connected
        :return:
        """
        assert self.main_window.is_connected() == "disconnect"

    def test_if_sram_zero(self):
        to_signal(self.main_window.bin_file_panel.combo_box.clear)()
        to_signal(self.main_window.bin_file_panel.combo_box.clearEditText)()
        to_signal(self.main_window.read_sram_button_slot)()
        self.main_window.is_downloaded_file_present()
        self.main_window.get_current_file()
        file_path = self.main_window.get_current_file.qget()
        addr = 0
        with open(file_path) as f:
            chars = f.read()
            for c in chars:
                self.assertEqual(c, '\x00', "Sram file not zero at addr: {}".format(addr))
                addr += 0

    # def test_upload_bank(self):
    #     new_file = os.path.join(RESOURCE, '8VG60.bin')
    #     self.queue.put({'file_to_upload': new_file})
    #     to_signal(self.main_window.set_new_file_for_upload)()
    #     to_signal(self.main_window.save_button_slot)()
    #     self.wait_for_queue_event({'text_browser': "File transmitted in:"},
    #                               to_signal(self.main_window.get_text_browser_to_queue), timeout=15)




    @classmethod
    def setUpClass(cls):
        clean_downloaded_files()
        clean_app_status_files_list()

        connection_timeout = 10
        t0 = time.time()
        while cls.main_window.is_connected() != "disconnect":
            time.sleep(0.5)
            assert time.time() - t0 < connection_timeout, "Connection timeout"

        # cls.main_window.wipe_banks()
        # wait_for(lambda : "wiping done" in str(cls.main_window.console.console_text_browser.toPlainText()), period=1)

        cls.main_window.bank1set_slot()
        time.sleep(0.5)
        cls.main_window.get_active_bank_button()
        cls.queue = cls.main_window.queue
        wait_for(lambda: cls.main_window.get_active_bank_button() == 1)

    @classmethod
    def tearDownClass(cls):
        cls.main_window.disconnect()
        while cls.main_window.is_connected() != "Connect":
            time.sleep(0.5)
        time.sleep(1)
        to_signal(cls.main_window.close)()


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
    thread.join()
    sys.exit()