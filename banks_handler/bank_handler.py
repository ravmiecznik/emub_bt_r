#!/usr/bin/python
"""
author: Rafal Miecznik
contact: ravmiecznk@gmail.com
created: 01.03.2020$
"""

from auxiliary_module import raw_to_uint, raw_str_to_hex, uint_to_raw, uint8_to_raw, uint16_to_raw
from  auxiliary_module import WindowGeometry
from panels import BanksPanel
from objects_with_help import CheckBox, PushButton
from event_handler import EventHandler
from PyQt4 import QtCore, QtGui
from PyQt4.QtGui import QLabel, QLCDNumber, QHeaderView
from PyQt4.QtCore import QEvent, pyqtSignal
from PyQt4 import Qt

def insert_to_string(string, substring, index=0):
    l = len(substring)
    string = string[0:index] + substring + string[index+l:]
    return string


class BankInfo(object):
    """
    Handles and formats banks related information data
    #define bank_name_len	26
    struct bank_info{
        uint8_t bank_num
        char name[bank_name_len];
        uint8_t enable_digidiag;
        uint16_t wear;
        uint8_t override_digi_frames;
        uint8_t frames_vectors[8*5];
    };
    """
    #sizes
    bank_num_size = 1
    bank_name_size = 26
    enable_digidiag_size = 1
    wear_size = 2
    override_digidiag_size = 1
    frames_vectors_size = 8*5
    bank_info_size = bank_num_size + bank_name_size + enable_digidiag_size + wear_size + override_digidiag_size + frames_vectors_size

    #positions
    bank_number_pos = 0
    bank_name_pos = bank_number_pos + bank_num_size
    enable_digidiag_pos = bank_name_pos + bank_name_size
    wear_pos = enable_digidiag_pos + enable_digidiag_size
    override_digidiag_pos = wear_pos + wear_size
    frames_vector_pos = override_digidiag_pos + override_digidiag_size

    def __init__(self, bank_info_raw=None):
        if bank_info_raw is None:
            self.raw_content = self.bank_info_size*'\x00'
            self.bank_name = "NOT AVAILABLE"
        else:
            self.raw_content = bank_info_raw

    # -------------------------------------------------------------------------------------------------------------------
    @property
    def bank_number(self):
        bank_number = self.raw_content[self.bank_number_pos]
        return raw_to_uint(bank_number)

    @bank_number.setter
    def bank_number(self, number):
        self.raw_content = insert_to_string(self.raw_content, uint8_to_raw(number), self.bank_number_pos)


    #-------------------------------------------------------------------------------------------------------------------
    @property
    def bank_name(self):
        _bank_raw = self.raw_content[self.bank_name_pos:]
        bank_name = _bank_raw[0:_bank_raw.find('\x00')]
        return bank_name

    @bank_name.setter
    def bank_name(self, new_name):
        new_name = new_name[0:self.bank_name_size]
        self.raw_content = insert_to_string(self.raw_content, new_name, self.bank_name_pos)

    # -------------------------------------------------------------------------------------------------------------------
    @property
    def enable_digidiag(self):
        enable_digidiag = self.raw_content[self.enable_digidiag_pos]
        return raw_to_uint(enable_digidiag)

    @enable_digidiag.setter
    def enable_digidiag(self, enable):
        enable = 1 if enable else 0
        self.raw_content = insert_to_string(self.raw_content, uint8_to_raw(enable), self.enable_digidiag_pos)

    # -------------------------------------------------------------------------------------------------------------------
    @property
    def wear(self):
        wear = self.raw_content[self.wear_pos: self.wear_pos + self.wear_size]
        return raw_to_uint(wear)

    @wear.setter
    def wear(self, val):
        self.raw_content = insert_to_string(self.raw_content, uint16_to_raw(val), self.wear_pos)

    # -------------------------------------------------------------------------------------------------------------------
    @property
    def override_digidiag(self):
        override_digidiag = self.raw_content[self.override_digidiag_pos: self.override_digidiag_pos + self.override_digidiag_size]
        return raw_to_uint(override_digidiag)

    @override_digidiag.setter
    def override_digidiag(self, override_flag):
        override_flag = 1 if override_flag else 0
        self.raw_content = insert_to_string(self.raw_content, uint8_to_raw(override_flag), self.override_digidiag_pos)

    # -------------------------------------------------------------------------------------------------------------------
    @property
    def frames_vector(self):
        return self.raw_content[self.frames_vector_pos:self.frames_vector_pos + self.frames_vectors_size]

    @frames_vector.setter
    def frames_vector(self, new_frames):
        if type(new_frames) is not str:
            raise Exception("String type expected")
        self.raw_content = insert_to_string(self.raw_content, new_frames, self.frames_vector_pos)


    def __str__(self):
        raw_hex = raw_str_to_hex(self.raw_content)
        enable_digidiag = self.enable_digidiag
        wear = self.wear
        override_digidag = self.override_digidiag
        frames_vector = raw_str_to_hex(self.frames_vector)
        return "raw:                {}\n" \
               "name:               {}\n" \
               "enable digidiag:    {}\n" \
               "wear:               {}\n" \
               "override_digidiag:  {}\n" \
               "frames_vector:      {}\n".format(
            raw_hex,
            self.bank_name,
            enable_digidiag,
            wear,
            override_digidag,
            frames_vector
        )

    def get_tip_msg(self):
        """
        :return: Formatted string for a button tip message for bank buttons
        """
        enable_digidiag = "ON" if self.enable_digidiag else "OFF"
        wear = self.wear
        override_digidag = "ON" if self.override_digidiag else "OFF"

        frames_vector = ''
        for i, c in enumerate(self.frames_vector):
            if not i % 8:
                frames_vector += '\n    '
            frames_vector += "{:02X} ".format(ord(c))


        return "name: {}\n" \
               "enable digidiag: {}\n" \
               "wear: {}\n" \
               "override_digidiag: {}\n" \
               "frames_vector: {}\n".format(
            self.bank_name,
            enable_digidiag,
            wear,
            override_digidag,
            frames_vector
        )


class CustomFramesEditor(QtGui.QTableWidget):
    #TODO: validate each cell on enter press if this is hexadicimal < 0xff
    #TODO: On apply button create BankInfo reversed message and send
    """
    Main Values Table.
    Stores values decode info.
    """
    remove_value_signal = pyqtSignal(object)
    values_updated_signal = pyqtSignal()
    def __init__(self, *args, **kwargs):
        QtGui.QTableWidget.__init__(self, *args, **kwargs)
        self.horizonatal_header_labels = [" {:02X}".format(i) for i in range(8)]
        self.vertical_labels = ["{:02X}".format(0xff-i) for i in range(6)]
        self.setColumnCount(len(self.horizonatal_header_labels))
        self.setRowCount(len(self.vertical_labels))
        self.setHorizontalHeaderLabels(self.horizonatal_header_labels)
        self.setVerticalHeaderLabels(self.vertical_labels)
        self.resizeColumnsToContents()

    def keyPressEvent(self, QKeyEvent):
        """
        Move to next cell on Return/Enter press
        :param QKeyEvent:
        :return:
        """
        QtGui.QTableWidget.keyPressEvent(self, QKeyEvent)
        if QKeyEvent.key() == Qt.Qt.Key_Return or QKeyEvent.key() == Qt.Qt.Key_Enter:
            self.setCurrentCell(self.currentRow(), (self.currentColumn()+1) % self.columnCount())
            if self.currentColumn() == 0:
                self.setCurrentCell((self.currentRow() + 1) % self.rowCount(), self.currentColumn())


class BankPropertyEditor(QtGui.QWidget):
    def __init__(self, name, parent=None):
        """

        :param name: bank name
        """
        QtGui.QWidget.__init__(self)
        self.setWindowTitle("Customize: {}".format(name))
        self.x_siz, self.y_siz = 400, 500
        self.resize(self.x_siz, self.y_siz)

        self.info_label = QLabel("\nCustomize settings for selected bank.\nIt works only for Digifant1 programs")
        self.info_label.setStyleSheet("font: Courier New")

        self.label = QLabel("Bank name:\n{}".format(name))
        self.label.setStyleSheet("font: 20pt Courier New; font-weight: bold")

        self.enable_digidiag_check_box = CheckBox("enable digidiag",
                                                  tip_msg="Enable Digifant diagnostic feedback for bank \"{}\"".format(name))
        self.override_digidiag_frames = CheckBox("override frames",
                                                  tip_msg="If selected it will override default digidiag frames with\n"
                                                          "values in Custom Digi Frames")

        self.custom_frames_label = QLabel("\nCustom Digi Frames")
        self.custom_frames_label.setStyleSheet("font: 10pt Courier New; font-weight: bold")

        self.custom_frames_table = CustomFramesEditor()

        self.apply_button = PushButton("Apply", tip_msg="Apply changes")
        self.cancel_button = PushButton("Cancel", tip_msg="close without applying changes")

        #GRID
        mainGrid = QtGui.QGridLayout()
        mainGrid.setSpacing(10)
        mainGrid.addWidget(self.info_label, 0, 0, 2, 3)
        mainGrid.addWidget(self.label, 2, 0, 1, 3)
        mainGrid.addWidget(self.enable_digidiag_check_box, 3, 0)
        mainGrid.addWidget(self.override_digidiag_frames, 3, 1)
        mainGrid.addWidget(self.custom_frames_label, 4, 0, 1, 3)
        mainGrid.addWidget(self.custom_frames_table, 5, 0, 1, 3)
        mainGrid.addWidget(self.cancel_button, 6, 0)
        mainGrid.addWidget(self.apply_button, 6, 1)
        self.setLayout(mainGrid)

        #place window next to parent
        if parent:
            x_offset = 0
            y_offset = 100
            current_position_and_size = WindowGeometry(parent)
            x_pos = current_position_and_size.get_position_to_the_right()
            self.setGeometry(x_pos + x_offset, current_position_and_size.pos_y + y_offset, self.x_siz, self.y_siz)

        self.show()


class BanksHandler():
    #TODO: move banks related stuff here
    def __init__(self, parent, event_handler=EventHandler()):
        self.parent = parent
        self.banks_panel = BanksPanel(parent, event_handler=event_handler)
        self.banks_panel.bank1_settings_btn.clicked.connect(self.display_property_editor_b1)
        self.banks_panel.bank2_settings_btn.clicked.connect(self.display_property_editor_b2)
        self.banks_panel.bank3_settings_btn.clicked.connect(self.display_property_editor_b3)
        self.banks_info = [BankInfo(), BankInfo(), BankInfo()]

    def display_property_editor_b1(self):
        self.editor = BankPropertyEditor(self.banks_info[0].bank_name, self.parent)

    def display_property_editor_b2(self):
        self.editor = BankPropertyEditor(self.banks_info[1].bank_name)

    def display_property_editor_b3(self):
        self.editor = BankPropertyEditor(self.banks_info[2].bank_name)

    def update_bank_info(self, raw_data):
        binfo = decode_banks_info(raw_data)
        if binfo:
            bank_num = binfo.bank_number
            self.banks_info[bank_num] = binfo
            self.banks_panel.update_tip_msg_for_bank(bank_num, binfo.get_tip_msg())


def decode_banks_info(msg):
    """

    :param msg:
    :return:
    """
    if msg.len == BankInfo.bank_info_size:
        return BankInfo(msg.msg)


if __name__ == "__main__":
    s = "rafal miecznik"
    print insert_to_string(s, "nic", 20)

