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
import filecmp
import configparser
from event_handler import to_signal
from test_interface import TestInterface, test_logger


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
    ## SETUP ###########################################################################################################
    @classmethod
    def setUpClass(cls):
        clean_downloaded_files()
        reset_config_file()

        cls.main_window.connect_button.clicked.emit(1)
        cls.main_window.is_connected()

    @classmethod
    def tearDownClass(cls):
        time.sleep(1)
        to_signal(cls.main_window.disconnect)()
        cls.main_window.is_disconnected()
        time.sleep(1)
        to_signal(cls.main_window.close)()

    def setUp(self):
        to_signal(self.main_window.bin_file_panel.combo_box.clearEditText)()

    ## TESTS ###########################################################################################################
    def test_if_sram_zero(self):
        """
        Test if sram contains only zeros bytes after banks wiping
        :return:
        """
        self.main_window.wipe_banks()
        self.main_window.are_banks_wiped()
        self.main_window.bank1set_slot()
        self.main_window.is_bank1_set()
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
                addr += 1

    def test_upload_bank(self):
        """
        Send and receive binary file, fail if file differs after reception
        :return:
        """
        new_file = os.path.join(RESOURCE, 'random.bin')
        self.main_window.send_file_for_emulation(new_file)
        downloaded_file_path = self.main_window.download_flash_bank()
        are_identical = filecmp.cmp(new_file, downloaded_file_path, shallow=False)
        if not are_identical:
            with open(new_file) as n, open(downloaded_file_path) as d:
                nfile = n.read()
                dfile = d.read()
                addr = 0
                for pair in zip(nfile, dfile):
                    if pair[0] != pair[1]:
                        print "Diff @0x{:08X}: n0x{:02X} != d0x{:02X}".format(addr, ord(pair[0]), ord(pair[1]))
                    addr += 1
        assert are_identical, "Downloaded file is not the same as transmitted one: {} != {}".format(new_file, downloaded_file_path)

    def test_digdiag_transmission(self):
        """
        Test if digidiag transmission was applied to a file which has no digidiag implemented
        :return:
        """
        digidag = self.main_window.digiag_widget
        digidiag_capable_file = os.path.join(RESOURCE, '8VG60.bin')
        self.main_window.bank1set_slot()
        self.main_window.is_bank1_set()
        self.main_window.send_file_for_emulation(digidiag_capable_file)
        self.main_window.bank1set_slot()
        self.main_window.is_bank1_set()

        digidag.reset_frames_count()
        time.sleep(5)   #collect data from digidiag

        # check if data is being transmitted
        rx_frames_count = digidag.get_frames_count()
        assert rx_frames_count > 100, "To few data frames received from EMUBT: {}".format(rx_frames_count)

        #check if data is being transmitted and appropriate amount of different frames received
        num_of_frames_id = len(digidag.frames)
        assert num_of_frames_id >= 6, \
            "For 1 Map file there should be 10 different frames received, got: {}".format(num_of_frames_id)

        #test first frame
        manifold_pressure = ord(digidag.frames[0xff][2])
        assert manifold_pressure>0x75 and manifold_pressure<0x82, \
            "Manifold pressure out of expected range: 0x{:02X}".format(manifold_pressure)

        #test last frame
        rpm_h = ord(digidag.frames[0xfb][6])
        rpm_l = ord(digidag.frames[0xfb][7])
        rpm = (rpm_h << 8) + rpm_l
        assert rpm == 17664, "Wrong RPM value: {}".format(rpm)

    def test_live_emulation(self):
        """
        Test of live update of emulated file.
        Scenarion to be implemented:
        -Copy some temporary file
        -Upload the file
        -Enable Live emulation
        -Check if live emulation thread is running
        -Modify some bytes in the file
        -Download SRAM file
        -Compare SRAM with temporary file
        :return:
        """
        assert True #keep in passing at the moment


if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_window = TestInterface(is_test=True)
    main_window.show()

    TestQApplication.main_window = main_window

    suite = unittest.TestSuite()
    #define suite here
    for t in [
        TestQApplication.test_digdiag_transmission,
        TestQApplication.test_upload_bank,
    ]:
        suite.addTest(TestQApplication(t.__name__))
    runner = unittest.TextTestRunner(verbosity=2)
    def run_suite():
        runner.run(suite)

    thread = threading.Thread(target=run_suite)

    # thread = threading.Thread(target=unittest.main,
    #                           kwargs={'verbosity': 2},
    #                           args=['TestQApplication.test_digdiag_transmission'])
    thread.start()

    #testRunner = HtmlTestRunner.HTMLTestRunner(output='html_report', report_name="EMUBT_test", add_timestamp=False)
    #thread = threading.Thread(target=unittest.main, kwargs={'verbosity': 2, 'testRunner': testRunner})

    app.exec_()
    thread.join()
    sys.exit()