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
from PyQt4.QtCore import pyqtSignal
from message_handler import MessageSender
import time

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

    @classmethod
    def from_instance(cls, instance):
        return cls(instance.raw_content)

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
               "bank_num:           {}\n" \
               "name:               {}\n" \
               "enable digidiag:    {}\n" \
               "wear:               {}\n" \
               "override_digidiag:  {}\n" \
               "frames_vector:      {}\n".format(
            raw_hex,
            self.bank_number+1,
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


RED_COLOR = QtGui.QColor(180, 48, 45)
BLUE_COLOR = QtGui.QColor(213, 230, 237)
GREY_COLOR = QtGui.QColor(235, 236, 237)
GREEN_COLOR = QtGui.QColor(33, 215, 137)

CUSTOM_CELL_TOOL_TIP_TEMPLATE = "Frame id: {:02X}\n" \
                                "Value index: {:02X}\n" \
                                "Value: 0x{}\n" \
                                "TWO DIGIT HEX VALUE ONLY !"

class FramesEditorCustomCell(QtGui.QTableWidgetItem):
    def __init__(self, frame_id, index_id):
        QtGui.QTableWidgetItem.__init__(self)
        self.frame_id = frame_id
        self.index_id = index_id
        self.valid = False
        self.setToolTip(self.__repr__())

    def validate(self):
        text = str(self.text())
        text = text.replace('0x', '')
        if text == '?':
            self.setBackgroundColor(GREEN_COLOR)
        else:
            try:
                v = int(text, 16)
                if v > 0xff:
                    raise ValueError("Value exceeds 0xFF")
                if v < 0:
                    raise ValueError("Can't be negative number")
                self.valid = True
                self.setText("{:02X}".format(v)[-2:])
                self.setBackground(BLUE_COLOR)
                self.setToolTip(self.__repr__())
            except ValueError as e:
                self.setBackground(RED_COLOR)
                self.valid = False
                self.setToolTip(e.message)

    def get(self):
        return int(str(self.text()), 16)

    def __repr__(self):
        return CUSTOM_CELL_TOOL_TIP_TEMPLATE.format(self.frame_id, self.index_id, self.text())

class CustomFramesEditor(QtGui.QTableWidget):
    """
    An editable table to customize digifant diagnostic frames.
    """
    remove_value_signal = pyqtSignal(object)
    values_updated_signal = pyqtSignal()
    def __init__(self, init_frames):
        """

        :param init_frames: raw string frames
        """
        self.__cols_num = 8
        self.__rows_num = 5

        QtGui.QTableWidget.__init__(self)
        self.setColumnCount(self.__cols_num)
        self.setRowCount(self.__rows_num)
        self.__set_horizontal_heaer_items()
        self.__set_vertical_heaer_items()
        self.resizeColumnsToContents()

        self.update_values(init_frames)

        self.cellChanged.connect(self.cellChanged_slot)

    def update_values(self, init_frames):
        self.frames = [ord(i) for i in init_frames]
        cnt = 0
        for r in range(self.rowCount()):
            for c in range(self.columnCount()):
                cell = FramesEditorCustomCell(0xff-r, c)
                cell.setText(hex(self.frames[cnt]))
                cell.validate()
                cnt += 1
                self.setItem(r, c, cell)

    def clean_table(self):
        cnt = 0
        for r in range(self.rowCount()):
            for c in range(self.columnCount()):
                cell = FramesEditorCustomCell(0xff-r, c)
                cell.setText('?')
                cell.validate()
                cnt += 1
                self.setItem(r, c, cell)

    def __set_horizontal_heaer_items(self):
        for i in range(self.__cols_num):
            header_item = QtGui.QTableWidgetItem(" {:02X}".format(i))
            header_item.setToolTip("Custom value index {:02X}".format(i))
            self.setHorizontalHeaderItem(i, header_item)

    def __set_vertical_heaer_items(self):
        for i in range(self.__rows_num):
            row_item = QtGui.QTableWidgetItem(" {:02X}".format(0xff-i))
            row_item.setToolTip("Frame id {:02X}".format(0xff-i))
            self.setVerticalHeaderItem(i, row_item)

    def cellChanged_slot(self, p_int, p_int_1):
        self.cellChanged.disconnect()
        cell = self.item(p_int, p_int_1)
        cell.validate()
        self.cellChanged.connect(self.cellChanged_slot)

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

    def get(self):
        raw_frames = ''
        cnt = 0
        for r in range(self.rowCount()):
            for c in range(self.columnCount()):
                cnt += 1
                raw_frames += chr(self.item(r, c).get())
        return raw_frames


class BankPropertyEditor(QtGui.QWidget, object):
    def __init__(self, bank_info, general_signal, message_sender, parent=None):
        """

        :param name: bank name
        """
        QtGui.QWidget.__init__(self)
        self.message_sender = message_sender
        self.general_signal = general_signal
        self.bank_info = BankInfo.from_instance(bank_info)
        # self.bank_num = self.bank_info.bank_number
        self.name = self.bank_info.bank_name
        self.setWindowTitle("Customize: {}".format(self.name))
        self.x_siz, self.y_siz = 500, 600
        self.resize(self.x_siz, self.y_siz)

        self.info_label = QLabel("\nCustomize settings for selected bank.\nIt works only for Digifant1 programs")
        self.info_label.setStyleSheet("font: Courier New")

        self.label = QLabel("Bank name:\n{}".format(self.name))
        self.label.setStyleSheet("font: 20pt Courier New; font-weight: bold")

        self.enable_digidiag_check_box = CheckBox("enable digidiag",
                                                  tip_msg="Enable Digifant diagnostic feedback for bank \"{}\"".format(self.name))


        self.override_digidiag_frames_check_box = CheckBox("override frames",
                                                           tip_msg="If selected it will override default digidiag frames with\n"
                                                          "values in Custom Digi Frames")


        self.custom_frames_label = QLabel("\nCustom Digi Frames")
        self.custom_frames_label.setStyleSheet("font: 10pt Courier New; font-weight: bold")

        self.custom_frames_table = CustomFramesEditor(self.bank_info.frames_vector)

        self.apply_button = PushButton("Apply", tip_msg="Apply changes")
        self.cancel_button = PushButton("Cancel", tip_msg="Discard changes")

        self.info_box = QLabel(" ")

        self.apply_button.clicked.connect(self.apply_button_slot)
        self.cancel_button.clicked.connect(self.display_values)

        #GRID
        mainGrid = QtGui.QGridLayout()
        mainGrid.setSpacing(10)
        mainGrid.addWidget(self.info_label, 0, 0, 2, 3)
        mainGrid.addWidget(self.label, 2, 0, 1, 3)
        mainGrid.addWidget(self.enable_digidiag_check_box, 3, 0)
        mainGrid.addWidget(self.override_digidiag_frames_check_box, 3, 1)
        mainGrid.addWidget(self.custom_frames_label, 4, 0, 1, 3)
        mainGrid.addWidget(self.custom_frames_table, 5, 0, 1, 3)
        mainGrid.addWidget(self.cancel_button, 6, 0)
        mainGrid.addWidget(self.apply_button, 6, 1)
        mainGrid.addWidget(self.info_box, 7, 0, 2, 3)
        self.setLayout(mainGrid)

        #place window next to parent
        if parent:
            x_offset = 0
            y_offset = 100
            current_position_and_size = WindowGeometry(parent)
            x_pos = current_position_and_size.get_position_to_the_right()
            self.setGeometry(x_pos + x_offset, current_position_and_size.pos_y + y_offset, self.x_siz, self.y_siz)

        #self.show()

    @property
    def bank_info(self):
        return self.__bank_info

    @bank_info.setter
    def bank_info(self, bank_info):
        self.__bank_info = BankInfo.from_instance(bank_info)
        self.bank_num = self.bank_info.bank_number

    def update(self, bank_info):
        self.bank_info = BankInfo.from_instance(bank_info)
        self.name = self.bank_info.bank_name
        self.display_values()
        self.label.setText("Bank name:\n{}".format(self.bank_info.bank_name))
        self.info_box.setText("Values refreshed")
        self.setWindowTitle("Customize: {}".format(self.name))
        self.enable_digidiag_check_box.update_tip_msg("Enable Digifant diagnostic feedback for bank \"{}\"".format(self.name))

    def display_values(self):
        if self.bank_info.enable_digidiag:
            self.enable_digidiag_check_box.setChecked(True)
        else:
            self.enable_digidiag_check_box.setChecked(False)

        if self.bank_info.override_digidiag:
            self.override_digidiag_frames_check_box.setChecked(True)
        else:
            self.override_digidiag_frames_check_box.setChecked(False)

        self.custom_frames_table.update_values(self.bank_info.frames_vector)

    def clean_values(self):
        self.custom_frames_table.clean_table()
        self.enable_digidiag_check_box.setChecked(False)
        self.override_digidiag_frames_check_box.setChecked(False)

    def apply_button_slot(self):
        try:
            self.bank_info.enable_digidiag = self.enable_digidiag_check_box.isChecked()
            self.bank_info.override_digidiag = self.override_digidiag_frames_check_box.isChecked()
            raw_frames = self.custom_frames_table.get()
            self.bank_info.frames_vector = raw_frames
            self.info_box.setText('')
            self.clean_values()
            m_send_thread = self.message_sender(message_id=MessageSender.ID.rxflush, timeout=0.5, re_tx=0)
            self.info_box.setText("Updating data...")
            while m_send_thread.isRunning():
                time.sleep(0.01)
            m_send_thread = self.message_sender(message_id=MessageSender.ID.update_bank_data, body=self.bank_info.raw_content,
                                timeout=0.5, re_tx=0)
            self.info_box.setText("Waiting for ack...")
            while m_send_thread.isRunning():
                time.sleep(0.01)
            self.message_sender(message_id=MessageSender.ID.get_banks_info, timeout=1, re_tx=3)

        except Exception as e:
            self.info_box.setText(e.message)


class BanksHandler():
    #TODO: move banks related stuff here
    def __init__(self, parent, general_signal, message_sender, event_handler):
        self.parent = parent
        self.message_sender = message_sender
        self.bank_info_update_signal = general_signal
        self.banks_panel = BanksPanel(parent, event_handler=event_handler)
        self.banks_info = 3*[BankInfo]
        self.editor = BankPropertyEditor(BankInfo(), self.bank_info_update_signal, self.message_sender, self.parent)
        self.banks_panel.bank1_settings_btn.clicked.connect(self.update_bank_editor_b1)
        self.banks_panel.bank2_settings_btn.clicked.connect(self.update_bank_editor_b2)
        self.banks_panel.bank3_settings_btn.clicked.connect(self.update_bank_editor_b3)


    def update_bank_editor_b1(self):
        #self.editor.hide()
        self.editor.update(self.banks_info[0])
        self.editor.show()

    def update_bank_editor_b2(self):
        #self.editor.hide()
        self.editor.update(self.banks_info[1])
        self.editor.show()

    def update_bank_editor_b3(self):
        #self.editor.hide()
        self.editor.update(self.banks_info[2])
        self.editor.show()

    def update_bank_info(self, msg):
        if msg.len == BankInfo.bank_info_size:
            raw_data = msg.msg
            binfo = BankInfo(raw_data)
            bank_num = binfo.bank_number
            self.banks_info[bank_num] = binfo
            self.banks_panel.update_tip_msg_for_bank(bank_num, binfo.get_tip_msg())
            try:
                if self.editor.bank_num == bank_num and self.editor.isVisible():
                    self.editor.update(binfo)
            except AttributeError:
                pass


if __name__ == "__main__":
    s = "rafal miecznik"
    print insert_to_string(s, "nic", 20)

