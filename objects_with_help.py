"""
author: Rafal Miecznik
contact: ravmiecznk@gmail.com
"""

from PyQt4 import QtCore, QtGui
from event_handler import to_signal

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
        self.setAcceptDrops(False)

    def editTextChanged_with_delay_connect_to_signal(self, ext_signal):
        self.edit_text_changed_signal = ext_signal
        self.editTextChanged.connect(to_signal(self.edit_text_changed_timer))

    def edit_text_changed_timer(self):
        self.timer = QtCore.QTimer()
        self.timer.connect(self.timer, QtCore.SIGNAL("timeout()"), self.edit_text_timeout)
        self.timer.start(500)

    def edit_text_timeout(self):
        self.edit_text_changed_signal.emit()
        self.timer.stop()
    
    #TODO:
    #refactor this name for PEP8 compliant
    def getItems(self):
        return [str(self.itemText(i)) for i in range(self.count())]

    #TODO:
    #refactor this name for PEP8 compliant
    def moveOnTop(self, item):
        """
        Move item on top of list view
        :param item:
        :return:
        """
        items = self.getItems()
        try:
            items.remove(item)
        except ValueError:
            pass
        self.clear()
        self.addItems(items)
        self.insertItem(0, item)
        self.setCurrentIndex(0)

    #TODO:
    #refactor this name for PEP8 compliant
    def removeByStr(self, string):
        """
        Remove item by string and update view
        :param string:
        :return:
        """
        items = self.getItems()
        try:
            items.remove(string)
            self.clear()
            self.addItems(items)
        except ValueError:
            pass



class LcdDisplay(QtGui.QLCDNumber, HelpTip):
    def __init__(self, *args, **kwargs):
        tip_msg = kwargs.pop('tip_msg')
        QtGui.QLCDNumber.__init__(self, *args, **kwargs)
        HelpTip.__init__(self, tip_msg)


class LineEdit(QtGui.QLineEdit, HelpTip):
    def __init__(self, *args, **kwargs):
        tip_msg = kwargs.pop('tip_msg')
        self.focus_event = kwargs.pop('focus_event')
        self.focus_out_event = kwargs.pop('focus_out_event')
        QtGui.QLineEdit.__init__(self, *args, **kwargs)
        HelpTip.__init__(self, tip_msg)

    def focusInEvent(self, event):
        QtGui.QLineEdit.focusInEvent(self, event)
        self.focus_event()

    def focusOutEvent(self, event):
        QtGui.QLineEdit.focusOutEvent(self, event)
        self.focus_out_event()
