"""
author: Rafal Miecznik
contact: ravmiecznk@gmail.com
"""

from PyQt4 import QtCore, QtGui, Qt
from PyQt4.QtCore import pyqtSignal
from pyqtgraph import PlotWidget, ScatterPlotItem, mkPen
from pyqtgraph import setConfigOptions as graphSetOptions

class Plotter(QtGui.QWidget):
    update_plot_xy_signal = pyqtSignal(object, object)
    def __init__(self, parent, title='PLOTTER', x_label='X', y_label='Y'):
        QtGui.QWidget.__init__(self)
        self.gridLayout = QtGui.QGridLayout(self)
        self.setWindowTitle(title)


        #graph
        graphSetOptions(antialias=True)
        self.graph = PlotWidget()
        self.graph.setTitle(title)
        self.graph.setLabel('left', y_label)
        self.graph.setLabel('bottom', x_label)
        self.graph.showGrid(x=True, y=True)
        self.graph.setBackground((235, 236, 237))
        self.pen = mkPen(color=(46, 142, 226), width=3, style=QtCore.Qt.DashLine)
        self.gridLayout.addWidget(self.graph, 0, 1)
        self.update_plot_xy_signal.connect(self.update_graph_with_value)
        self.x_vect = []
        self.y_vect = []
        self.__x_range_was_set = False

    def set_max_x(self, value):
        self.graph.setXRange(0, value)
        self.__x_range_was_set = True

    def get_max(self):
        max_y = max(self.y_vect)
        x = self.x_vect[self.y_vect.index(max_y)]
        return x, max_y

    def get_min(self):
        min_y = min(self.y_vect)
        x = self.x_vect[self.y_vect.index(min_y)]
        return x, min_y

    def update_graph_with_value(self, x, y):
        self.x_vect.append(x)
        self.y_vect.append(y)
        y_max = 0
        y_min = 0
        x_max = 0
        for x_val in self.x_vect:
            y_val = self.y_vect[self.x_vect.index(x_val)]
            if y_val > y_max:
                y_max = y_val
            if y_val < y_min:
                y_min = y_val
            if x_val > x_max:
                x_max = x_val
        self.graph.clear()
        self.graph.setYRange(y_min - float(y_min)/10, y_max + float(y_max)/10)
        if self.__x_range_was_set is False:
            self.graph.setXRange(0, x_max + float(x_max)/10)
        self.graph.plot(self.x_vect, self.y_vect, symbol='o', pen=self.pen)
