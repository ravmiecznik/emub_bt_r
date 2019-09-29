"""
author: Rafal Miecznik
contact: ravmiecznk@gmail.com
"""

import os
from PyQt4 import QtCore, QtGui
from PyQt4.QtGui import QTextBrowser
from PyQt4.QtGui import QFileDialog
from PyQt4.QtCore import pyqtSignal
from setup_emubt import logger, info, debug, error, warn, EMU_BT_PATH, LOG_PATH
from gui_thread import SimpleGuiThread, thread_this_method
import struct, time
from event_handler import to_signal


try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    def _fromUtf8(s):
        return s

try:
    _encoding = QtGui.QApplication.UnicodeUTF8
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig, _encoding)
except AttributeError:
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig)

class Ui_DockWidget(object):
    def setupUi(self, DockWidget):
        DockWidget.setObjectName(_fromUtf8("DockWidget"))
        DockWidget.resize(1010, 910)
        self.dockWidgetContents = QtGui.QWidget()
        self.dockWidgetContents.setObjectName(_fromUtf8("dockWidgetContents"))
        self.ktextbrowser = QTextBrowser(self.dockWidgetContents)
        self.ktextbrowser.setGeometry(QtCore.QRect(10, 20, 1000, 900))
        self.ktextbrowser.setObjectName(_fromUtf8("ktextbrowser"))
        DockWidget.setWidget(self.dockWidgetContents)

        self.retranslateUi(DockWidget)
        QtCore.QMetaObject.connectSlotsByName(DockWidget)

    def retranslateUi(self, DockWidget):
        DockWidget.setWindowTitle(_translate("DockWidget", "DockWidget", None))


def log_tstamp_pack(t):
    """
    pack tstamp to unsigned short (2 bytes)
    log_stamp: 2digits_decimal_value__3digits_miliseconds
    first two digits represents seconds, three last digits represents time in miliseconds
    :param t: packed tstamp
    :return:
    """
    #print t, '|',
    t = int(t * 10000) #shift milisecods to integer values
    #print t
    try:
        return struct.pack('H', t)
    except struct.error:
        print "ERROR", t


class DigiFrames(dict):
    def __str__(self):
        o = ''
        for frame_id in sorted(self.keys(), reverse=True):
            o += ('{:02X}: ' + 8*' {:02X}' + '\n').format(frame_id, *self[frame_id])
        return o


class DigiDiag(QtGui.QWidget):
    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent=parent)
        self.setWindowTitle("DIGDIAG")
        self.x_siz, self.y_siz = 600, 500
        mainGrid = QtGui.QGridLayout()
        mainGrid.setSpacing(10)
        font = QtGui.QFont('Courier New', 8)
        self.ktextbrowser = QTextBrowser(self)
        self.ktextbrowser.setGeometry(QtCore.QRect(10, 20, 400, 200))
        self.ktextbrowser.setFont(font)
        self.log_file = open(os.path.join(LOG_PATH, 'digidag.dmp'), 'w')
        self.refresh_thread = SimpleGuiThread(to_signal(self.refresh), period=0.1)
        self.refresh_thread.start()
        self.__log_period = 0.05
        self.log_thread = SimpleGuiThread(self.log_thread, period=self.__log_period)
        self.prev_tstamp = time.time()
        self.tmp = time.time()
        self.template = '{:02X}: ' + 8*' {:02X}' + '\n'
        self.frames = dict()
        self.log_thread.start()
        self.log_thread.start()
        self._log_separator = 10 * '\0'


    def log_thread(self):
        self.log_file.write(self._log_separator)
        for frame_id in sorted(self.frames.keys(), reverse=True):
            self.log_file.write(self.frames[frame_id])


    def feed_with_data(self, frame):
        self.frames[ord(frame[1])] = frame  #key by frame id

    def refresh(self):
        o = ''
        for frame_id in sorted(self.frames.keys(), reverse=True):
            o+= self.template.format(*[frame_id] + [ord(i) for i in self.frames[frame_id]])
        o += '\n {:<03.2f}'.format(time.time()*10000 - self.tmp)
        self.tmp = time.time()*10000
        self.ktextbrowser.setText(o)


    def __del__(self):
        print 'bye from digidiag'
        self.log_file.close()






if __name__ == "__main__":
    c = CircIoBuffer(byte_size=2)
    c.write('ab')
    c.write('c')
    print 'ab' in c