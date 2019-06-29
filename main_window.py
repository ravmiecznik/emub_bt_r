import time

from PyQt4 import QtCore, QtGui
from PyQt4.QtCore import pyqtSignal

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

"""
Progress bar styles
"""
BLUE_STYLE = """
QProgressBar{
    border: 2px solid grey;
    border-radius: 5px;
    text-align: center
}

QProgressBar::chunk {
    background-color: lightblue;
    width: 10px;
    margin: 1px;
}
"""

RED_STYLE = """
QProgressBar{
    border: 2px solid grey;
    border-radius: 5px;
    text-align: center
}

QProgressBar::chunk {
    background-color: red;
    width: 10px;
    margin: 1px;
}
"""

"""
Help tips
"""
STORE_FLASH_BANK_BTN_TIP    = "This button commits selected binary file to permanent memory in currently selected bank"
READ_SRAM_BTN_TIP           = "SRAM: this memory is visible to your ECU. This button will get its content." \
                            "\nBut beware that during read process Emulator is not accessible to ECU" \
                            "\nEmulation will stop"
READ_BANK_BTN_TIP           = "Read and save to file content of currently selected bank, which is stored in internal flash"
LCD_WEAR_DISPLAY_TIP        = "Bank wear counter. Will increase if any of 256bytes page of given bank was rewritten in given bank slot.\n" \
                              "It helps to keep track of how many times flash memory was overwritten.\n" \
                              "There is a check if a given page was modified, if no it is not erased to extend its life.\n" \
                              "To refresh just click 'bank' button."
AUTO_OPEN_CHECK_BOX_TIP     = "If checked it will automatically open a saved file with new binary image downloaded from BT emulator\n"
OVERWRITE_CHECK_BOX_TIP     = "If checked it will overwrte current file without asking\n"

class WindowGeometry(object):
    def __init__(self, QtGuiobject):
        #self.parent = parent
        self.pos_x = QtGuiobject.x()
        self.pos_y = QtGuiobject.y()
        self.height = QtGuiobject.height()
        self.width = QtGuiobject.width()

    def get_position_to_the_right(self):
        pos_x = self.width + self.pos_x
        return pos_x

    def __call__(self):
        return self.pos_x, self.pos_y, self.width, self.height

class ColorProgressBar(QtGui.QProgressBar):
    set_val_signal = pyqtSignal(object)
    def __init__(self, parent = None):
        QtGui.QProgressBar.__init__(self)
        self.setStyleSheet(BLUE_STYLE)
        self.parent = parent
        self.set_val_signal.connect(self.setValue)

    def set_red_style(self):
        self.setStyleSheet(RED_STYLE)

    def set_blue_style(self):
        self.setStyleSheet(BLUE_STYLE)


    def set_title(self, title):
        self.setWindowTitle(title)

    def display(self, width=400, height=50, x_offset=400, y_offset=100):
        self.setValue(0)
        current_position_and_size = WindowGeometry(self.parent)
        x_pos = current_position_and_size.get_position_to_the_right()
        self.setGeometry(x_pos - x_offset, current_position_and_size.pos_y + y_offset, width, height)
        self.show()

    def set_red_style(self):
        self.setStyleSheet(RED_STYLE)

    def set_blue_style(self):
        self.setStyleSheet(BLUE_STYLE)



#TODO: try to do a docorator which will add help on hover
#It may work like this:
#It takes a Class as input, adds new methods like enter and leave envent and returns such Class
class CheckBoxWithHelp(QtGui.QCheckBox):
    help_tip_slot = None
    def __init__(self, parent, help_msg=None):
        super(CheckBoxWithHelp, self).__init__(parent)
        self.help_msg = help_msg
        self.tip_displayed = False

    @staticmethod
    def set_static_help_tip_slot_signal(signal):
        CheckBoxWithHelp.help_tip_slot = signal

    def tip(self):
        tip_msg = self.help_msg
        CheckBoxWithHelp.help_tip_slot.emit(tip_msg)
        self.tip_displayed = True
        self.timer.stop()

    def enterEvent(self, QEvent):
        if self.help_msg:
            self.timer = QtCore.QTimer()
            self.timer.connect(self.timer, QtCore.SIGNAL("timeout()"), self.tip)
            self.timer.start(500)

    def leaveEvent(self, QEvent):
        if self.help_msg and self.tip_displayed:
            CheckBoxWithHelp.help_tip_slot.emit('')

class LcdDisplayWithHelp(QtGui.QLCDNumber):
    help_tip_slot = None
    def __init__(self, parent, help_msg=None):
        super(LcdDisplayWithHelp, self).__init__(parent)
        self.help_msg = help_msg
        self.tip_displayed = False

    @staticmethod
    def set_static_help_tip_slot_signal(signal):
        LcdDisplayWithHelp.help_tip_slot = signal

    def tip(self):
        tip_msg = self.help_msg
        LcdDisplayWithHelp.help_tip_slot.emit(tip_msg)
        self.tip_displayed = True
        self.timer.stop()

    def enterEvent(self, QEvent):
        if self.help_msg:
            self.timer = QtCore.QTimer()
            self.timer.connect(self.timer, QtCore.SIGNAL("timeout()"), self.tip)
            self.timer.start(500)

    def leaveEvent(self, QEvent):
        if self.help_msg and self.tip_displayed:
            LcdDisplayWithHelp.help_tip_slot.emit('')

class PushButtonWithHelp(QtGui.QPushButton):
    help_tip_slot = None
    def __init__(self, parent, help_msg=None):
        super(PushButtonWithHelp, self).__init__(parent)
        self.help_msg = help_msg
        self.tip_displayed = False

    @staticmethod
    def set_static_help_tip_slot_signal(signal):
        PushButtonWithHelp.help_tip_slot = signal

    def tip(self):
        tip_msg = self.help_msg
        PushButtonWithHelp.help_tip_slot.emit(tip_msg)
        self.tip_displayed = True
        self.timer.stop()

    def enterEvent(self, QEvent):
        if self.help_msg:
            self.timer = QtCore.QTimer()
            self.timer.connect(self.timer, QtCore.SIGNAL("timeout()"), self.tip)
            self.timer.start(500)

    def leaveEvent(self, QEvent):
        if self.help_msg and self.tip_displayed:
            PushButtonWithHelp.help_tip_slot.emit('')

class myTextBrowser(QtGui.QTextBrowser):
    """
    Qt Class: modifed QTextBrowser
    """

    def __init__(self, parent, scroll_pressed_signal=None, console_select_text_slot=None, help_tip_slot=None):
        super(myTextBrowser, self).__init__(parent)
        self.scroll_pressed_signal = scroll_pressed_signal
        self.selectionChanged.connect(console_select_text_slot)
        self.timer = None
        self.help_tip_slot = help_tip_slot
        self.tip_displayed = False

    def tip(self):
        tip_msg = "Hold left button to select text, double click to select word, middle button to execute selected word"
        self.help_tip_slot.emit(tip_msg)
        self.tip_displayed = True
        self.timer.stop()

    def enterEvent(self, QEvent):
        self.timer = QtCore.QTimer()
        self.timer.connect(self.timer, QtCore.SIGNAL("timeout()"), self.tip)
        self.timer.start(500)

    def leaveEvent(self, QEvent):
        if self.tip_displayed:
            self.help_tip_slot.emit('')

    def mouseReleaseEvent(self, MouseEvent):
        if MouseEvent.button() == QtCore.Qt.MidButton:
            self.scroll_pressed_signal.emit()

class TestPanel(QtGui.QMainWindow):
    mainGrid = QtGui.QGridLayout()
    mainGrid.setSpacing(10)
    test_panel_frame_FrameGrid = QtGui.QGridLayout()
    test_panel_frame_FrameGrid.setSpacing(10)
    def __init__(self, parent=None):
        super(TestPanel, self).__init__(parent)
        self.setWindowTitle("Test Panel")
        self.resize(200, 100)
        self.centralwidget = QtGui.QWidget(self)
        self.setCentralWidget(self.centralwidget)
        self.test_panel = QtGui.QGroupBox(self.centralwidget)
        self.test_panel.setLayout(self.test_panel_frame_FrameGrid)
        self.injectErrorsCheckBox = QtGui.QCheckBox(self.test_panel)
        self.test_panel_frame_FrameGrid.addWidget(self.injectErrorsCheckBox, 0, 0)
        self.injectErrorsCheckBox.setText("Inject false errors for crc test")
        self.test_panel.raise_()
        self.mainGrid.addWidget(self.test_panel, 0, 0)

