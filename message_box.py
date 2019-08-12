"""
author: Rafal Miecznik
contact: ravmiecznk@gmail.com
"""

from PyQt4.QtGui import QFileDialog, QMessageBox
Question = QMessageBox.Question
Information = QMessageBox.Information
Warning = QMessageBox.Warning
Critical = QMessageBox.Critical
Ok = QMessageBox.Ok
Open = QMessageBox.Open
Save = QMessageBox.Save
Cancel = QMessageBox.Cancel
Yes = QMessageBox.Yes
No = QMessageBox.No

def message_box(msg, parent=None, detailed_msg='', icon=QMessageBox.Critical, buttons=QMessageBox.Ok, title='', exe=True, button_clicked_sig=lambda: None):
    msg_box = QMessageBox(parent)
    msg_box.setIcon(icon)
    msg_box.setText(msg)
    msg_box.setDetailedText(detailed_msg)
    msg_box.setStandardButtons(buttons)
    msg_box.setWindowTitle(title)
    msg_box.buttonClicked.connect(button_clicked_sig)
    if exe:
        msg_box.exec_()
    return msg_box


def show_welcome_msg(*args, **kwargs):
    from PyQt4 import QtGui
    import sys
    app = QtGui.QApplication(sys.argv)
    kwargs['exe'] = False
    myapp = message_box(*args, **kwargs)
    myapp.show()
    app.exec_()
    sys.exit()
    sys.stdout = STDOUT

if __name__ == "__main__":
    pass