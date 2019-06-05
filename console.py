"""
author: Rafal Miecznik
contact: ravmiecznk@gmail.com
"""

from PyQt4 import QtCore, QtGui
from dummy_event_handler import DummyEventHandler
from objects_with_help import HelpTip, CheckBox
import time
from call_tracker import method_call_track

HELP_TIP = "Hold left button to select text, double click to select word,\n" \
           "middle button to execute selected word"


@method_call_track
class MyTextBrowser(QtGui.QTextBrowser, HelpTip):
    """
    Qt Class: modifed QTextBrowser
    """

    def __init__(self, parent, scroll_pressed_slot, console_select_text_slot):
        QtGui.QTextBrowser.__init__(self, parent)
        HelpTip.__init__(self, HELP_TIP)
        #super(myTextBrowser, self).__init__(parent)
        self.scroll_pressed_slot = scroll_pressed_slot
        self.selectionChanged.connect(console_select_text_slot)

    def mouseReleaseEvent(self, MouseEvent):
        if MouseEvent.button() == QtCore.Qt.MidButton:
            self.scroll_pressed_slot()


@method_call_track
class Console(QtGui.QGroupBox):
    #def __init__(self, parent, scroll_pressed_slot, console_select_text_slot, event_handler=DummyEventHandler()):
    def __init__(self, parent, event_handler=DummyEventHandler()):
        super(Console, self).__init__(parent)
        self.parent = parent
        self.setTitle("Console")
        console_frame_FraneGrid = QtGui.QGridLayout()
        console_frame_FraneGrid.setSpacing(1)
        self.command_line = QtGui.QLineEdit()
        self.command_line.returnPressed.connect(self.scroll_pressed_slot)
        #self.bootlader_support_checkbox = CheckBox(tip_msg="Support bootloader command mode")
        self.help_button = QtGui.QPushButton("HLP")
        self.reset_button = QtGui.QPushButton("RST")

        #self.console_text_browser = myTextBrowser(self, scroll_pressed_slot, console_select_text_slot)
        self.console_text_browser = MyTextBrowser(self, self.scroll_pressed_slot, self.console_select_text_slot)
        #self.console_text_browser.setFontPointSize(8)
        font = QtGui.QFont('Courier New', 8)
        self.console_text_browser.setFont(font)
        self.command_line.setFont(font)
        self.event_handler = event_handler
        console_frame_FraneGrid.addWidget(self.console_text_browser, 0, 0, 4, 20)
        console_frame_FraneGrid.addWidget(self.command_line, 5, 0, 1, 16)
        #console_frame_FraneGrid.addWidget(self.bootlader_support_checkbox, 5, 17, 1, 1)
        console_frame_FraneGrid.addWidget(self.help_button, 5, 17, 1, 1)
        console_frame_FraneGrid.addWidget(self.reset_button, 5, 18, 1, 1)
        self.setLayout(console_frame_FraneGrid)
        self.help_button.clicked.connect(self.event_handler.send_help_cmd_slot)
        self.reset_button.clicked.connect(self.event_handler.send_resetemu_slot)

    def scroll_pressed_slot(self):
        cmd = self.command_line.text()
        if cmd:
            self.event_handler.command_line_slot(cmd)

    def communication_pipe_slot(self, msg):
        tstamp = time.strftime("%H:%M:%S", time.localtime())
        msg = "{}| {}".format(tstamp, msg)
        self.console_text_browser.append(msg)
        self.console_text_browser.moveCursor(QtGui.QTextCursor.End)

    def console_select_text_slot(self):
        cursor = self.console_text_browser.textCursor()
        selected_text = self.console_text_browser.toPlainText()[cursor.selectionStart(): cursor.selectionEnd()]
        self.command_line.setText(selected_text)
        self.command_line.setFocus()