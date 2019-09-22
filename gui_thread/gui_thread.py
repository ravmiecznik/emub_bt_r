"""
author: Rafal Miecznik
contact: ravmiecznk@gmail.com
"""

from loggers import create_logger
import time, os
from PyQt4.QtCore import QThread
from setup_emubt import LOG_PATH

log_format = '[%(asctime)s]: %(levelname)s method:"%(funcName)s" %(message)s'
logger_name = "thread_tracker"

t_logger = create_logger(logger_name, log_path=LOG_PATH, format=log_format, log_to_file=True)

class SimpleGuiThread(QThread):
    threads = []

    @staticmethod
    def append_new_thread(item):
        t_id = len(SimpleGuiThread.threads)
        SimpleGuiThread.threads.append(item)
        return t_id

    @staticmethod
    def num_of_threads():
        return len(SimpleGuiThread.threads)

    @staticmethod
    def suspend_all_threads():
        for t in SimpleGuiThread.threads:
            t.suspend()

    @staticmethod
    def resume_all_threads():
        for t in SimpleGuiThread.threads:
            t.resume()

    @staticmethod
    def kill_all_threads():
        while SimpleGuiThread.threads:
            SimpleGuiThread.threads[0].kill()
            SimpleGuiThread.threads.remove(SimpleGuiThread.threads[0])

    def __init__(self, process, args=(), kwargs={}, period=0, delay=None, action_when_done=None):
        QThread.__init__(self)
        self.result = None
        self.target = process
        self.__period = period
        self.__delay = delay
        self.__args = args
        self.__kwargs = kwargs
        self.__id = None
        self.__id = SimpleGuiThread.append_new_thread(self)
        self.__suspend = False
        self.__action_when_done = action_when_done
        self.__was_suspension_communicated = False
        self.__is_running = False

    def set_args(self, args):
        if not type(args) is tuple:
            raise Exception("Args must be tuple, got: {} type of: {}".format(args, type(args)))
        self.__args = args

    def set_kwargs(self, kwargs):
        if not type(kwargs) is dict:
            raise Exception("Args must be dict, got: {} type of: {}".format(kwargs, type(kwargs)))
        self.__kwargs = kwargs

    def suspend(self):
        self.__suspend = True
        self.__was_suspension_communicated = False

    def resume(self):
        self.__suspend = False

    def returned(self):
        return self.result

    def is_running(self):
        return self.__is_running

    @property
    def t_id(self):
        return self.__id

    def __run(self):
        if self.__delay: time.sleep(self.__delay)
        if not self.__suspend:
            t_logger.debug("start of: {}, period: {}".format(self, self.__period))
            self.result = self.target(*self.__args, **self.__kwargs)
        elif not self.__was_suspension_communicated:
            t_logger.debug("suspended: {}".format(self))
            self.__was_suspension_communicated = True


    def run(self):
        t_logger.debug("Run: {}, ARGS: {}, KWARGS: {}".format(self.target, self.__args, self.__kwargs))
        self.__is_running = True
        if self.__delay: time.sleep(self.__delay)
        while self.__period != 0:
            self.__run()
            time.sleep(self.__period)
        else:
            self.__run()
        if self.__action_when_done:
            self.__action_when_done()
        self.__is_running = False
        self.kill()


    def terminate(self):
        """
        Will stop the thread but it is still present in memory
        :return:
        """
        t_logger.debug("Terminating {}".format(self))
        self.__prev_period = self.__period
        self.__period = 0
        #while not self.wait():
        #    time.sleep(0.001)


    def restart(self, period):
        """
        Will resurect the thread if terminate was used
        :param period:
        :return:
        """
        self.__period = period if period else self.__prev_period


    def kill(self):
        """
        :return:
        """
        self.terminate()
        t_logger.debug("Deleting: {}".format(self))
        try:
            SimpleGuiThread.threads.remove(self)
        except ValueError:
            pass
        t_logger.debug("Num of threads: {}".format(len(SimpleGuiThread.threads)))


    def __repr__(self):
        return "{}.{} id:{}".format(SimpleGuiThread, self.target.__name__, self.__id)


if __name__ == "__main__":
    from PyQt4 import QtGui
    import sys
    class MainW(QtGui.QMainWindow):
        """
        Mainw to host and run one single thread
        """

        def __init__(self):
            QtGui.QMainWindow.__init__(self)
            self.thr = SimpleGuiThread(process=fun, period=0.2)
            SimpleGuiThread.threads[0].start()
            time.sleep(1)
            print id(self.thr)
            #self.thr.kill()
            print id(self.thr)
            print 'is running', self.thr.isRunning()
            self.thr.kill()

        def fetch_thread(self, mt):
            self.mt = mt
            return self.mt

        def get_thread(self):
            return self.mt

        def start_thread(self):
            self.mt.start()
            while self.mt.isRunning(): time.sleep(0.001)
            return


    def fun():
        print fun.__name__

    app = QtGui.QApplication(sys.argv)
    myapp = MainW()
    myapp.show()
    app.exec_()
    print 'bye'
    sys.exit()

