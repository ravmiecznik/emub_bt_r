"""
author: Rafal Miecznik
contact: ravmiecznk@gmail.com

There are available test frameworks for QT GUIs but none can display the GUI and perform a test.
This approach solves the problem.

How it is solved:
    A MainWindow is a main thread of the test, QT will not allow to control main GUI applicatoin with another thread.
    A test being executed is run as another thread: it controls MainWindow by clicking buttons, sending signals
    and providing the data into it and retrieving some data back. Accessing any graphical object of MainWindow can't
    be done directly. Signals and queues must be used !!!


    app = QApplication(sys.argv)                        <-  create QApplication as for most of QT Guis
    main_window = TestInterface(is_test=True)           <-  here is a main window being tested. To make it easy to controll
                                                            it is good idea to create some test interface which is subclass of
                                                            your MainWindow
    main_window.show()                                  <-  display the window


    TestQApplication.main_window = main_window          <-  Make main window accessible for test suite, here it is done
                                                            by composition

    thread = threading.Thread(target=unittest.main, kwargs={'verbosity': 2})    <- this is a test suite thread
    thread.start()                                      <- It starts here

    app.exec_()                                         <-  Main app is started just after
    thread.join()
    sys.exit()

tearDownClass should close the main window otherwise whole process will never stop by itself, only closing main window
will terminate all processes:

    @classmethod
    def tearDownClass(cls):
        some_teardown_actions
        to_signal(cls.main_window.close)()      <-final close !

"""

#append main module to PATH
import sys
sys.path.append('../')

import unittest
from PyQt4.QtGui import QApplication, QWidget
import threading
from main import TestInterface
import time
import os
import configparser
from event_handler import to_signal
from test_interface import TestInterface

DOWNLOADED = 'DOWNLOADED'
APP_STATUS_FILE = 'app_status.sts'
FILE_LIST_TAG = "LAST BIN FILES"
RESOURCE = 'RESOURCE'

def clean_downloaded_files():
    """
    Remove old test artifacts
    :return:
    """
    files = os.listdir(DOWNLOADED)
    for f in files:
        f = os.path.join(DOWNLOADED, f)
        print "removing: {}".format(f)
        os.remove(f)

def reset_config_file():
    """
    Prepare starting configuration
    :return:
    """
    print("Clean latest files list")
    config = configparser.ConfigParser()
    config.read(APP_STATUS_FILE)
    config[FILE_LIST_TAG] = {
        'files': '[]',
        'browse_hist': '',
        'autoconnect': 'False',
        'auto open': 'False',
        'reload sram checkbox': 'False'
    }

    with open(APP_STATUS_FILE, 'w') as cf:
        config.write(cf)


class TestQApplication(unittest.TestCase):

    def test_if_sram_zero(self):
        to_signal(self.main_window.bin_file_panel.combo_box.clear)()
        to_signal(self.main_window.bin_file_panel.combo_box.clearEditText)()
        time.sleep(0.5)
        to_signal(self.main_window.read_sram_button_slot)()
        self.main_window.is_downloaded_file_present()
        self.main_window.get_current_file()
        file_path = self.main_window.get_current_file.qget()
        addr = 0
        with open(file_path) as f:
            chars = f.read()
            for c in chars:
                self.assertEqual(c, '\x00', "Sram file not zero at addr: {}".format(addr))
                addr += 1

    def test_upload_bank(self):
        new_file = os.path.join(RESOURCE, '8VG60.bin')
        self.queue.put({'file_to_upload': new_file})
        to_signal(self.main_window.set_new_file_for_upload)()
        to_signal(self.main_window.save_button_slot)()
        self.wait_for_queue_event({'text_browser': "File transmitted in:"},
                                  to_signal(self.main_window.get_text_browser_to_queue), timeout=15)




    @classmethod
    def setUpClass(cls):
        clean_downloaded_files()
        reset_config_file()

        cls.main_window.connect_button.clicked.emit(1)
        cls.main_window.is_connected()

        cls.main_window.wipe_banks()
        cls.main_window.are_banks_wiped()

        cls.main_window.bank1set_slot()
        cls.main_window.is_bank1_set()


    @classmethod
    def tearDownClass(cls):
        to_signal(cls.main_window.disconnect)()
        cls.main_window.is_disconnected()
        time.sleep(1)
        to_signal(cls.main_window.close)()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_window = TestInterface(is_test=True)
    main_window.show()

    TestQApplication.main_window = main_window
    thread = threading.Thread(target=unittest.main, kwargs={'verbosity': 2})
    thread.start()

    #testRunner = HtmlTestRunner.HTMLTestRunner(output='html_report', report_name="EMUBT_test", add_timestamp=False)
    #thread = threading.Thread(target=unittest.main, kwargs={'verbosity': 2, 'testRunner': testRunner})

    app.exec_()
    thread.join()
    sys.exit()