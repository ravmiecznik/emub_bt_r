# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'untitled.ui'
#
# Created by: PyQt4 UI code generator 4.12.1
#
# WARNING! All changes made in this file will be lost!


from PyQt4 import QtCore, QtGui, Qt
from PyQt4.QtCore import QEvent, pyqtSignal
from objects_with_help import PushButton, HelpTip
import struct
import traceback
from setup_emubt import EMU_BT_PATH, LOG_PATH
from loggers import create_logger
from values_editor import ValuesEditor
from lookup_table import LookupTableEditor



digidiag_logger = create_logger(name="digidiag", log_path=LOG_PATH)

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




class DigidiagWindow(QtGui.QWidget):
    def __init__(self):

        QtGui.QWidget.__init__(self)
        x_siz, y_siz = 700, 600

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

        self.lookup_table_editor = LookupTableEditor()
        self.tabWidget.addTab(self.lookup_table_editor, 'LOOKUP TABLES')

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
            frame_id = values_definition[key].decode_info.frame_id
            self.values_extractor[key] = {
                'FRAME ID': values_definition[key].decode_info.frame_id.get(),
                'OFFSET': values_definition[key].decode_info.offset.get(),
                'BYTES SIZE': values_definition[key].decode_info.bytes_size.get(),
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
                #print e.message
                #traceback.print_exc()
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
    myapp.setWindowIcon(QtGui.QIcon('icon.png'))

    myapp.show()
    app.exec_()
    sys.exit()
    sys.stdout = _stdout
    sys.stderr = _stderr