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
from collections import OrderedDict

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


RED_COLOR = QtGui.QColor(180, 48, 45)
BLUE_COLOR = QtGui.QColor(213, 230, 237)


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


# def invalid_table_item(item, message):
#     invalid_item = QtGui.QTableWidgetItem(item)
#     invalid_item.setBackgroundColor(QtGui.QColor(180, 48, 45))
#     invalid_item.setToolTip(message)
#     return invalid_item
#
#
# def valid_table_item(value, message='field is valid'):
#     item = QtGui.QTableWidgetItem(value)
#     item.setBackgroundColor(QtGui.QColor(213, 230, 237))
#     item.setToolTip(message)
#     return item


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


class ValueTableRow(object, PublicAttrsAbstract):
    """
    This class decodes each value
    """
    name = ''
    delete = None

    class decode_info(object, PublicAttrsAbstract):
        units = None
        frame_id = None
        bytes_size = None
        offset = None
        formula = None
        def __init__(self, units, frame_id, bytes_size, offset, formula):
            self.units = units
            self.frame_id = frame_id
            self.bytes_size = bytes_size
            self.offset = offset
            self.formula = formula

        def to_json(self):
            json_dict = {k: getattr(self, k) for k in self.p_attrs()}
            return json_dict

    class display_attrs(PublicAttrsAbstract):
        reading = None
        raw = None
        def __init__(self):
            self.reading = ''
            self.raw = ''

    def __init__(self, name, units, frame_id, bytes_size, offset, formula, delete_button):
        self.decode_info = ValueTableRow.decode_info(units, frame_id, bytes_size, offset, formula)
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


class TableItemValidProperty():
    """
    This is abstract class
    """
    def set_valid(self, value=None, tool_tip=None):
        tool_tip = self.text() if tool_tip is None else tool_tip
        self.setBackgroundColor(BLUE_COLOR)
        self.setToolTip(tool_tip)
        if value:
            self.setText(value)

    def set_invalid(self, error_msg):
        self.setBackgroundColor(RED_COLOR)
        self.setToolTip(error_msg)


class OffsetTableItem(QtGui.QTableWidgetItem, TableItemValidProperty):
    def validate(self):
        value = str(self.text())
        try:
            value_int = int(value)
        except ValueError as e:
            try:
                value_int = int(value, 16)
            except ValueError as e:
                self.set_invalid(e.message)
                return
        try:
            if value_int < 255:
                self.set_valid(str(value_int))
            else:
                self.set_invalid("Offset exceeds 255")
        except UnboundLocalError as e:
            self.set_invalid(e.message)


class ByteSizeTableItem(QtGui.QTableWidgetItem, TableItemValidProperty):
    def validate(self):
        value = str(self.text())
        print value
        try:
            print 't1'
            value_int = int(value)
        except ValueError:
            print 't2'
            try:
                value_int = int(value, 16)
            except Exception as e:
                print 'except'
                self.set_invalid(e.message)
                return

        print 'else'
        if value_int < 5:
            self.set_valid('0x{:02X}'.format(value_int), str(value_int))
        else:
            self.set_invalid("Value exceeds 4")


class FormulaTableItem(QtGui.QTableWidgetItem, TableItemValidProperty):
    def validate(self):
        formula = str(self.text())
        try:
            l = eval('lambda x:{}'.format(formula))
        except SyntaxError as e:
            self.set_invalid(e.message)
            return
        try:
            l(1)
        except Exception as e:
            self.set_invalid(e.message)
            return
        self.set_valid()


class FrameIdTableItem(QtGui.QTableWidgetItem, TableItemValidProperty):
    def validate(self):
        value = str(self.text())
        try:
            value_int = int(value)
        except ValueError as e:
            try:
                value_int = int(value, 16)
            except ValueError as e:
                self.set_invalid(e.message)
                return

        try:
            if value_int < 255:
                self.set_valid('0x{:02X}'.format(value_int), str(value_int))
            else:
                self.set_invalid("Frame Id can't exceed 255")
        except UnboundLocalError as e:
            self.set_invalid(e.message)


class NameTableItem(QtGui.QTableWidgetItem, TableItemValidProperty):
    def validate(self):
        value = str(self.text())
        self.set_valid()
        if isinstance(value, str) and len(value) > 0:
            self.table_item = value
        else:
            self.set_invalid("name can't be empty")

class UnitsTableItem(NameTableItem):
    def __init__(self, initval='?'):
        NameTableItem.__init__(self, initval)


class Table(QtGui.QTableWidget):
    """
    Main Values Table.
    Stores values decode info.
    """
    remove_value_signal = pyqtSignal(object)
    def __init__(self, *args, **kwargs):
        QtGui.QTableWidget.__init__(self, *args, **kwargs)
        self.horizonatal_header_labels = ['NAME', 'OFFSET', 'FORMULA', 'FRAME ID', 'BYTES SIZE', 'UNITS', 'READING', 'RAW', 'DELETE']
        self.setColumnCount(len(self.horizonatal_header_labels))
        self.setHorizontalHeaderLabels(self.horizonatal_header_labels)
        self.__editable_fields = (
            ('BYTES SIZE', ByteSizeTableItem),
            ('OFFSET', OffsetTableItem),
            ('FORMULA', FormulaTableItem),
            ('FRAME ID', FrameIdTableItem),
            ('NAME', NameTableItem),
            ('UNITS', NameTableItem)
        )


    def column_index(self, column_string):
        return self.horizonatal_header_labels.index(column_string)

    def delete_value_slot(self, button_id):
        del_button_col_index = self.column_index('DELETE')
        for row in xrange(self.rowCount()):
            del_button = self.cellWidget(row, del_button_col_index)
            if del_button == button_id:
                self.removeRow(row)
                self.remove_value_signal.emit(self.item(row, self.column_index('NAME')))
                break

    def create_delete_row_button(self):
        delete_button = PushButton('delete')
        delete_button.clicked_s.connect(self.delete_value_slot)
        return delete_button

    def add_row(self):
        self.setRowCount(self.rowCount() + 1)
        current_row = self.rowCount() - 1
        delete_button = self.create_delete_row_button()
        for column, cls in self.__editable_fields:
            self.setItem(current_row, self.column_index(column), cls())

        del_index = self.column_index('DELETE')
        self.setCellWidget(current_row, del_index, delete_button)

        reading_index = self.column_index('READING')
        self.setItem(current_row, reading_index, read_only_table_item())

        raw_index = self.column_index('RAW')
        self.setItem(current_row, raw_index, read_only_table_item())

    def __put_validable_field(self, column, ValidableItemClass, row):
        item = ValidableItemClass(self.item(row, self.column_index(column)))
        item.validate()
        self.setItem(row, self.column_index(column), item)


    def set_validated_values(self, row):
        for column, cls in self.__editable_fields:
            self.__put_validable_field(column, cls, row)


class ValuesEditor(QtGui.QWidget):
    """
    Creates decoding info for values received in digiframes.
    display_value: will convert raw value according to formula and display in READING column
    """
    apply_button_singnal = pyqtSignal()
    cell_button_clicked = pyqtSignal(object)

    def __init__(self):
        QtGui.QWidget.__init__(self)

        self.valuesEditorLayout = QtGui.QGridLayout(self)

        self.table = Table()
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

    def read_status_file(self):
        try:
            values = json.load(open(self.__values_file_path), object_pairs_hook=OrderedDict)
        except (IOError, ValueError):
            values = dict()
        self.values = {}
        row = 0
        for value_name in values:
            self.table.add_row()
            self.table.setItem(row, self.table.column_index('NAME'), valid_table_item(value_name))
            value_dict = {}
            for column in values[value_name]:
                cell_value = values[value_name][column]
                value_dict[column] = values[value_name][column]
                column = class_attr_to_colname(column)
                self.table.setItem(row, self.table.column_index(column), valid_table_item(cell_value))
            value = ValueTableRow(name=value_name, delete_button=self.table.create_delete_row_button(), **value_dict)
            self.table.set_validated_values(row)
            self.values[value_name] = value
            row += 1
        self.__update_values()

    def dump_values_to_file(self):
        json_friendly_values = {}
        for v in sorted(self.values):
            json_friendly_values[v] = self.values[v].decode_info.to_json()
        with open(self.__values_file_path, 'w') as json_dump:
            json.dump(json_friendly_values, json_dump, indent=4)
            print 'json dumped to', self.__values_file_path

    def __update_values(self):
        self.values = {}
        for row in xrange(self.table.rowCount()):
            value_descriptor = {}
            for column in self.table.horizonatal_header_labels:
                try:
                    item = self.table.item(row, self.table.column_index(column))
                    if item.flags() & Qt.Qt.ItemIsEditable:
                        value_descriptor[colname_to_class_attr(column)] = str(item.text())
                except AttributeError as e:
                    print column, e
            try:
                value = ValueTableRow(delete_button=self.table.cellWidget(row, self.table.column_index('DELETE')), **value_descriptor)
                self.table.set_validated_values(row)
                self.values[value.name] = value
            except TypeError as e:
                print 'ERROR', e.message

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
        values_definition = self.values_editor.values_decoder
        self.values_extractor = {}
        for key in values_definition:
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