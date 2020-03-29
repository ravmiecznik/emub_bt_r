"""
author: Rafal Miecznik
contact: ravmiecznk@gmail.com

An auxiliary module to control and retrieve data from main window QT thread from a test_suite test thread.
"""

#append main module to PATH
import sys
sys.path.append('../')

import inspect
from main import MainWindow
from message_handler import MessageSender
from gui_thread import GuiThread
from event_handler import to_signal
import queue
import time
import os
from setup_emubt import LOG_PATH

#Main window related imports
from objects_with_help import GREEN_BACKGROUND_PUSHBUTTON
from loggers import create_logger

test_logger = create_logger('test_logger', log_path=LOG_PATH)

##### wait_for DECORATOR STUFF #########################################################################################
def __apply_queue_to_method(method, _queue, args, kwargs):
    """
    Wrapps a method so it is output is put into queue.
    """

    def invoke_method():
        _queue.put(method(*args, **kwargs))

    return invoke_method


def __do_until_with_timeout(self, test, _queue, invoke_method, timeout, sleep):
    t0 = time.time()
    self.general_signal_args_kwargs.emit(invoke_method, (), {})
    result = _queue.get(timeout=timeout)
    while not test(result) and time.time() - t0 < timeout:
        time.sleep(sleep)
        self.general_signal_args_kwargs.emit(invoke_method, (), {})
        result = _queue.get(timeout=timeout)
    assert test(result), inspect.getsource(test) + " " + str(result)
    return result

def wait_for(timeout=10, test=None, sleep=None):
    """
    A decorator function for automatic testing purposes.
    This decorator wraps the method, calls it and waits unitl provided test is True.
    After exiting while loop it will assert the "test" method. Basically after timeout assert check most probably will
    raise an exception by calling test(result).

    The test statement can be executed only in case when wrapped method puts result to queue argument.
    The queue is applied to method by __apply_queue_to_method.
    Wrapped method must belong to instance of Class which has general_signal_args_kwargs signal which accepts three
    object arguments. Those are used to pass: method, args, kwargs.
    Result of wrapped method can be accessd by qget attribute:

    @do_until(do_until_config_here)
    def some_method(self):
        return some_stuff

    output = some_method().qget(timeout=5)

    :param timeout: if test statement is not True (not test(result)) assertion will be checked, test step will fail
    :param test: an executable condition to check. Positive check must return True.
            e.g. test=os.path.isfile to check if
            returned by wrapped method path exists.
            By lambda expression if path is not None can be assured:
            test = lambda p: p is not None and os.path.isfile(p)
    :return: trigger containing wrapped method
    """
    if sleep is None:
        sleep = timeout/5

    if test is None:
        test = lambda r: r is None
    _queue = queue.Queue()
    def trigger(method):
        def wrapper(*args, **kwargs):
            invoke_method = __apply_queue_to_method(method, _queue, args, kwargs)
            self = args[0]
            test_logger.debug("Invoking: {}".format(method))
            result = __do_until_with_timeout(self, test, _queue, invoke_method, timeout, sleep)
            test_logger.debug("Invoking done: {} result: {}".format(method, result))
            #put back result and make it still available
            _queue.put(result)
            return _queue
        #result can be accessed by qget attribute
        wrapper.qget = _queue.get
        return wrapper
    return trigger

########################################################################################################################

def apply_queue(timeout=2):
    """
    Appy queue to method.
    :param object: depends how decorator is applied: without call it meas a wrapped method, with call like
                    @apply_queue() means it is timeout, default is 2
    :return:
    """

    #support of call like @apply_queue or @apply_queue() or @apply_queue(timeout=9)
    if type(timeout) is not int:
        _object = timeout
        timeout = 2

    _queue = queue.Queue()

    def qget():
        return _queue.get(timeout=timeout)

    def wrapper(*wargs, **wkwargs):
        if len(wargs) == 1:
            #wraps just a method
            method = wargs[0]
            def call(*args, **kwargs):
                self = args[0]
                args = args[1:]
                _queue.put((args, kwargs))
                return method(self, qget)
            return call
        else:
            self = wargs[0]
            wargs = wargs[1:]
            _queue.put((wargs, wkwargs))
            return _object(self, qget)

    return wrapper

class TestInterface(MainWindow):
    def __init__(self, *args, **kwargs):
        MainWindow.__init__(self, *args, **kwargs)
        self.digiag_widget.show()
        self.digidiag_window.show()
        self.queue = queue.Queue()


    def get_key_from_queue(self, key):
        elem = self.queue.get(timeout=2)
        if key in elem:
            return elem[key]
        else:
            self.queue.put(elem)    #put back not matching elem


    def get_active_bank_button(self):
        try:
            return [self.banks_panel.bank1pushButton.styleSheet(),
                   self.banks_panel.bank2pushButton.styleSheet(),
                   self.banks_panel.bank3pushButton.styleSheet()].index(GREEN_BACKGROUND_PUSHBUTTON) + 1
        except ValueError as e:
            print e
            return None

    @wait_for(test=lambda text: text == "disconnect", timeout=15)
    def is_connected(self, queue=None):
        return    str(self.connect_button.text())

    @wait_for(test=lambda text: text == "Connect", timeout=15)
    def is_disconnected(self):
        return str(self.connect_button.text())

    @wait_for(test=lambda isfile: isfile is True, timeout=25)
    def is_downloaded_file_present(self):
        return os.path.isfile(str(self.bin_file_panel.get_current_file()))

    @wait_for(test=lambda p: p and os.path.isfile(p), timeout=25)
    def get_current_file(self):
        return self.bin_file_panel.get_current_file()

    def wipe_banks(self):
        self.message_sender.send(MessageSender.ID.wipe_banks)

    @wait_for(test=lambda console_text: "wiping done" in console_text, timeout=15, sleep=1)
    def are_banks_wiped(self):
        return str(self.console.console_text_browser.toPlainText())

    @wait_for(test=lambda bank: bank == 1, timeout=2, sleep=0.5)
    def is_bank1_set(self):
        return self.get_active_bank_button()

    def send_file_for_emulation(self, file_path):
        to_signal(self.console.clear)()
        self.insert_new_file_signal.emit(file_path)
        wait_for(timeout=1, test=lambda path: os.path.isfile(path) if path else False)\
            (lambda arg: self.bin_file_panel.get_current_file())(self)

        to_signal(self.save_button_slot)()
        wait_for(timeout=25, test=lambda text: "File transmitted in" in text)(
            lambda arg: str(self.console.console_text_browser.toPlainText()))(self)

    @wait_for(timeout=20, test=lambda text: "File received in:" in text)
    def wait_for_file_reception(self):
        return str(self.console.console_text_browser.toPlainText())

    def download_flash_bank(self):
        self.bin_file_panel.combo_box.clearEditText()
        to_signal(self.console.clear)()
        self.read_bank_button_slot()
        return self.get_current_file().get()

    def download_sram(self):
        self.bin_file_panel.combo_box.clearEditText()
        to_signal(self.console.clear)()
        self.read_sram_button_slot()
        return self.get_current_file().get()



    #     path = self.get_key_from_queue('file_to_upload')
    #     if path:
    #         self.insert_new_file_signal.emit(path)
    #
    # def get_text_browser_to_queue(self):
    #     self.queue.put({'text_browser': self.console.console_text_browser.toPlainText()})

    def disconnect(self):
        self.connect_button.clicked.emit(1)
