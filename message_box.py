"""
author: Rafal Miecznik
contact: ravmiecznk@gmail.com
"""

from PyQt4.QtGui import QFileDialog, QMessageBox

def message_box(msg, parent=None):
    msg_box = QMessageBox(parent)
    msg_box.setIcon(QMessageBox.Critical)
    msg_box.setText(msg)
    msg_box.setStandardButtons(QMessageBox.Ok)
    msg_box.exec_()