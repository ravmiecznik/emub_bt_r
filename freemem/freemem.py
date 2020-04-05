#!/usr/bin/python
"""
author: Rafal Miecznik
contact: ravmiecznk@gmail.com
created: 30.03.2020$
"""

from PyQt4 import QtGui
from PyQt4.QtCore import QEvent
from message_handler import MessageSender
from gui_thread import thread_this_method
from plotter import Plotter



class FreeMemPlotter(Plotter):
    def __init__(self, message_sender):
        Plotter.__init__(self, title="FREE MEMORY", x_label="time", y_label="freemem")

        self.lcd = QtGui.QLCDNumber()
        self.lcd.setSegmentStyle(QtGui.QLCDNumber.Flat)
        self.gridLayout.addWidget(self.lcd, 11, 10, 1, 1)

        self.message_sender = message_sender
        self.freemem_request_thread()
        self.sample = 0

    def update_xy(self, freemem):
        self.update_plot_xy_signal.emit(self.sample, freemem)
        self.sample += 1
        self.lcd.display(freemem)

    @thread_this_method(period=2)
    def freemem_request_thread(self):
        self.message_sender.send(m_id=MessageSender.ID.freemem)


    def closeEvent(self, event):
        if event.type() == QEvent.Close:
            self.freemem_request_thread.terminate()
