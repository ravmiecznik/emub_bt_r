"""
author: Rafal Miecznik
contact: ravmiecznk@gmail.com
"""

from PyQt4 import QtCore, QtGui
from PyQt4.QtGui import QFileDialog, QMessageBox
import os
import configparser
from event_handler import EventHandler, to_signal
from setup_emubt import debug, error, warn, info
from call_tracker import method_call_track


def str_fill(string, fill_len=20, chr=' ', right=True):
    fill = fill_len - len(string)
    if fill > 0:
        return string+(fill*chr) if right else (fill*chr)+string
    else:
        return string


#@method_call_track
class ConfigEntry(QtGui.QWidget):
    def __init__(self, parent, option, value, grid, y_pos, qobject):
        QtGui.QWidget.__init__(self)
        self.label = QtGui.QLabel(option, parent=parent)
        self.value = qobject
        grid.addWidget(self.label, y_pos, 0, 1, 2)
        grid.addWidget(self.value, y_pos, 1, 1, 2)

    def get(self):
        return str(self.value.text())


class ConfigSettings:
    def __init__(self):
        self.config_file_path = os.path.join(self.config_path, 'emubt.cnf')
        self.app_status_file = os.path.join(self.config_path, 'app_status.sts')


class Config:
    """
    No Gui Config class
    """
    def __init__(self, config_file):
        self.config = configparser.ConfigParser()
        self.config.read(config_file)
        self.config_file_path = config_file
        self.read_config()

    def read_config(self):
        if 'BLUETOOTH' not in self.config:
            debug("Adding missing BLUETOOTH section to: {}".format(self.config_file_path))
            self.config['BLUETOOTH'] = {
                'bt_device_port': '',
                'bt_device_address': '',
                'rcv_chunk_size': '258',
            }
        if 'EDITORS' not in self.config:
            debug("Adding missing EDITORS section to: {}".format(self.config_file_path))
            self.config['EDITORS'] = {
                'bin_editor': '',
            }
        if 'APPSETTINGS' not in self.config:
            debug("Adding missing APPSETTINGS section to: {}".format(self.config_file_path))
            self.config['APPSETTINGS'] = {
                'allow_read_sram': 'False',
                'response_time': '',
                'tx_packet_size': '{}'.format(256*8)
            }

        return self.config

    def updade_config_file(self, config_section, sub_key, value):
        """
        Updates config file according to config_section entry
        :param config_section:
        :param sub_key:
        :param value:
        :return:
        """
        if config_section not in self.config:
            debug("Adding missing {} section to: {}".format(config_section, self.config_file_path))
            self.config[config_section] = {}
        self.config.set(config_section, sub_key, value)
        try:
            if self.validate():
                with open(self.config_file_path, 'w') as cf:
                    self.config.write(cf)
        except AttributeError:
            with open(self.config_file_path, 'w') as cf:
                self.config.write(cf)

    def update_config_file_BLUETOOTH(self, **kwargs):
        self.config['BLUETOOTH'] = kwargs
        with open(self.config_file_path, 'w') as cf:
            self.config.write(cf)


#@method_call_track
class ConfigWindow(QtGui.QWidget, Config):
    """
    Gui based Config
    """
    def __init__(self, config_file, apply_signal):
        QtGui.QWidget.__init__(self)

        self.setWindowTitle("CONFIG")
        self.x_siz, self.y_siz = 400, 200
        self.mainGrid = QtGui.QGridLayout()
        self.mainGrid.setSpacing(1)
        self.__mainGrid_y_cnt = 0

        Config.__init__(self, config_file)

        self.apply_button = QtGui.QPushButton("APPLY")
        self.cancel_button = QtGui.QPushButton("Cancel")
        self.apply_button.clicked.connect(to_signal(to_signal(self.apply_slot)))
        self.cancel_button.clicked.connect(to_signal(self.close))
        self.mainGrid.addWidget(self.apply_button,   self.__mainGrid_y_cnt, 2, 1, 1)
        self.mainGrid.addWidget(self.cancel_button,  self.__mainGrid_y_cnt, 0, 1, 1)
        self.setLayout(self.mainGrid)
        self.resize(self.x_siz, self.y_siz)
        self.apply_signal = apply_signal


    def close(self):
        QtGui.QWidget.close(self)

    def add_line_edit_entry_to_grid(self, option, value):
        if option in ['tx_packet_size']:
            qobject = self.packetsize_options(value)
        else:
            qobject = QtGui.QLineEdit()
            qobject.setText(value)
        setattr(self, option, ConfigEntry(parent=self, option=option, value=value, grid=self.mainGrid,
                                          y_pos=self.__mainGrid_y_cnt, qobject=qobject))
        self.__mainGrid_y_cnt += 1

    def packetsize_options(self, value):
        qobject = QtGui.QComboBox()
        allowed_values = ['{}'.format(256 * 2**i) for i in xrange(3, -1, -1)]
        if value not in allowed_values:
            value = '{}'.format(256*8)
        qobject.addItems(allowed_values)
        qobject.text = qobject.currentText
        qobject.setCurrentIndex(allowed_values.index(value))
        return qobject

    def read_config(self):
        self.config = Config.read_config(self)
        for config_section in self.config:
            for sub_key in self.config[config_section]:
                self.add_line_edit_entry_to_grid(option=sub_key, value=self.config[config_section][sub_key])

    def apply_slot(self):
        for config_section in self.config:
            for sub_key in self.config[config_section]:
                value = getattr(self, sub_key).get()
                self.config.set(config_section, sub_key, value)
        if self.validate():
            with open(self.config_file_path, 'w') as cf:
                self.config.write(cf)
            self.close()
        self.apply_signal.emit()

    def validate(self):
        bin_editor = self.config['EDITORS']['bin_editor']
        if bin_editor and not os.path.exists(bin_editor):
            msg_box = QMessageBox(self)
            msg_box.setIcon(QMessageBox.Critical)
            msg_box.setText("bin_editor path does not exist: {}.\n"
                            "File will not be updated".format(bin_editor))
            msg_box.setStandardButtons(QMessageBox.Ok)
            msg_box.exec_()
            return False
        return True




if __name__ == "__main__":
    import sys
    app = QtGui.QApplication(sys.argv)
    myapp = ConfigWindow('/home/rafal/EMU_BTR_FILES/emubt.cnf', lambda x:x)
    myapp.show()
    app.exec_()
    # myapp.safe_close()
    sys.exit()
    sys.stdout = STDOUT