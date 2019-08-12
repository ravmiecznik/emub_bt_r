#!/usr/bin/env python
"""
author: Rafal Miecznik
contact: ravmiecznk@gmail.com
"""

import sys
sys.path.append('..')
import unittest
from PyQt4.QtGui import QApplication, QWidget
import main
import time
import threading
import os
import random, tempfile, string
import HtmlTestRunner
from test_interface import check_with_timeout
from collections import namedtuple


#TODO: add test for APPLY button in config_window, to check whenever bt address changes it will apply in configuration
#1) change address, APPLY, connectin should fail
#2) resotre correct address, APPLY, connection should succedd, help command should return help output

def assert_with_timeout(assertion, test, timeout=5, period=1, **kwargs):
    t0 = time.time()
    while time.time() - t0 < timeout:
        result = test() if callable(test) else test
        try:
            assertion(result, **kwargs)
            return
        except AssertionError:
            time.sleep(period)
    assertion(result, **kwargs)


def compare_two_files(p1, p2):
    with open(p1, 'rb') as f1, open(p2, 'rb') as f2:
        a, b = f1.read(), f2.read()
        return a == b


def create_random_bin():
    f = tempfile.NamedTemporaryFile(mode='w+b')
    for i in xrange(0x8000):
        f.write(chr(random.randint(0,0xff)))
    f.seek(0)
    return f


def step(s, *args, **kwargs):
    return dict(step=s, args=args, kwargs=kwargs)

def execute_steps_with_delay(*steps):
    for s in steps:
        step, args, kwargs = s.pop('step'), s.pop('args', ()), s.pop('kwargs', {})
        step(*args, **kwargs)
        time.sleep(0.5)


def randomString(stringLength=10):
    """Generate a random string of fixed length """
    letters = string.ascii_lowercase
    return ''.join(random.choice(letters) for i in range(stringLength))


class TestQApplication(unittest.TestCase):

    # def __init__(self, *args, **kwargs):
    #     self.test_if.connect_button.clicked.emit(1)
    #     assert_with_timeout(self.assertTrue, self.test_if.recevive_emulator_data_thread.isRunning, msg="FAIL", timeout=5, period=0.1)
    #     assert_with_timeout(self.assertTrue, self.test_if.is_bank_in_use_set, timeout=2)
    #     unittest.TestCase.__init__(self, *args, **kwargs)

    def run(self, *args, **kwargs):
        """
        Reset test_module inputs and check connection status before each test_module
        :param args:
        :param kwargs:
        :return:
        """
        self.test_image_path = os.path.join(os.path.dirname(__file__), 'test_image.bin')
        self.test_if.parent.receive_data_suceeded = False
        self.test_if.parent.send_data_suceeded = False
        self.assertTrue(self.test_if.is_connected())
        unittest.TestCase.run(self, *args, **kwargs)


    def test_store_and_read_bank(self):
        self.test_if.put_new_bin_file_path(self.test_image_path)
        self.test_if.click(self.test_if.buttons.save)
        self.assertTrue(self.test_if.is_send_data_succeeded())
        self.assertTrue(self.test_if.is_emulation_panel_unlocked())
        self.test_if.click(self.test_if.buttons.read_bank)
        self.assertTrue(self.test_if.is_receive_data_succeeded())
        received_current_file_path = self.test_if.get_received_file_path()
        self.assertTrue(compare_two_files(self.test_image_path, received_current_file_path),
                        msg='Files are different')

    def test_read_sram(self):
        self.test_if.put_new_bin_file_path(self.test_image_path)
        self.test_if.click(self.test_if.buttons.save)
        self.assertTrue(self.test_if.is_send_data_succeeded())
        self.assertTrue(self.test_if.is_emulation_panel_unlocked())
        self.test_if.click(self.test_if.buttons.read_sram)
        self.assertTrue(self.test_if.is_receive_data_succeeded())
        received_current_file_path = self.test_if.get_received_file_path()
        self.assertTrue(compare_two_files(self.test_image_path, received_current_file_path),
                        msg='Files are different')


    def test_set_bank_name(self):
        """
        try/except clause to try at least twice
        One fail in read of bank name is allowed
        :return:
        """
        rand_bin = create_random_bin()
        bin_path = rand_bin.name
        bank_name1 = randomString(5)
        bank_name2 = randomString(5)
        bank_name3 = randomString(5)
        def bank1_name_setting_test():
            self.test_if.click(self.test_if.buttons.bank1btn)
            self.test_if.enter_bank_name(bank_name1)
            time.sleep(0.5)
            self.assertEquals(self.test_if.get_bank_name(), bank_name1)

        def bank2_name_setting_test():
            self.test_if.click(self.test_if.buttons.bank2btn)
            self.test_if.enter_bank_name(bank_name2)
            time.sleep(0.5)
            self.assertEquals(self.test_if.get_bank_name(), bank_name2)

        def bank3_name_setting_test():
            self.test_if.click(self.test_if.buttons.bank3btn)
            self.test_if.enter_bank_name(bank_name3)
            time.sleep(0.5)
            self.assertEquals(self.test_if.get_bank_name(), bank_name3)

        def bank1_name_read_test():
            self.test_if.click(self.test_if.buttons.bank1btn)
            t0 = time.time()
            while time.time() - t0 < 2:
                try:
                    self.assertEquals(self.test_if.get_bank_name(), bank_name1)
                except AssertionError:
                    time.sleep(0.1)
            else:
                self.assertEquals(self.test_if.get_bank_name(), bank_name1)

        try:
            bank1_name_setting_test()
        except AssertionError:
            bank1_name_setting_test()

        try:
            bank2_name_setting_test()
        except AssertionError:
            bank2_name_setting_test()

        try:
            bank3_name_setting_test()
        except AssertionError:
            bank3_name_setting_test()

        try:
            bank1_name_read_test()
        except AssertionError:
            bank1_name_read_test()


    def tearDown(self):
        self.test_if.receive_data_suceeded = False
        self.test_if.send_data_suceeded = False


    @classmethod
    def tearDownClass(cls):
        cls.test_if.disconnect()
        cls.main_window.close()
        cls.main_app.exit()


def all_tests():
    import sys
    app = QApplication(sys.argv)
    main_window = main.MainWindow(is_test=True)
    main_window.show()

    main_window.connect_button.clicked.emit(1)

    TestQApplication.test_if = main_window.test_interface
    TestQApplication.main_window = main_window
    TestQApplication.main_app = app
    testRunner = HtmlTestRunner.HTMLTestRunner(output='html_report', report_name="EMUBT_test", add_timestamp=False)
    thread = threading.Thread(target=unittest.main, kwargs={'verbosity': 2, 'testRunner': testRunner})
    thread.start()
    app.exec_()

def test_suite():
    import sys
    app = QApplication(sys.argv)
    main_window = main.MainWindow()
    main_window.show()

    main_window.connect_button.clicked.emit(1)

    TestQApplication.test_if = main_window.test_interface
    TestQApplication.main_window = main_window
    TestQApplication.main_app = app
    import sys
    suite = unittest.TestSuite()
    suite.write = sys.stdout.write
    suite.flush = sys.stdout.flush
    suite.addTest(TestQApplication('test_config_change_and_apply'))
    testRunner = unittest.TextTestRunner(suite)
    thread = threading.Thread(target=testRunner.run, args=(suite,))
    thread.start()
    app.exec_()

if __name__ == "__main__":
    all_tests()
