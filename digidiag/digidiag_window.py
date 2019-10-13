# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'untitled.ui'
#
# Created by: PyQt4 UI code generator 4.12.1
#
# WARNING! All changes made in this file will be lost!

import pickle
from PyQt4 import QtCore, QtGui, Qt
from PyQt4.QtCore import QEvent, pyqtSignal
from objects_with_help import PushButton, HelpTip
import time, json, os
import struct
import traceback
from setup_emubt import EMU_BT_PATH
import types

DIGIDIAG_STATUS_DIR = EMU_BT_PATH
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
    item.setBackgroundColor(QtGui.QColor(204, 227, 240))
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


def invalid_table_item(item, message):
    invalid_item = QtGui.QTableWidgetItem(item)
    invalid_item.setBackgroundColor(QtGui.QColor(180, 48, 45))
    invalid_item.setToolTip(message)
    return invalid_item


def valid_table_item(formula, message='field is valid'):
    item = QtGui.QTableWidgetItem(formula)
    item.setBackgroundColor(QtGui.QColor(213, 230, 237))
    item.setToolTip(message)
    return item

def class_attr_to_colname(attr):
    return attr.upper().replace('_', ' ')

def colname_to_class_attr(colname):
    return colname.lower().replace(' ', '_')

class PublicAttrsAbstract():
    """
    This is abstract class
    """
    @classmethod
    def p_attrs(cls):
        """
        Return public (non pseudo-private attrs)
        :return:
        """
        return [ v for v in cls.__dict__.keys() if '__' not in v and type(getattr(cls, v)) is not types.ClassType and not callable(getattr(cls, v))]

    @classmethod
    def p_attrs_as_column_names(cls):
        """
        Return public (non pseudo-private attrs)
        :return:
        """
        return [class_attr_to_colname(i) for i in cls.p_attrs()]

class Value(PublicAttrsAbstract):
    name = None,
    delete = None,

    class decode_info(PublicAttrsAbstract):
        units = None,
        frame_id= None,
        bytes_size = None,
        offset = None,
        formula = None,
        def __init__(self, units, frame_id, bytes_size, offset, formula):
            self.units = units
            self.frame_id = frame_id
            self.bytes_size = bytes_size
            self.offset = offset
            self.formula = formula

        def to_json(self):
            return {k: getattr(self, k) for k in self.p_attrs()}

    class display_attrs(PublicAttrsAbstract):
        reading = None,
        raw = None,
        def __init__(self):
            self.reading = ''
            self.raw = ''

    def __init__(self, name, units, frame_id, bytes_size, offset, formula, delete_button):
        self.decode_info = Value.decode_info(units, frame_id, bytes_size, offset, formula)
        self.name = name
        self.delete = delete_button

    def __repr__(self):
        return '' \
            'name: {name}\n' \
            'units: {units}\n' \
            'frame_id: {frame_id}\n' \
            'bytes_size: {bytes_size}\n' \
            'offset: {offset}\n' \
            'formula: {formula}'.format(
            name=self.name,
            units=self.decode_info.units,
            frame_id=self.decode_info.frame_id,
            bytes_size=self.decode_info.bytes_size,
            offset=self.decode_info.offset,
            formula=self.decode_info.formula)


class Table(QtGui.QTableWidget):
    def __init__(self, header_labels, *args, **kwargs):
        self.horizonatal_header_labels = header_labels
        QtGui.QTableWidget.__init__(self, *args, **kwargs)

    def column_index(self, column_string):
        return self.horizonatal_header_labels.index(column_string)

    def delete_value_slot(self, button_id):
        del_button_col_index = self.column_index('DELETE')
        for row in xrange(self.rowCount()):
            del_button = self.cellWidget(row, del_button_col_index)
            if del_button == button_id:
                self.removeRow(row)
                #self.__update_values()
                break

    def create_delete_row_button(self):
        delete_button = PushButton('delete')
        delete_button.clicked_s.connect(self.delete_value_slot)
        return delete_button

    def add_row(self):
        self.setRowCount(self.rowCount() + 1)
        current_row = self.rowCount() - 1
        delete_button = self.create_delete_row_button()
        del_index = self.column_index('DELETE')
        self.setCellWidget(current_row, del_index, delete_button)

        reading_index = self.column_index('READING')
        self.setItem(current_row, reading_index, read_only_table_item())

        raw_index = self.column_index('RAW')
        self.setItem(current_row, raw_index, read_only_table_item())


class ValuesEditor(QtGui.QWidget):
    """
    Creates decoding info for values received in digiframes.
    Validates formula to calculate the value.
    display_value: will convert raw value according to formula and display in READING column
    """
    apply_button_singnal = pyqtSignal()
    cell_button_clicked = pyqtSignal(object)

    def __init__(self):
        QtGui.QWidget.__init__(self)

        self.__table_header = Value.p_attrs_as_column_names() + Value.decode_info.p_attrs_as_column_names() + Value.display_attrs.p_attrs_as_column_names()
        #self.__table_header = map(lambda i: i.upper().replace('_', ' '), self.__table_header)
        self.__table_header.sort(key='DELETE'.__eq__)       #move delete column to the end


        self.valuesEditorLayout = QtGui.QGridLayout(self)

        self.table = Table(self.__table_header)
        self.table.setColumnCount(len(self.__table_header))
        self.table.setHorizontalHeaderLabels(self.__table_header)
        self.add_button = PushButton('ADD NEW', tip_msg="Add new value")
        self.apply_button = PushButton('APPLY', tip_msg="Verifies and saves values table")

        self.add_button.clicked.connect(self.table.add_row)
        self.apply_button.clicked.connect(self.apply_button_slot)

        self.values = dict()

        self.__values_file_path = os.path.join(DIGIDIAG_STATUS_DIR, VALUES_FILE_NAME)

        self.valuesEditorLayout.addWidget(self.table, 0, 0, 5, 5)
        self.valuesEditorLayout.addWidget(self.apply_button, 6, 3)
        self.valuesEditorLayout.addWidget(self.add_button, 6, 4)

        self.read_status_file()


    def __validate_formula(self, formula_str):
        formula_str = formula_str.lower()
        expr = eval('lambda x: {formula}'.format(formula=formula_str))
        expr(1)     #test of formula
        return expr


    def read_status_file(self):
        try:
            with open(self.__values_file_path, 'r') as json_str:
                values = json.loads(json_str.read())
        except (IOError, ValueError):
            values = dict()

        self.values = {}

        row = 0
        for value_name in values:
            self.table.add_row()
            self.table.setItem(row, self.table.column_index('NAME'), QtGui.QTableWidgetItem(value_name))
            value_dict = {}
            for column in values[value_name]:
                cell_value = QtGui.QTableWidgetItem(values[value_name][column])
                value_dict[column] = values[value_name][column]
                column = class_attr_to_colname(column)
                self.table.setItem(row, self.table.column_index(column), cell_value)
            value = Value(name=value_name, delete_button=self.table.create_delete_row_button(), **value_dict)
            self.values[value_name] = value
            print self.values
            row += 1
        #self.__update_values()

    def dump_values_to_file(self):
        json_friendly_values = {}
        for v in self.values:
            json_friendly_values[v] = self.values[v].decode_info.to_json()
        with open(self.__values_file_path, 'w') as json_dump:
            json.dump(json_friendly_values, json_dump, indent=4)
            print 'json dumped to', self.__values_file_path

    # def __coln(self, col_name):
    #     return self.__table_header.index(col_name)

    # def __assign_formula(self, row, col_name, value_name):
    #     """
    #     assigns decoding formula for given value
    #     :param row:
    #     :param col_name:
    #     :param value_name:
    #     :return:
    #     """
    #     formula = str(self.table.item(row, self.__table_header.index(col_name)).text())
    #     try:
    #         validated_formula = self.__validate_formula(formula)
    #         self.values_calculator[value_name] = validated_formula
    #     except Exception as e:
    #         self.table.setItem(row, self.__coln(col_name), invalid_table_item(formula, e.message))
    #     else:
    #         self.table.setItem(row, self.__coln(col_name), valid_table_item(formula, message=formula))

    # def __assign_frame_id(self, row, col_name, value_name):
    #     frame_id = str(self.table.item(row, self.__table_header.index(col_name)).text()).lower()
    #     validated_id = frame_id
    #     try:
    #         if '0x' in frame_id:
    #             validated_id = int(frame_id, 16)
    #         else:
    #             validated_id = int(frame_id)
    #     except Exception as e:
    #         self.table.setItem(row, self.__coln(col_name), invalid_table_item(frame_id, e.message))
    #     else:
    #         self.table.setItem(row, self.__coln(col_name), valid_table_item(frame_id, message=frame_id))
    #     return validated_id
    #
    # def __is_field_integer(self, row, col_name):
    #     frame_id = str(self.table.item(row, self.__table_header.index(col_name)).text()).lower()
    #     validated_id = '0'
    #     try:
    #         validated_id = int(frame_id)
    #     except Exception as e:
    #         self.table.setItem(row, self.__coln(col_name), invalid_table_item(frame_id, e.message))
    #     else:
    #         self.table.setItem(row, self.__coln(col_name), valid_table_item(frame_id, message=frame_id))
    #     return validated_id

    def __update_values(self):
        for row in xrange(self.table.rowCount()):
            value_descriptor = {}
            for column in self.table.horizonatal_header_labels:
                try:
                    item = self.table.item(row, self.table.column_index(column))
                    if item.flags() & Qt.Qt.ItemIsEditable:
                        value_descriptor[colname_to_class_attr(column)] = str(item.text())
                except AttributeError as e:
                    print column, e
            value = Value(delete_button=self.table.cellWidget(row, self.table.column_index('DELETE')), **value_descriptor)
            self.values[value.name] = value

        self.dump_values_to_file()
        return

    def apply_button_slot(self):
        self.__update_values()

    def display_value(self, value_name, raw_value, byte_size):
        """
        Fills column READING at given value_name with value
        :param value_name:
        :param value:
        :param raw_value: raw value
        :return:
        """
        try:
            value = self.values_calculator[value_name](raw_value)
        except ZeroDivisionError:
            value = 'NaN'
        self.values_display_dict[value_name].setData(Qt.Qt.DisplayRole, value)
        self.raw_values_display_dict[value_name].setData(Qt.Qt.DisplayRole, '0x{val:0{bsiz}X}'.format(bsiz=byte_size*2, val=raw_value))

    # def add_row(self):
    #     self.table.setRowCount(self.table.rowCount() + 1)
    #     current_row = self.table.rowCount() - 1
    #     delete_button = self.table.create_delete_row_button()
    #     del_index = self.table.column_index('DELETE')
    #     self.table.setCellWidget(current_row, del_index, delete_button)
    #
    #     reading_index = self.table.column_index('READING')
    #     self.table.setItem(current_row, reading_index, read_only_table_item())
    #
    #     raw_index = self.table.column_index('RAW')
    #     self.table.setItem(current_row, raw_index, read_only_table_item())


    def __del__(self):
        self.dump_values_to_file()

    def closeEvent(self, event):
        if event.type() == QEvent.Close:
            self.dump_values_to_file()

    def destroyEvent(self, event):
        if event.type() == QEvent.Destroy:
            self.dump_values_to_file()


class DigidiagWindow(QtGui.QWidget):
    def __init__(self):

        QtGui.QWidget.__init__(self)
        x_siz, y_siz = 1000, 600

        self.setWindowTitle("DIGIDIAG")
        self.__ord_to_int_vs_size = {
            1: lambda v: struct.unpack('B', v),
            2: lambda v: struct.unpack('>H', v),
            4: lambda v: struct.unpack('>I', v),
        }

        self.frames = dict()
        self.values_extractor = {}

        self.gridLayout = QtGui.QGridLayout(self)
        self.horizontalLayout = QtGui.QHBoxLayout()

        self.add_view_btn = PushButton('ADD VIEW', tip_msg="Add new view")
        self.button2 = QtGui.QPushButton('B2')
        self.button3 = QtGui.QPushButton('B3')

        self.tabWidget = QtGui.QTabWidget(self)
        self.values_editor = ValuesEditor()
        self.values_editor.apply_button_singnal.connect(self.define_extraction_rules)

        self.tabWidget.addTab(self.values_editor, 'VALUES')

        self.horizontalLayout.addWidget(self.add_view_btn)
        self.horizontalLayout.addWidget(self.button2)
        self.horizontalLayout.addWidget(self.button3)


        self.gridLayout.addLayout(self.horizontalLayout, 0, 0, 1, 1)
        self.gridLayout.addWidget(self.tabWidget, 1, 0, 1, 1)

        self.resize(x_siz, y_siz)
        self.show()
        self.define_extraction_rules()

    def define_extraction_rules(self):
        #self.__table_header = ['NAME', 'UNITS', 'FRAME ID', 'BYTES SIZE', 'OFFSET', 'FORMULA', 'READING', 'RAW', 'REMOVE']
        values_definition = self.values_editor.values_decoder
        self.values_extractor = {}
        for key in values_definition:
            #self.values_extractor[key] = {}
            frame_id = values_definition[key]['FRAME ID']
            self.values_extractor[key] = {
                'FRAME ID': int(frame_id, 16) if '0x' in frame_id else int(frame_id),
                'OFFSET': int(values_definition[key]['OFFSET']),
                'BYTES SIZE': int(values_definition[key]['BYTES SIZE']),
            }

    def feed_data(self, frame):
        frame_id = ord(frame[1])
        self.frames[frame_id] = frame[2:]

    def refresh(self):
        for value in self.values_extractor:
            frame_id = self.values_extractor[value]['FRAME ID']
            offset = self.values_extractor[value]['OFFSET']
            byte_size = self.values_extractor[value]['BYTES SIZE']
            try:
                raw_value = self.frames[frame_id][offset:offset + byte_size]
                raw_value = self.__ord_to_int_vs_size[byte_size](raw_value)[0]
                self.values_editor.display_value(value, raw_value, byte_size)
            except (KeyError, struct.error) as e:
                pass


if __name__ == "__main__":
    import sys

    class MainW(QtGui.QMainWindow):
        hlp_sig = pyqtSignal(object)
        def __init__(self):
            QtGui.QMainWindow.__init__(self)
            HelpTip.set_static_help_tip_slot_signal(self.hlp_sig)
            self.hlp_sig.connect(self.tip)

            self.centralwidget = QtGui.QWidget(self)
            self.setCentralWidget(self.centralwidget)
            self.values = ValuesEditor()
            self.values.resize(1000, 500)
            self.values.show()
            self.resize(400, 400)
            self.show()

        def tip(self, *args):
            print args

    app = QtGui.QApplication(sys.argv)
    myapp = MainW()
    # myapp.setWindowIcon(QtGui.QIcon(os.path.join('spec', 'icon.ico')))
    myapp.setWindowIcon(QtGui.QIcon('icon.png'))
    # app.setWindowIcon(QtGui.QIcon(os.path.join('spec', 'icon.ico')))

    myapp.show()
    app.exec_()
    sys.exit()
    sys.stdout = _stdout
    sys.stderr = _stderr