"""
author: Rafal Miecznik
contact: ravmiecznk@gmail.com
"""

from PyQt4 import QtCore, QtGui

BACKGROUND = "background-color: rgb({},{},{})"
GREEN_STYLE_SHEET = BACKGROUND.format(154,252,41)
GREY_STYLE_SHEET = BACKGROUND.format(48,53,58)

class HelpTip():
    help_tip_slot = None
    def __init__(self, help_msg=None):
        self.help_msg = help_msg
        self.tip_displayed = False

    @staticmethod
    def set_static_help_tip_slot_signal(signal):
        HelpTip.help_tip_slot = signal

    def tip(self):
        tip_msg = self.help_msg
        self.help_tip_slot.emit(tip_msg)
        self.tip_displayed = True
        self.timer.stop()

    def enterEvent(self, QEvent):
        if self.help_msg:
            self.timer = QtCore.QTimer()
            self.timer.connect(self.timer, QtCore.SIGNAL("timeout()"), self.tip)
            self.timer.start(500)

    def test(self):
        """
        method for testing purposes
        :return:
        """
        if self.help_msg:
            self.timer = QtCore.QTimer()
            self.timer.connect(self.timer, QtCore.SIGNAL("timeout()"), self.tip)
            self.timer.start(500)

    def leaveEvent(self, QEvent):
        if self.help_msg and self.tip_displayed:
            self.help_tip_slot.emit('')

class PushButton(QtGui.QPushButton, HelpTip):
    def __init__(self, *args, **kwargs):
        tip_msg = kwargs.pop('tip_msg')
        QtGui.QPushButton.__init__(self, *args, **kwargs)
        HelpTip.__init__(self, tip_msg)
        self._default_style_sheet = self.styleSheet()
        self.set_default_style_sheet()
        self._active_style = False

    def set_default_style_sheet(self):
        self.setStyleSheet(self._default_style_sheet)

    def set_green_style_sheet(self):
        self.setStyleSheet(GREEN_STYLE_SHEET)
        self.clearFocus()

    def blink(self):
        if self._active_style:
            self.set_default_style_sheet()
        else:
            self.set_green_style_sheet()
        self._active_style ^= True

    #
    # def blink_stop(self):
    #     self.blink.stop()
    #     self.set_default_style_sheet()


class CheckBox(QtGui.QCheckBox, HelpTip):
    def __init__(self, *args, **kwargs):
        tip_msg = kwargs.pop('tip_msg')
        QtGui.QPushButton.__init__(self, *args, **kwargs)
        HelpTip.__init__(self, tip_msg)

class ComboBox(QtGui.QComboBox, HelpTip):
    def __init__(self, *args, **kwargs):
        tip_msg = kwargs.pop('tip_msg')
        QtGui.QComboBox.__init__(self, *args, **kwargs)
        HelpTip.__init__(self, tip_msg)

    def getItems(self):
        return [str(self.itemText(i)) for i in range(self.count())]

class LcdDisplay(QtGui.QLCDNumber, HelpTip):
    def __init__(self, *args, **kwargs):
        tip_msg = kwargs.pop('tip_msg')
        QtGui.QLCDNumber.__init__(self, *args, **kwargs)
        HelpTip.__init__(self, tip_msg)


class LineEdit(QtGui.QLineEdit, HelpTip):
    def __init__(self, *args, **kwargs):
        tip_msg = kwargs.pop('tip_msg')
        QtGui.QLineEdit.__init__(self, *args, **kwargs)
        HelpTip.__init__(self, tip_msg)