import time

from PyQt4 import QtCore, QtGui
#import main
from PyQt4.QtCore import pyqtSignal
from matplotlib.backends.backend_qt5 import MainWindow

from PyQt4.QtCore import QEvent
from PyQt4.QtGui import QKeyEvent, QMouseEvent, QWheelEvent

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
    def __init__(self, parent = None):
        QtGui.QProgressBar.__init__(self)
        self.setStyleSheet(BLUE_STYLE)
        self.parent = parent

    def set_red_style(self):
        self.setStyleSheet(RED_STYLE)

    def set_blue_style(self):
        self.setStyleSheet(BLUE_STYLE)

    def set_title(self, title):
        self.setWindowTitle(title)

    def display(self, width=400, height=50, x_offset=15, y_offset=100):
        self.setValue(0)
        current_position_and_size = WindowGeometry(self.parent)
        x_pos = current_position_and_size.get_position_to_the_right()
        self.setGeometry(x_pos + x_offset, current_position_and_size.pos_y + y_offset, width, height)
        self.show()

    def set_red_style(self):
        self.setStyleSheet(RED_STYLE)

    def set_blue_style(self):
        self.setStyleSheet(BLUE_STYLE)

    # def setValue(self, value):
    #     QtGui.QProgressBar.setValue(self, value)
    #
    #     if value == self.maximum():
    #         self.setStyleSheet(COMPLETED_STYLE)


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


class Ui_MainWindow(object):
    def __init__(self):
        pass

    def setupUi(self, MainWindow):
        x_siz = 500
        y_siz=710
        mainGrid = QtGui.QGridLayout()
        mainGrid.setSpacing(10)

        MainWindow.setObjectName(_fromUtf8("MainWindow"))
        MainWindow.resize(x_siz, y_siz)
        self.centralwidget = QtGui.QWidget(MainWindow)
        self.centralwidget.setObjectName(_fromUtf8("centralwidget"))

        file_in_use_FrameGrid = QtGui.QGridLayout()
        file_in_use_FrameGrid.setSpacing(1)
        control_frame_FrameGrid = QtGui.QGridLayout()
        control_frame_FrameGrid.setSpacing(1)
        banks_frame_FraneGrid = QtGui.QGridLayout()
        banks_frame_FraneGrid.setSpacing(1)
        console_frame_FraneGrid = QtGui.QGridLayout()
        console_frame_FraneGrid.setSpacing(1)
        emu_performance_panelGrid = QtGui.QGridLayout()
        emu_performance_panelGrid.setSpacing(1)

        #file in use panel
        self.file_in_use_panel = QtGui.QGroupBox(self.centralwidget)
        self.file_selection_comboBox = QtGui.QComboBox(self.file_in_use_panel)
        #self.checkBox = QtGui.QCheckBox(self.file_in_use_panel)
        self.browseButton = QtGui.QPushButton(self.file_in_use_panel)
        self.open_in_editor = QtGui.QPushButton(self.file_in_use_panel)
        self.copy_path = QtGui.QPushButton(self.file_in_use_panel)
        file_in_use_FrameGrid.addWidget(self.file_selection_comboBox, 0, 0, 1, 4)
        file_in_use_FrameGrid.addWidget(self.browseButton, 1, 1)
        file_in_use_FrameGrid.addWidget(self.open_in_editor, 1, 2)
        file_in_use_FrameGrid.addWidget(self.copy_path, 1, 3)
        self.file_in_use_panel.setLayout(file_in_use_FrameGrid)

        #emu performacne panel
        self.emu_performance_panel = QtGui.QGroupBox(self.centralwidget)
        self.cpu_loops_lcd = QtGui.QLCDNumber(self.emu_performance_panel)
        self.free_memory_lcd = QtGui.QLCDNumber(self.emu_performance_panel)
        cpu_text = QtGui.QLabel(self.emu_performance_panel)
        free_mem_text = QtGui.QLabel(self.emu_performance_panel)
        cpu_text.setText("CPU")
        free_mem_text.setText("Free mem")
        emu_performance_panelGrid.addWidget(self.cpu_loops_lcd, 0, 0)
        emu_performance_panelGrid.addWidget(self.free_memory_lcd, 0, 1)
        emu_performance_panelGrid.addWidget(cpu_text, 1, 0)
        emu_performance_panelGrid.addWidget(free_mem_text, 1, 1)
        self.emu_performance_panel.setLayout(emu_performance_panelGrid)

        #banks panel
        LcdDisplayWithHelp.set_static_help_tip_slot_signal(MainWindow.help_tip_signal)
        self.banks_panel = QtGui.QGroupBox(self.centralwidget)
        self.auto_download_checkbox = QtGui.QCheckBox(self.banks_panel)
        self.bank1pushButton = QtGui.QPushButton(self.banks_panel)
        self.bank2pushButton = QtGui.QPushButton(self.banks_panel)
        self.bank3pushButton = QtGui.QPushButton(self.banks_panel)
        self.bank1_wear_lcd = LcdDisplayWithHelp(self.banks_panel, LCD_WEAR_DISPLAY_TIP)
        self.bank2_wear_lcd = LcdDisplayWithHelp(self.banks_panel, LCD_WEAR_DISPLAY_TIP)
        self.bank3_wear_lcd = LcdDisplayWithHelp(self.banks_panel, LCD_WEAR_DISPLAY_TIP)
        self.bank_name_line_edit = QtGui.QLineEdit(self.banks_panel)
        self.bank1pushButton.raise_()
        self.bank2pushButton.raise_()
        self.bank3pushButton.raise_()
        self.bank1_wear_lcd.raise_()
        self.bank2_wear_lcd.raise_()
        self.bank3_wear_lcd.raise_()
        self.bank1pushButton.raise_()
        self.bank2pushButton.raise_()
        self.bank3pushButton.raise_()
        self.bank2pushButton.raise_()
        self.bank1pushButton.raise_()
        self.bank1_wear_lcd.raise_()
        self.bank3_wear_lcd.raise_()
        self.auto_download_checkbox.raise_()
        banks_frame_FraneGrid.addWidget(self.bank1pushButton, 0, 0)
        banks_frame_FraneGrid.addWidget(self.bank2pushButton, 1, 0)
        banks_frame_FraneGrid.addWidget(self.bank3pushButton, 2, 0)
        banks_frame_FraneGrid.addWidget(self.bank1_wear_lcd, 0, 2)
        banks_frame_FraneGrid.addWidget(self.bank2_wear_lcd, 1, 2)
        banks_frame_FraneGrid.addWidget(self.bank3_wear_lcd, 2, 2)
        banks_frame_FraneGrid.addWidget(self.bank_name_line_edit, 3, 0, 1, 3)
        banks_frame_FraneGrid.addWidget(self.auto_download_checkbox, 4, 0)
        self.banks_panel.setLayout(banks_frame_FraneGrid)
        self.bank1pushButton.setMaximumSize(QtCore.QSize(50, 20))
        self.bank2pushButton.setMaximumSize(QtCore.QSize(50, 20))
        self.bank3pushButton.setMaximumSize(QtCore.QSize(50, 20))

        #control panel
        self.control_panel = QtGui.QGroupBox(self.centralwidget)
        self.control_panel_widget = QtGui.QWidget(self.control_panel)
        self.control_panel_widget.setGeometry(QtCore.QRect(10, 30, 151, 74))
        self.control_panel.setTitle(_translate("MainWindow", "Control", None))
        self.connect_button = QtGui.QPushButton(self.control_panel)
        self.reflash_button = QtGui.QPushButton(self.control_panel)
        self.discover_button = QtGui.QPushButton(self.control_panel)
        self.config_button = QtGui.QPushButton(self.control_panel)
        self.control_panel.setLayout(control_frame_FrameGrid)
        self.dbg_checkbox = QtGui.QCheckBox("DBG log to file")
        control_frame_FrameGrid.addWidget(self.connect_button, 0, 0)
        control_frame_FrameGrid.addWidget(self.reflash_button, 0, 1)
        control_frame_FrameGrid.addWidget(self.discover_button, 1, 0)
        control_frame_FrameGrid.addWidget(self.config_button, 1, 1)
        control_frame_FrameGrid.addWidget(self.dbg_checkbox, 2, 0, 1, 2)

        #console panel
        self.console_panel = QtGui.QGroupBox(self.centralwidget)
        self.command_line = QtGui.QLineEdit(self.console_panel)
        self.help_button = QtGui.QPushButton(self.console_panel)
        self.reset_button = QtGui.QPushButton(self.console_panel)
        self.console_text_browser = myTextBrowser(self.console_panel, MainWindow.console_double_click_signal,
                                                  MainWindow.console_select_text_slot, MainWindow.help_tip_signal)
        self.console_text_browser.setFontPointSize(9)
        console_frame_FraneGrid.addWidget(self.console_text_browser, 0, 0, 4, 20)
        console_frame_FraneGrid.addWidget(self.command_line, 5, 0, 1, 17)
        console_frame_FraneGrid.addWidget(self.help_button, 5, 18, 1, 1)
        console_frame_FraneGrid.addWidget(self.reset_button, 5, 19, 1, 1)
        self.console_panel.setLayout(console_frame_FraneGrid)

        self.help_text = QtGui.QLabel(self.centralwidget)

        #emulation_panel
        CheckBoxWithHelp.set_static_help_tip_slot_signal(MainWindow.help_tip_signal)
        PushButtonWithHelp.set_static_help_tip_slot_signal(MainWindow.help_tip_signal)
        self.emulation_panel = QtGui.QGroupBox(self.centralwidget)
        self.emulate_button = QtGui.QPushButton(self.emulation_panel)
        self.read_sram_button = PushButtonWithHelp(self.emulation_panel, READ_SRAM_BTN_TIP)
        self.read_bank_button = PushButtonWithHelp(self.emulation_panel, READ_BANK_BTN_TIP)
        self.store_to_flash_button = PushButtonWithHelp(self.emulation_panel, STORE_FLASH_BANK_BTN_TIP)
        self.auto_open_checkbox = CheckBoxWithHelp(self.emulation_panel, AUTO_OPEN_CHECK_BOX_TIP)
        self.overwrite_checkbox = CheckBoxWithHelp(self.emulation_panel, OVERWRITE_CHECK_BOX_TIP)
        self.read_sram_button.raise_()
        self.read_bank_button.raise_()
        self.emulate_button.raise_()
        emulation_panel_FrameGrid = QtGui.QGridLayout()
        emulation_panel_FrameGrid.setSpacing(1)
        emulation_panel_FrameGrid.addWidget(self.emulate_button, 0, 0)
        emulation_panel_FrameGrid.addWidget(self.read_bank_button, 1, 0)
        emulation_panel_FrameGrid.addWidget(self.read_sram_button, 1, 1)
        emulation_panel_FrameGrid.addWidget(self.store_to_flash_button, 0, 1)
        emulation_panel_FrameGrid.addWidget(self.auto_open_checkbox, 3, 0, 1, 2)
        emulation_panel_FrameGrid.addWidget(self.overwrite_checkbox, 4, 0, 1, 2)
        self.emulation_panel.setLayout(emulation_panel_FrameGrid)

        self.store_to_flash_button.raise_()
        self.file_in_use_panel.raise_()
        #self.file_in_use_panel.raise_()
        self.banks_panel.raise_()
        self.control_panel.raise_()
        self.emulation_panel.raise_()
        self.console_panel.raise_()
        self.help_text.raise_()
        MainWindow.setCentralWidget(self.centralwidget)
        self.statusbar = QtGui.QStatusBar(MainWindow)
        MainWindow.setStatusBar(self.statusbar)

        self.retranslateUi(MainWindow)

        QtCore.QMetaObject.connectSlotsByName(MainWindow)
        self.centralwidget.setLayout(mainGrid)
        mainGrid.addWidget(self.control_panel, 0, 0, 2, 1)
        mainGrid.addWidget(self.emulation_panel, 0, 2, 2, 1)
        mainGrid.addWidget(self.banks_panel, 0, 4, 2, 1)
        mainGrid.addWidget(self.file_in_use_panel, 2, 0, 2, 6)
        mainGrid.addWidget(self.console_panel, 6, 0, 6, 6)
        mainGrid.addWidget(self.emu_performance_panel, 12, 0, 1, 2)
        mainGrid.addWidget(self.help_text, 13, 0, 1, 6)


    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(_translate("MainWindow", "EMU BT", None))
        self.file_in_use_panel.setTitle(_translate("MainWindow", "File in use", None))
        self.auto_open_checkbox.setText(_translate("MainWindow", "auto open", None))
        self.overwrite_checkbox.setText(_translate("MainWindow", "overwrite current file", None))
        self.browseButton.setText(_translate("MainWindow", "browse", None))
        self.open_in_editor.setText(_translate("MainWindow", "open in editor", None))
        self.copy_path.setText(_translate("MainWindow", "copy path", None))
        self.banks_panel.setTitle(_translate("MainWindow", "Flash Banks", None))
        self.auto_download_checkbox.setText(_translate("MainWindow", "auto download", None))
        self.bank1pushButton.setText(_translate("MainWindow", "bank1", None))
        self.bank2pushButton.setText(_translate("MainWindow", "bank2", None))
        self.bank3pushButton.setText(_translate("MainWindow", "bank3", None))
        #self.panels.setTitle(_translate("MainWindow", "Control", None))
        self.connect_button.setText(_translate("MainWindow", "Connect", None))
        self.reflash_button.setText(_translate("MainWindow", "Reflash", None))
        self.discover_button.setText(_translate("MainWindow", "Discover", None))
        self.config_button.setText(_translate("MainWindow", "Config", None))
        self.help_button.setText(_translate("MainWindow", "?", None))
        self.reset_button.setText(_translate("MainWindow", "RST", None))
        self.console_panel.setTitle(_translate("MainWindow", "Console", None))
        self.help_text.setText(_translate("MainWindow", "EMU BT", None))
        self.emulation_panel.setTitle(_translate("MainWindow", "Emulation", None))
        self.emulate_button.setText(_translate("MainWindow", "emulate", None))
        self.read_sram_button.setText(_translate("MainWindow", "read sram", None))
        self.read_bank_button.setText(_translate("MainWindow", "read bank", None))
        self.store_to_flash_button.setText(_translate("MainWindow", "store to flash", None))
        self.connect_gui_objects(MainWindow)

    def connect_gui_objects(self, MainWindow):
        QtCore.QObject.connect(self.store_to_flash_button, QtCore.SIGNAL(_fromUtf8("clicked()")),
                               MainWindow.store_to_flash_button_slot)
        QtCore.QObject.connect(self.connect_button, QtCore.SIGNAL(_fromUtf8("clicked()")),
                               MainWindow.connect_button_slot)
        QtCore.QObject.connect(self.discover_button, QtCore.SIGNAL(_fromUtf8("clicked()")),
                               MainWindow.discover_emu_bt_slot)
        QtCore.QObject.connect(self.bank1pushButton, QtCore.SIGNAL(_fromUtf8("clicked()")),
                               MainWindow.bank1_button_slot)
        QtCore.QObject.connect(self.bank2pushButton, QtCore.SIGNAL(_fromUtf8("clicked()")),
                               MainWindow.bank2_button_slot)
        QtCore.QObject.connect(self.bank3pushButton, QtCore.SIGNAL(_fromUtf8("clicked()")),
                               MainWindow.bank3_button_slot)
        QtCore.QObject.connect(self.browseButton, QtCore.SIGNAL(_fromUtf8("clicked()")),
                               MainWindow.browse_button_slot)
        QtCore.QObject.connect(self.help_button, QtCore.SIGNAL(_fromUtf8("clicked()")),
                               MainWindow.help_button_slot)
        QtCore.QObject.connect(self.read_sram_button, QtCore.SIGNAL(_fromUtf8("clicked()")),
                               MainWindow.read_sram_button_slot)
        QtCore.QObject.connect(self.reset_button, QtCore.SIGNAL(_fromUtf8("clicked()")),
                               MainWindow.reset_emu_slot)
        QtCore.QObject.connect(self.emulate_button, QtCore.SIGNAL(_fromUtf8("clicked()")),
                               MainWindow.emulate_button_slot)
        QtCore.QObject.connect(self.open_in_editor, QtCore.SIGNAL(_fromUtf8("clicked()")),
                               MainWindow.open_in_editor_button_slot)
        QtCore.QObject.connect(self.read_bank_button, QtCore.SIGNAL(_fromUtf8("clicked()")),
                               MainWindow.read_bank_button_slot)
        QtCore.QObject.connect(self.bank_name_line_edit, QtCore.SIGNAL(_fromUtf8("editingFinished()")),
                               MainWindow.bank_name_line_edit_text_changed_event_slot)
        QtCore.QObject.connect(self.reflash_button, QtCore.SIGNAL(_fromUtf8("clicked()")),
                               MainWindow.reflash_button_slot)
        self.command_line.returnPressed.connect(MainWindow.command_line_slot)
        #self.command_line.keyPressEvent(QKeyEvent(QEvent.KeyPress, QtCore.Qt.Key_Up, QtCore.Qt.NoModifier))
        #self.console_text_browser.selectionChanged.connect(MainWindow.console_select_text_slot)
        #self.bank_name_line_edit.editingFinished.connect(MainWindow.bank_name_edit_slot)

# if __name__ == "__main__":
#     main.start()
