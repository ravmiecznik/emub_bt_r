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
from copy import copy

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


def read_only_table_item():
    item = QtGui.QTableWidgetItem()
    item.setFlags(item.flags() ^ Qt.Qt.ItemIsEditable)
    return item


def delete_cell_button_table_item():
    del_cell = QtGui.QTableWidgetItem("DELETE")
    del_cell.setTextColor(QtGui.QColor(180, 48, 45))
    del_cell.setBackgroundColor(QtGui.QColor(204, 227, 240))
    font = QtGui.QFont()
    font.setBold(True)
    del_cell.setToolTip('double clik to remove line')
    del_cell.setTextAlignment(Qt.Qt.AlignCenter)
    del_cell.setFont(font)
    return del_cell


def invalid_formula_table_item(formula, message):
    invalid_formula_item = QtGui.QTableWidgetItem(formula)
    invalid_formula_item.setBackgroundColor(QtGui.QColor(180, 48, 45))
    invalid_formula_item.setToolTip(message)
    return invalid_formula_item


def valid_formula_table_item(formula, message='formula is valid'):
    item = QtGui.QTableWidgetItem(formula)
    item.setBackgroundColor(QtGui.QColor(140, 208, 211))
    item.setToolTip(message)
    return item

class ValuesEditor(QtGui.QWidget):
    """
    Creates decoding info for values received in digiframes.
    Validates formula to calculate the value.
    display_value: will convert raw value according to formula and display in READING column
    """
    def __init__(self):
        QtGui.QWidget.__init__(self)
        self.__table_header = ['NAME', 'UNITS', 'FRAME ID', 'BYTES SIZE', 'OFFSET', 'FORMULA', 'READING', 'RAW', 'REMOVE']
        self.table = QtGui.QTableWidget(self)


        self.table.setColumnCount(len(self.__table_header))
        self.table.setHorizontalHeaderLabels(self.__table_header)
        self.add_button = QtGui.QPushButton('ADD NEW')
        self.apply_button = QtGui.QPushButton('APPLY')
        self.table.cellDoubleClicked.connect(self.cell_double_clicked)
        self.gridLayout = QtGui.QGridLayout(self)
        self.gridLayout.addWidget(self.table, 0, 0, 5, 5)
        self.gridLayout.addWidget(self.apply_button, 6, 3)
        self.gridLayout.addWidget(self.add_button, 6, 4)
        self.add_button.clicked.connect(self.add_row)
        self.apply_button.clicked.connect(self.table_save_slot)

        self.values_decoder = {}
        self.values_calculator = {}
        self.values_display_dict = {}

        self.__values_file_path = os.path.join(DIGIDIAG_STATUS_DIR, VALUES_FILE_NAME)
        self.read_status_file()
        self.table.cellPressed.connect(self.table_save_slot)
        for d in dir(QtGui.QTableWidgetItem()):
            print d


    def __validate_formula(self, formula_str):
        formula_str = formula_str.lower()
        expr = eval('lambda x: {formula}'.format(formula=formula_str))
        expr(1)     #test of formula
        return expr


    def read_status_file(self):
        try:
            with open(self.__values_file_path, 'r') as json_str:
                self.values_decoder = json.loads(json_str.read())
        except (IOError, ValueError):
            self.values_decoder = {}

        row = 0
        for value_name in sorted(self.values_decoder.keys(), key=lambda s: s.lower()):
            self.add_row()
            for value_property_name in self.values_decoder[value_name]:
                col_name = self.values_decoder[value_name][str(value_property_name)]
                if col_name:
                    if col_name == 'DELETE':
                        self.table.setItem(row, self.__coln(value_property_name), delete_cell_button_table_item())
                    else:
                        self.table.setItem(row, self.__coln(value_property_name), QtGui.QTableWidgetItem(col_name))
            row += 1
        self.__update_values()

    def dump_status_file(self):
        with open(self.__values_file_path, 'w') as json_dump:
            json.dump(self.values_decoder, json_dump, indent=4)


    def __coln(self, col_name):
        return self.__table_header.index(col_name)

    def cell_double_clicked(self, *cell, **kwargs):
        if cell[1] == self.__table_header.index('REMOVE'):
            self.table.removeRow(cell[0])
        self.__update_values()

    def __assign_formula(self, row, col_name, value_name):
        """
        assigns decoding formula for given value
        :param row:
        :param col_name:
        :param value_name:
        :return:
        """
        formula = str(self.table.item(row, self.__table_header.index(col_name)).text())
        try:
            validated_formula = self.__validate_formula(formula)
            self.values_calculator[value_name] = validated_formula
        except Exception as e:
            self.table.setItem(row, self.__coln(col_name), invalid_formula_table_item(formula, e.message))
        else:
            self.table.setItem(row, self.__coln(col_name), valid_formula_table_item(formula, message=formula))

    def __update_values(self):
        self.values_decoder = {}
        for row in xrange(self.table.rowCount()):
            try:
                value_name = str(self.table.item(row, self.__table_header.index('NAME')).text())
                self.values_decoder[value_name] = {}
                for col_name in self.__table_header:
                    try:
                        if col_name == 'FORMULA':
                            self.__assign_formula(row, col_name, value_name)
                        elif col_name == 'READING':
                            val_display = read_only_table_item()
                            self.table.setItem(row, self.__coln(col_name), val_display)
                            self.values_display_dict[value_name] = val_display
                        val_property = self.table.item(row, self.__table_header.index(col_name)).text()
                        self.values_decoder[value_name][col_name] = str(val_property)
                    except AttributeError:
                        self.values_decoder[value_name][col_name] = None
            except AttributeError:
                pass

    def table_save_slot(self):
        self.__update_values()
        self.display_value('test', 2)
        try:
            self.display_value('test', 2)
        except KeyError:
            pass

    def display_value(self, value_name, raw_value):
        """
        Fills column READING at given value_name with value
        :param value_name:
        :param value:
        :param raw_value: raw value
        :return:
        """
        value = self.values_calculator[value_name](raw_value)
        #value = str(value)
        self.values_display_dict[value_name].setData(Qt.Qt.DisplayRole, value)

    def add_row(self):
        self.table.setRowCount(self.table.rowCount() + 1)
        current_row = self.table.rowCount() - 1
        self.table.setItem(current_row, self.__coln('REMOVE'), delete_cell_button_table_item())
        self.table.setItem(current_row, self.__coln('READING'), read_only_table_item())

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