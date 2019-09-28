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
        self.dump_log_file()
        self.dump_log_file.start()

        #mainGrid.addWidget(self.line_edit,      0, 0, 1, 5)
        #mainGrid.addWidget(self.browse_button,  0, 5)
        #mainGrid.addWidget(self.text_browser,   1, 0, 4, 5)
        #mainGrid.addWidget(self.cancel_button,  5, 0, 1, 1)
        #mainGrid.addWidget(self.reflash_button, 5, 4, 1, 1)
        #self.setLayout(mainGrid)

        #self.check_if_bootloader_ready()
        #self.check_if_bootloader_ready.start()

    def show_frames(self, frames):
        o=''
        template = '{:02X}: ' + 8*' {:02X}' + '\n'
        for frame_id in sorted(frames.keys(), reverse=True):
            o+= template.format(*[frame_id] + [ord(i) for i in frames[frame_id]])
            self.log_file.write(frames[frame_id])
        # for d in dir(self.ktextbrowser):
        #     print d
        self.ktextbrowser.setText(o)

    @thread_this_method(period=1)
    def dump_log_file(self):
        self.log_file.flush()

    def __del__(self):
        print 'bye from digidiag'
        self.log_file.close()






if __name__ == "__main__":
    c = CircIoBuffer(byte_size=2)
    c.write('ab')
    c.write('c')
    print 'ab' in c