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
import queue
import time
import os

#Main window related imports
from objects_with_help import GREEN_BACKGROUND_PUSHBUTTON


def __apply_queue_kwarg(method, _queue, kwargs):
    """
    Applies queue keyword argument to method decorated by do_until decorator
    :param method: decorated method
    :param _queue: a queue.Queue() object
    :param kwargs: kwargs of 'method'
    :return: None, modify kwargs by reference
    """

    try:
        if kwargs['queue'] is None:
            kwargs['queue'] = _queue
        else:
            raise Exception("Can't apply {decor} for method: {method}, queue already defined".format(do_until.__name__,
                                                                                                     method.__name__))
    except KeyError:
        kwargs['queue'] = _queue

def do_until(timeout=10, test=None, sleep=1):
    """
    A decorator function for automatic testing purposes.
    This decorator wraps the method, calls it and waits unitl provided test is True.
    After exiting while loop it will assert the "test" method. Basically after timeout assert check most probably will
    raise an exception by calling test(result).

    The test statment can be executed only in case when wrpapped method puts result to queue keyworded argument.
    Wrapped method must belong to instance of Class which has general_signal_args_kwargs signal which accepts three
    object arguments. Those are used to pass: method, args, kwargs.
    This decorator applies also a keyworded argument 'queue' to access applied queue more easily.
    :param timeout: if test statement is not True (not test(result)) assertion will be checked, test step will fail
    :param test: an executable condition to check. Positive check must return True.
            e.g. test=os.path.isfile to check if
            returned by wrapped method path exists.
            By lambda expression if path is not None can be assured:
            test = lambda p: p is not None and os.path.isfile(p)
    :return: trigger containing wrapped method
    """
    if test is None:
        test = lambda r: r is None
    _queue = queue.Queue()
    def trigger(method):
        def wrapper(*args, **kwargs):
            __apply_queue_kwarg(method, _queue, kwargs)

            #check until timeout
            t0 = time.time()
            self = args[0]
            self.general_signal_args_kwargs.emit(method, args, kwargs)
            result = _queue.get(timeout=timeout)
            while not test(result) and time.time() - t0 < timeout:
                time.sleep(sleep)
                self.general_signal_args_kwargs.emit(method, args, kwargs)
                result = _queue.get(timeout=timeout)

            #check the test
            assert test(result), inspect.getsource(test) + " " + str(result)

            #put back result and make it still available
            _queue.put(result)
        #result can be accessed by qget attribute
        wrapper.qget = _queue.get
        return wrapper
    return trigger

class TestInterface(MainWindow):
    def __init__(self, *args, **kwargs):
        MainWindow.__init__(self, *args, **kwargs)
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

    @do_until(test=lambda text: text == "disconnect", timeout=15)
    def is_connected(self, queue=None):
        queue.put(
            str(self.connect_button.text())
        )

    @do_until(test=lambda text: text == "Connect", timeout=15)
    def is_disconnected(self, queue=None):
        queue.put(
            str(self.connect_button.text())
        )

    @do_until(test=lambda isfile: isfile is True, timeout=25)
    def is_downloaded_file_present(self, queue=None):
        queue.put(
            os.path.isfile(str(self.bin_file_panel.get_current_file()))
        )

    @do_until(test=lambda p: p and os.path.isfile(p))
    def get_current_file(self, queue=None):
        queue.put((
            self.bin_file_panel.get_current_file())
        )

    def wipe_banks(self):
        self.message_sender.send(MessageSender.ID.wipe_banks)

    @do_until(test=lambda console_text: "wiping done" in console_text, timeout=15, sleep=1)
    def are_banks_wiped(self, queue=None):
        queue.put(
            str(self.console.console_text_browser.toPlainText())
        )

    @do_until(test=lambda bank: bank == 1, timeout=2, sleep=0.5)
    def is_bank1_set(self, queue=None):
        queue.put(
            self.get_active_bank_button()
        )

    #
    # def set_new_file_for_upload(self):
    #     path = self.get_key_from_queue('file_to_upload')
    #     if path:
    #         self.insert_new_file_signal.emit(path)
    #
    # def get_text_browser_to_queue(self):
    #     self.queue.put({'text_browser': self.console.console_text_browser.toPlainText()})

    def disconnect(self):
        self.connect_button.clicked.emit(1)
