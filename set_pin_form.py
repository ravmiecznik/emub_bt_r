"""
author: Rafal Miecznik
contact: ravmiecznk@gmail.com
"""

import time
from PyQt4 import QtCore, QtGui
from PyQt4.QtGui import QFileDialog
from PyQt4.QtCore import pyqtSignal
from message_box import message_box
from event_handler import to_signal

class SetPinWindow(QtGui.QWidget):
    def __init__(self, set_pin_signal):
        QtGui.QWidget.__init__(self)
        self.setWindowTitle("SET PIN")
        self.x_siz, self.y_siz = 200, 200
        mainGrid = QtGui.QGridLayout()
        mainGrid.setSpacing(10)
        self.line_edit = QtGui.QLineEdit()
        self.ok_button = QtGui.QPushButton("OK")
        self.cancel_button = QtGui.QPushButton("Cancel")
        self.ok_button.clicked.connect(self.set_pin)
        self.cancel_button.clicked.connect(to_signal(self.close))
        mainGrid.addWidget(self.line_edit,      0, 0, 1, 5)
        mainGrid.addWidget(self.cancel_button,  5, 0, 1, 1)
        mainGrid.addWidget(self.ok_button,      5, 4, 1, 1)
        self.setLayout(mainGrid)
        self.resize(self.x_siz, self.y_siz)
        self.set_pin_signal = set_pin_signal
        self.show()


    def set_pin(self):
        pin = str(self.line_edit.text())
        if len(pin) != 4:
            message_box("Pin length must be 4 !")
        else:
            time.sleep(1)
            self.set_pin_signal.emit(pin)
            self.close()

if __name__ == "__main__":
    import sys
    app = QtGui.QApplication(sys.argv)
    myapp = SetPinWindow(None)
    #myapp.show()
    app.exec_()
    # myapp.safe_close()
    sys.exit()
    sys.stdout = STDOUT