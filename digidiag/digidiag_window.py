# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'untitled.ui'
#
# Created by: PyQt4 UI code generator 4.12.1
#
# WARNING! All changes made in this file will be lost!

import pickle
from PyQt4 import QtCore, QtGui, Qt
from PyQt4.QtCore import QEvent, pyqtSignal
import time, json, os

DIGIDIAG_STATUS_DIR = ''
VALUES_FILE_NAME = 'values.json'

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


class ValuesEditor(QtGui.QWidget):
    def __init__(self):
        QtGui.QWidget.__init__(self)
        self.table_header = ['NAME', 'UNITS', 'FRAME ID', 'BYTES SIZE', 'OFFSET', 'FORMULA', 'READING', 'REMOVE']
        self.table = QtGui.QTableWidget(self)

        self.table.setColumnCount(len(self.table_header))
        #self.table.setRowCount(1)
        #self.table.setItem(0, self.coln('READING'), self.__read_only_item())
        self.table.setHorizontalHeaderLabels(self.table_header)
        self.add_button = QtGui.QPushButton('ADD NEW')
        #self.table.setItem(0, self.table_header.index('REMOVE'), self.delete_cell_button())
        self.table.cellDoubleClicked.connect(self.cell_double_clicked)
        self.gridLayout = QtGui.QGridLayout(self)
        self.gridLayout.addWidget(self.table, 0, 0, 5, 5)
        self.gridLayout.addWidget(self.add_button, 6, 4)
        self.add_button.clicked.connect(self.add_row)
        self.values = {}
        self.__values_file_path = os.path.join(DIGIDIAG_STATUS_DIR, VALUES_FILE_NAME)
        self.read_status_file()


    def read_status_file(self):
        try:
            with open(self.__values_file_path, 'r') as json_str:
                self.values = json.loads(json_str.read())
        except (IOError, ValueError):
            self.values = {}

        row = 0
        for value_name in sorted(self.values.keys(), key=lambda s: s.lower()):
            self.add_row()
            for value_property_name in self.values[value_name]:
                property = self.values[value_name][str(value_property_name)]
                if property:
                    if property == 'DELETE':
                        self.table.setItem(row, self.coln(value_property_name), self.delete_cell_button())
                    else:
                        self.table.setItem(row, self.coln(value_property_name), QtGui.QTableWidgetItem(property))
            row += 1
        self.table.cellChanged.connect(self.cell_changed_slot)

    def dump_status_file(self):
        with open(self.__values_file_path, 'w') as json_dump:
            json.dump(self.values, json_dump, indent=4)

    def __read_only_item(self):
        item = QtGui.QTableWidgetItem()
        item.setFlags(item.flags() ^ Qt.Qt.ItemIsEditable)
        return item

    def delete_cell_button(self):
        del_cell = QtGui.QTableWidgetItem("DELETE")
        del_cell.setTextColor(QtGui.QColor(180, 48, 45))
        del_cell.setBackgroundColor(QtGui.QColor(204, 227, 240))
        font = QtGui.QFont()
        font.setBold(True)
        del_cell.setToolTip('double clik to remove line')
        del_cell.setTextAlignment(Qt.Qt.AlignCenter)
        del_cell.setFont(font)
        return del_cell

    def coln(self, col_name):
        return self.table_header.index(col_name)

    def cell_double_clicked(self, *cell, **kwargs):
        if cell[1] == self.table_header.index('REMOVE'):
            self.table.removeRow(cell[0])
        self.__update_values()

    def __update_values(self):
        self.values = {}
        for row in xrange(self.table.rowCount()):
            try:
                value_name = str(self.table.item(row, self.table_header.index('NAME')).text())
                self.values[value_name] = {}
                for property in self.table_header:
                    try:
                        val_property = self.table.item(row, self.table_header.index(property)).text()
                        self.values[value_name][property] = str(val_property)
                    except AttributeError:
                        self.values[value_name][property] = None
            except AttributeError:
                pass

    def cell_changed_slot(self):
        self.__update_values()

    def add_row(self):
        self.table.setRowCount(self.table.rowCount() + 1)
        current_row = self.table.rowCount() - 1
        self.table.setItem(current_row , self.coln('REMOVE'), self.delete_cell_button())


    def __del__(self):
        self.dump_status_file()


class Ui_Form(object):
    def setupUi(self, Form):
        Form.setObjectName(_fromUtf8("Form"))
        self.resize(1000, 600)
        self.gridLayout = QtGui.QGridLayout(Form)
        self.gridLayout.setObjectName(_fromUtf8("gridLayout"))
        self.horizontalLayout = QtGui.QHBoxLayout()
        self.horizontalLayout.setObjectName(_fromUtf8("horizontalLayout"))

        self.pushButton_3 = QtGui.QPushButton(Form)
        self.pushButton_3.setObjectName(_fromUtf8("pushButton_3"))



        self.horizontalLayout.addWidget(self.pushButton_3)
        self.pushButton_2 = QtGui.QPushButton(Form)
        self.pushButton_2.setObjectName(_fromUtf8("pushButton_2"))

        self.horizontalLayout.addWidget(self.pushButton_2)
        self.pushButton = QtGui.QPushButton(Form)
        self.pushButton.setObjectName(_fromUtf8("pushButton"))

        self.horizontalLayout.addWidget(self.pushButton)
        self.pushButton_4 = QtGui.QPushButton(Form)
        self.pushButton_4.setObjectName(_fromUtf8("pushButton_4"))

        self.horizontalLayout.addWidget(self.pushButton_4)
        self.checkBox_2 = QtGui.QCheckBox(Form)
        self.checkBox_2.setObjectName(_fromUtf8("checkBox_2"))

        self.horizontalLayout.addWidget(self.checkBox_2)
        self.checkBox = QtGui.QCheckBox(Form)
        self.checkBox.setObjectName(_fromUtf8("checkBox"))

        self.horizontalLayout.addWidget(self.checkBox)
        self.gridLayout.addLayout(self.horizontalLayout, 0, 0, 1, 1)

        self.tabWidget = QtGui.QTabWidget(Form)

        self.tabWidget.setObjectName(_fromUtf8("tabWidget"))
        self.tab = QtGui.QWidget()


        self.tab.setObjectName(_fromUtf8("tab"))
        self.tabWidget.addTab(self.tab, _fromUtf8(""))

        self.values = ValuesEditor()
        self.values.setObjectName(_fromUtf8("values"))
        self.tabWidget.addTab(self.values, _fromUtf8(""))
        self.gridLayout.addWidget(self.tabWidget, 1, 0, 1, 1)

        self.retranslateUi(Form)
        self.tabWidget.setCurrentIndex(1)
        QtCore.QMetaObject.connectSlotsByName(Form)

    def retranslateUi(self, Form):
        Form.setWindowTitle(_translate("Form", "Form", None))
        self.pushButton_3.setText(_translate("Form", "PushButton", None))
        self.pushButton_2.setText(_translate("Form", "PushButton", None))
        self.pushButton.setText(_translate("Form", "PushButton", None))
        self.pushButton_4.setText(_translate("Form", "PushButton", None))
        self.checkBox_2.setText(_translate("Form", "CheckBox", None))
        self.checkBox.setText(_translate("Form", "CheckBox", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab), _translate("Form", "Tab 1", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.values), _translate("Form", "VALUES", None))

class MainWindow(QtGui.QMainWindow, Ui_Form):

    def __init__(self):
        QtGui.QMainWindow.__init__(self)
        Ui_Form.__init__(self)
        self.centralwidget = QtGui.QWidget(self)
        self.setCentralWidget(self.centralwidget)
        self.setupUi(self.centralwidget)
        self.show()

        self.pushButton_3.clicked.connect(self.add_tab)

    def add_tab(self):
        count = self.tabWidget.count()
        self.tabWidget.insertTab(count - 1, QtGui.QWidget(self), 'new {}'.format(count))



if __name__ == "__main__":
    import sys

    app = QtGui.QApplication(sys.argv)
    myapp = MainWindow()
    # myapp.setWindowIcon(QtGui.QIcon(os.path.join('spec', 'icon.ico')))
    myapp.setWindowIcon(QtGui.QIcon('icon.png'))
    # app.setWindowIcon(QtGui.QIcon(os.path.join('spec', 'icon.ico')))

    myapp.show()
    app.exec_()
    sys.exit()
    sys.stdout = _stdout
    sys.stderr = _stderr