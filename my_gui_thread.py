"""
author: Rafal Miecznik
contact: ravmiecznk@gmail.com
"""
import traceback
from main_logger import logger, info, tstamp, error, warn, ExceptionLogger
from collections import OrderedDict
import time
from PyQt4.QtCore import QThread
from call_tracker import shallow_track_class_calls

threads_exception_logger = ExceptionLogger("threads_exceptions")

def thread_this_method(**thread_kwargs):
    """
    This is decorator.
    It will turn given method into GuiThread.
    Usage:
    @thread_this_method(GuiThread args)
    def method(self, *method_args)
        method stuff here

    start method as thread:
    method(*method_args).start()

    kill method thread:
    method.kill()

    :param thread_kwargs:
    :return: wrapped GuiThread object
    """
    def method_wraper(method):
        def method_call_wrap(*args, **kwargs):
            instance = args[0]
            info("decorator {}: Converting method {} into {} object".format(thread_this_method.__name__, method.__name__, GuiThread.__name__))
            info("{} with args: {}, kwargs: {}".format(GuiThread.__name__, args, thread_kwargs))
            thread = GuiThread(method, args=args, **thread_kwargs)
            thread.__name__ = "threaded_{}".format(method.__name__)
            setattr(instance, method.__name__, thread)
            return thread
        return method_call_wrap
        method_wraper.__name__ = method.__name__
        method_call_wrap.__name__ = method.__name__
    return method_wraper

class ThreadById():
    def __init__(self, thread, id, alias=None):
        self.thread = thread
        self.id = id
        self.alias = alias

    def __str__(self):
        return "name:{} id:{} alias:{}".format(self.thread.process.__name__, self.id, self.alias)

    def __repr__(self):
        return self.__str__()

class AliasedThreadsDict(dict):
    def __setitem__(self, key, value):
        if isinstance(value, list) and isinstance(value[0], ThreadById):
            dict.__setitem__(self, key, value)
        else:
            raise Exception("This dict is for list of {} type only".format(ThreadById.__name__))

    def get_by_alias(self, alias):
        thread_found = None
        for key in self:
            for thread in self[key]:
                a = thread.alias
                if alias == a:
                    if not thread_found:
                        thread_found = thread.thread
                    else:
                        raise Exception("More than one threads with alias: {}".format(alias))
        if thread_found:
            return thread_found
        else:
            raise Exception("No thread with alias: {}".format(alias))

    def __getattr__(self, item):
        return self.get_by_alias(item)


def thread_periodic_print(msg='', print_method=info):
    print_method(msg)


#@shallow_track_class_calls
class GuiThread(QThread):
    threads_dict = AliasedThreadsDict()

    @staticmethod
    def append_new_thread(thread, alias=None):
        thread_name = thread.process.__name__
        if not thread_name in GuiThread.threads_dict:
            thread_id = ThreadById(thread=thread, id=0, alias=alias)
            GuiThread.threads_dict[thread_name] = [thread_id]
        else:
            id = len(GuiThread.threads_dict[thread_name])
            thread_id = ThreadById(thread=thread, id=id, alias=alias)
            GuiThread.threads_dict[thread_name].append(thread_id)
        return thread_id

    @staticmethod
    def threads_list(some_instance=None):
        info("{}".format(GuiThread.__name__))
        for t in GuiThread.threads_dict:
            info("{}".format(t))

    @staticmethod
    def kill_all_threads(some_instance=None):
        info("Called by: {}".format(some_instance))
        for thread_name in GuiThread.threads_dict:
            for thread in GuiThread.threads_dict[thread_name]:
                info("{} kill {}".format(GuiThread.__name__, thread))
                thread.thread.kill()

    @staticmethod
    def suspend_all_threads(some_instance=None):
        info("Called by: {}".format(some_instance))
        for thread_name in GuiThread.threads_dict:
            for thread in GuiThread.threads_dict[thread_name]:
                info("{} suspend {}".format(GuiThread.__name__, thread))
                thread.thread.suspend()

    @staticmethod
    def resume_all_threads(some_instance=None):
        info("Called by: {}".format(some_instance))
        for thread_name in GuiThread.threads_dict:
            for thread in GuiThread.threads_dict[thread_name]:
                info("{} resume {}".format(GuiThread.__name__, thread))
                thread.thread.resume()

    def __init__(self, process, args=(), kwargs={}, period=None, delay=None, action_when_done=None, alias=None,
                 on_terminate=None):
        QThread.__init__(self)
        self.process = process
        self.args = args
        self.kwargs = kwargs
        self.period = period
        self.returned_from_thread = None
        self.start_tstamp = None
        self.delay = delay
        self._suspension_timeout = 0
        self._suspension_tstamp = 0
        self.action_when_done = action_when_done
        self.on_terminate = on_terminate
        self.stop = False
        self.hard_supended = False
        self._is_suspended = False
        self.__is_running = False
        self.thread_reference = GuiThread.append_new_thread(self, alias)
        info("Init thread {}({}) args: {} total num of threads: {}".format(self.process.__name__, alias, self.args, len(GuiThread.threads_dict)))

    def set_new_args(self, *args):
        self.args = args

    def suspend(self, timeout=None):
        self.suspension_print = True    #self.suspension_print blocks printing suspension status in loop but only once
        if timeout:
            self._suspension_timeout = timeout
            self._suspension_tstamp = time.time()
        else:
            self.hard_supended = True

    def resume(self):
        self._suspension_timeout = 0
        self.hard_supended = False
        self.suspension_print = False

    def get_output(self):
        return self.returned_from_thread

    def wait_for_output(self, timeout=1):
        t0 = time.time()
        while not self.returned_from_thread:
            time.sleep(0.001)
            if time.time() - t0 > timeout:
                info("{} {} timeout".format(self, self.wait_for_output.__name__))
                return None
        return self.returned_from_thread

    def kill(self):
        self.terminate()
        while self.isRunning():
            time.sleep(0.01)
        if self.on_terminate:
            info("{} executing on_terminate action {}".format(self, self.on_terminate.__name__))
            self.on_terminate()
        info("{} terminated".format(self))

    def safe_start(self):
        if not self.isRunning():
            self.start()
        else:
            info("{} safe start prevented to run another instance of {}".format(self.thread_reference))

    def wait_until_previous_finish_and_restart(self):
        if self.isRunning():
            info("{} Restart thread {}: wait for previous run finish".format(self.thread_reference))
        while self.isRunning():
            time.sleep(0.0001)
        self.start()

    def try_restart(self):
        if not self.isRunning():
            self.start()
        else:
            info("Restart thread {}: wait for previous run finish".format(self.thread_reference))

    def start_with_params(self, **kwargs):
        for param in kwargs:
            if param[0] == "-":
                raise Exception("{} apparently this is private !")
            self.__dict__[param] = kwargs[param]
        self.run()

    def is_suspended(self):
        return self._is_suspended or self.hard_supended

    def suspend_and_wait(self):
        self.suspend()
        while not self.is_suspended():
            time.sleep(0.01)
        info("{}: {} done".format(self.thread_reference, self.suspend_and_wait.__name__))

    def is_running(self):
        return self.__is_running

    def run(self):
        self.__is_running = True
        self.resume()
        if self.delay:
            time.sleep(self.delay)
        #single run
        if not self.period:
            self.start_tstamp = tstamp()
            info("Thread started: {} args: {}".format(self.process.__name__, self.args))
            try:
                self.returned_from_thread = self.process(*self.args, **self.kwargs)
            except Exception as E:
                traceback.print_exc(file=threads_exception_logger)
                raise E
        else:
            while True:
                if not self.hard_supended:
                    if self._suspension_timeout == 0:
                        self._is_suspended = False
                        self.returned_from_thread = self.process(*self.args, **self.kwargs)
                    elif time.time() - self._suspension_tstamp > self._suspension_timeout:
                        self._suspension_timeout = 0
                        self.suspension_print = True
                    if self._suspension_timeout != 0:
                        self._is_suspended = True
                        if self.suspension_print:
                            info("Thread suspended: {} for: {:.1f}".format(self.thread_reference, self._suspension_timeout - time.time() + self._suspension_tstamp))
                            self.suspension_print = False
                else:
                    if self.suspension_print:
                        info("Thread {} hard-suspended".format(self.thread_reference))
                        self.suspension_print = False
                time.sleep(self.period)
        if self.action_when_done:
            info("Call action_when_done: {}".format(self.action_when_done.__name__))
            self.action_when_done()
        info("Thread ended: {} created at: {}, returns: {}".format(self.thread_reference, self.start_tstamp, self.returned_from_thread))
        self.__is_running = False

    def __str__(self):
        return "GUI thread {} with args: {}".format(self.thread_reference, self.args)

    def __del__(self):
        info("{} gone by __del__".format(str(self)))
        del self.thread_reference

    @staticmethod
    def check():
        return GuiThread.__dict__['suspend_all_threads']



if __name__ == "__main__":
    import types
    print type(GuiThread.suspend_all_threads)
    print GuiThread.__dict__
    print type(GuiThread.__dict__['suspend_all_threads']) in [staticmethod]
    print type(getattr(GuiThread, 'suspend_all_threads'))
    print GuiThread.check()
