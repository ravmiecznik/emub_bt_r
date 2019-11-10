"""
author: Rafal Miecznik
contact: ravmiecznk@gmail.com
"""
from PyQt4 import QtCore, QtGui, Qt
from PyQt4.QtCore import QEvent, pyqtSignal
from objects_with_help import PushButton, HelpTip
from pyqtgraph import PlotWidget, ScatterPlotItem, mkPen
from pyqtgraph import setConfigOptions as graphSetOptions
import traceback, os, json

import traceback
from setup_emubt import EMU_BT_PATH, LOG_PATH

LOOKUP_TABLES_PATH = os.path.join(EMU_BT_PATH, 'LOOKUP_TABLES')

RED_COLOR = QtGui.QColor(180, 48, 45)
BLUE_COLOR = QtGui.QColor(213, 230, 237)

TOOL_TIP_STYLE_SHEET = """
        QToolTip {
         background-color: rgba(140, 208, 211, 150);
        }
        """
BACKGROUND = "background-color: rgb({r},{g},{b})"
RED_STYLE_SHEET = BACKGROUND.format(r=180, g=48, b=45)
RED_BACKGROUND_PUSHBUTTON = "QPushButton {}".format("{" + RED_STYLE_SHEET + ";}") + TOOL_TIP_STYLE_SHEET


class IntTableWidgetItem(QtGui.QTableWidgetItem):
    def __init__(self, *args, **kwargs):
        QtGui.QTableWidgetItem.__init__(self, *args, **kwargs)
        str_value = str(self.text())
        self.value = None
        try:
            self.value = int(str_value)
            self.setBackgroundColor(BLUE_COLOR)
            self.setText(str(self.value))
        except ValueError as e:
            try:
                self.value = int(str_value, 16)
                #self.setText(str(self.value))
                self.setText(str(self.value))
                self.setBackgroundColor(BLUE_COLOR)
            except ValueError as e:
                traceback.print_exc()

    def get(self):
        return self.value

    def __repr__(self):
        return "{} {}".format(FloatTableWidgetItem, self.text())

class FloatTableWidgetItem(QtGui.QTableWidgetItem):
    def __init__(self, *args, **kwargs):
        QtGui.QTableWidgetItem.__init__(self, *args, **kwargs)
        str_value = str(self.text())
        self.value = None
        try:
            self.value = float(str_value)
            self.setBackgroundColor(BLUE_COLOR)
            #self.setData(Qt.Qt.EditRole, self.value)
        except ValueError as e:
            try:
                self.value = float(str_value)
                #self.setData(Qt.Qt.EditRole, self.value)
                self.setBackgroundColor(BLUE_COLOR)
            except ValueError as e:
                traceback.print_exc()

    def get(self):
        return self.value

    def __repr__(self):
        return "{} {}".format(FloatTableWidgetItem, self.text())

class LookupTable(QtGui.QTableWidget):
    """
    Main Values Table.
    Stores values decode info.
    """
    remove_value_signal = pyqtSignal(object)
    values_updated_signal = pyqtSignal()
    def __init__(self, init_vals={}, *args, **kwargs):
        QtGui.QTableWidget.__init__(self, *args, **kwargs)
        self.horizonatal_header_labels = ['INPUT', 'OUTPUT', 'DEL']
        self.setColumnCount(len(self.horizonatal_header_labels))
        self.setHorizontalHeaderLabels(self.horizonatal_header_labels)
        self.setColumnWidth(self.column_index('DEL'), 35)
        self.lookup_table = init_vals
        self.update_view()
        self.itemChanged.connect(self.item_changed_slot)

    def get_table(self):
        return self.lookup_table

    def validate_fields_slot(self):
        self.lookup_table = {}
        inp, out = None, None
        try:
            print
            for row in xrange(self.rowCount()):
                inp, out = self.item(row, self.column_index('INPUT')).get(), self.item(row, self.column_index('OUTPUT')).get()
                if inp is not None:
                    self.lookup_table[inp] = out
            if None not in [inp, out]:
                self.add_row()
                self.update_view()
        except AttributeError:
            pass
        self.values_updated_signal.emit()

    def update_view(self):
        self.setRowCount(0)
        for row, v in enumerate(sorted(self.lookup_table.keys())):
            self.add_row()
            self.setItem(row, self.column_index('INPUT'), IntTableWidgetItem(str(v)))

            self.setItem(row, self.column_index('OUTPUT'), FloatTableWidgetItem(str(self.lookup_table[v])))
        self.add_row()


    def remove_lookup_table_item(self, row):
        item = self.item(row, self.column_index('INPUT'))
        if item:
            value = item.get()
            if value in self.lookup_table:
                self.lookup_table.__delitem__(value)

    def delete_value_slot(self, button_id):
        del_button_col_index = self.column_index('DEL')
        is_empty_row = False
        for row in xrange(self.rowCount()):
            del_button = self.cellWidget(row, del_button_col_index)
            if del_button == button_id:
                self.remove_lookup_table_item(row)
                self.removeRow(row)
                break
        self.values_updated_signal.emit()

        #check if there is empty row, add empty row if there is no empty row
        for row in xrange(self.rowCount()):
            is_empty_row = is_empty_row or (self.item(row, self.column_index('INPUT')) is None and self.item(row, self.column_index('OUTPUT')) is None)
        print self.rowCount()

        if self.rowCount() == 0 or not is_empty_row:
            self.add_row()


    def item_changed_slot(self, item):
        self.itemChanged.disconnect()
        for row in xrange(self.rowCount()):
            for col in [self.column_index('INPUT'), self.column_index('OUTPUT')]:
                if item == self.item(row, col):
                    if col == self.column_index('INPUT'):
                        new_item = IntTableWidgetItem(item.text())
                    else:
                        new_item = FloatTableWidgetItem(item.text())
                    self.setItem(row, col, new_item)
                    break
        self.validate_fields_slot()
        self.itemChanged.connect(self.item_changed_slot)
        self.setFocus()
        self.setCurrentCell(self.rowCount()-1, 0)

    def create_delete_row_button(self):
        delete_button = PushButton('X')
        delete_button.clicked_s.connect(self.delete_value_slot)
        delete_button.setStyleSheet(RED_BACKGROUND_PUSHBUTTON)
        return delete_button

    def column_index(self, column_string):
        return self.horizonatal_header_labels.index(column_string)

    def add_row(self):
        self.setRowCount(self.rowCount() + 1)
        current_row = self.rowCount() - 1
        delete_button = self.create_delete_row_button()

        del_index = self.column_index('DEL')
        self.setCellWidget(current_row, del_index, delete_button)


class LookupTableWithGraph(QtGui.QWidget):
    def __init__(self, name='LOOKPUP TABLE', init_table={}):
        QtGui.QWidget.__init__(self)
        self.gridLayout = QtGui.QGridLayout(self)
        self.name = name

        #table
        self.table = LookupTable(init_table)
        #self.table.add_row()
        self.table.values_updated_signal.connect(self.values_updated_slot)

        #graph
        graphSetOptions(antialias=True)
        self.graph = PlotWidget()
        self.graph.setTitle(self.name)
        self.graph.setLabel('left', 'OUTPUT')
        self.graph.setLabel('bottom', 'INPUT')
        self.graph.showGrid(x=True, y=True)
        self.graph.setBackground((235, 236, 237))
        self.pen = mkPen(color=(46, 142, 226), width=3, style=QtCore.Qt.DashLine)

        self.gridLayout.addWidget(self.table, 0, 0)
        self.gridLayout.addWidget(self.graph, 0, 1)
        self.values_updated_slot()


    def values_updated_slot(self):
        x_vect = []
        y_vect = []
        y_max = 0
        y_min = 0
        x_max = 0
        for x_val in self.table.lookup_table:
            y_val = self.table.lookup_table[x_val]
            x_vect.append(x_val)
            y_vect.append(y_val)
            if y_val > y_max:
                y_max = y_val
            if y_val < y_min:
                y_min = y_val
            if x_val > x_max:
                x_max = x_val
        self.graph.clear()
        self.graph.setYRange(y_min - float(y_min)/10, y_max + float(y_max)/10)
        self.graph.setXRange(0, x_max + float(x_max)/10)
        self.graph.plot(x_vect, y_vect, symbol='o', pen=self.pen)

    def get_table(self):
        return self.table.get_table()


class LookupTableEditor(QtGui.QWidget):
    def __init__(self, name='LOOKUP_TABLE'):

        QtGui.QWidget.__init__(self)
        x_siz, y_siz = 1000, 600


        self.gridLayout = QtGui.QGridLayout(self)
        self.horizontalLayout = QtGui.QHBoxLayout()

        self.tab_widget = QtGui.QTabWidget(self)

        self.add_table_btn = PushButton('ADD NEW', tip_msg="Add new lookup table")
        self.add_table_btn.clicked.connect(self.add_new_table)
        self.apply_btn = PushButton('APPLY', tip_msg="dumps table to file")
        self.apply_btn.clicked.connect(self.dump)

        self.name = name
        self.dump_name = self.name + '.lkt'
        self.dump_path = os.path.join(LOOKUP_TABLES_PATH, self.dump_name)
        init_table = self.load_table()
        self.lookup_tables = {name: LookupTableWithGraph(name, init_table)}
        lookup_table = self.lookup_tables.get(self.lookup_tables.keys()[0])

        self.tab_widget.addTab(lookup_table, self.name)
        self.horizontalLayout.addWidget(self.add_table_btn)
        self.horizontalLayout.addWidget(self.apply_btn)
        #self.horizontalLayout.addWidget(self.button2)
        #self.horizontalLayout.addWidget(self.button3)

        self.gridLayout.addLayout(self.horizontalLayout, 0, 0, 1, 1)
        self.gridLayout.addWidget(self.tab_widget, 1, 0, 4, 4)

        self.resize(x_siz, y_siz)
        self.show()

    def add_new_table(self):
        name = "LOOKUP_TABLE"
        while name in self.lookup_tables:
            name = name.split('_')
            name[-1] = str(int(name[-1]) + 1) if name[-1].isdigit() else name[-1]+'_0'
            name = '_'.join(name)
        print name
        self.lookup_tables[name] = LookupTableWithGraph(name)
        self.tab_widget.addTab(self.lookup_tables[name], name)


    def load_table(self):
        try:
            table = {}
            json_table = json.load(open(self.dump_path))
            for key in json_table:
                table[int(key)] = json_table[key]
            return table
        except (IOError, ValueError) as e:
            print e.message
            return {}

    def dump(self):
        try:
            dir_path = os.path.dirname(self.dump_path)
            os.makedirs(dir_path)
        except OSError:
            pass
        table = self.lookup_table.get_table()
        with open(self.dump_path, 'w') as dump_f:
            json.dump(table, dump_f, indent=4, sort_keys=True)


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
            self.widget = LookupTableEditor()
            self.widget.resize(1000, 500)
            self.widget.show()
            self.resize(400, 400)
            self.show()

        def tip(self, *args):
            print args

    app = QtGui.QApplication(sys.argv)
    myapp = MainW()
    myapp.setWindowIcon(QtGui.QIcon('icon.png'))

    myapp.show()
    app.exec_()
    sys.exit()
    sys.stdout = _stdout
    sys.stderr = _stderr