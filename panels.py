"""
author: Rafal Miecznik
contact: ravmiecznk@gmail.com
"""
import platform
platform = platform.system()
from PyQt4 import QtCore, QtGui
from dummy_event_handler import DummyEventHandler
from objects_with_help import PushButton, SmallPushButton, CheckBox, LcdDisplay, LineEdit, ComboBox
from call_tracker import method_call_track
import os
import configparser
from setup_emubt import debug
from event_handler import to_signal
from message_box import message_box


def prepare_file_path_for_platform(fpath):
    if platform != 'Linux':
        if fpath[0] == '/':
            fpath = fpath[1:]
        fpath = fpath.replace('/', '\\')
    return fpath

CONNECT_BTN_HELP = "Connect or Disconnect from EMU_BT"
REFLASH_BTN_HELP = "Upload new firmware to EMU_BT"
DISCOVER_BTN_HELP = "Discover EMU_BT among bluetooth devices and store result"
AUTOCONNECT_CHECKBOX_HELP = "Autoconnect at startup"
CONFIG_BTN_HELP = "Update config file"
CHECK_RESPONSE_TIME_BTN_HELP = "Measure average response time, required to optimize transimission timings. Check " \
                               "Config button to see current value"
SET_PIN_BTN_HELP = "Sets/changes PIN for bluetooth device"

#@method_call_track
class ControlPanel(QtGui.QGroupBox):
    def __init__(self, parent, event_handler=DummyEventHandler()):
        #super(ControlPanel, self).__init__(parent)
        QtGui.QGroupBox.__init__(self, parent)
        self.parent = parent
        self.setTitle("Control")
        control_frame_FrameGrid = QtGui.QGridLayout()
        control_frame_FrameGrid.setSpacing(1)
        self.control_panel_widget = QtGui.QWidget(self)
        self.control_panel_widget.setGeometry(QtCore.QRect(10, 30, 151, 74))
        self.connect_button = PushButton("Connect", tip_msg=CONNECT_BTN_HELP)
        self.reflash_button = PushButton("Reflash", tip_msg=REFLASH_BTN_HELP)
        self.discover_button = PushButton("Discover", tip_msg=DISCOVER_BTN_HELP)
        self.config_button = PushButton("Config", tip_msg=CONFIG_BTN_HELP)
        self.resp_time_button = PushButton("RespTime", tip_msg=CHECK_RESPONSE_TIME_BTN_HELP)
        self.set_pin_button = PushButton("Set PIN", tip_msg=SET_PIN_BTN_HELP)
        self.setLayout(control_frame_FrameGrid)
        self.autoconnect_checkbox = CheckBox("Autoconnect", tip_msg=AUTOCONNECT_CHECKBOX_HELP)


        control_frame_FrameGrid.addWidget(self.connect_button, 0, 0)
        control_frame_FrameGrid.addWidget(self.reflash_button, 0, 1)
        control_frame_FrameGrid.addWidget(self.discover_button, 1, 0)
        control_frame_FrameGrid.addWidget(self.config_button, 1, 1)
        control_frame_FrameGrid.addWidget(self.set_pin_button, 2, 0)
        control_frame_FrameGrid.addWidget(self.resp_time_button, 2, 1)
        control_frame_FrameGrid.addWidget(self.autoconnect_checkbox, 3, 0, 1, 2)

        #connect buttons
        self.connect_button.clicked.connect(event_handler.connect_button_slot)
        self.discover_button.clicked.connect(event_handler.discover_emu_bt_slot)
        self.reflash_button.clicked.connect(event_handler.reflash_button_slot)
        self.config_button.clicked.connect(event_handler.config_button_slot)
        self.resp_time_button.clicked.connect(event_handler.estimate_response_time_slot)
        self.set_pin_button.clicked.connect(event_handler.set_pin_button_slot)
        self.event_handler = event_handler
        self.event_handler.add_event(self.set_connected)
        self.event_handler.add_event(self.set_disconnected)

    def set_connected(self):
        self.connect_button.setText("disconnect")
        self.connect_button.set_green_style_sheet()

    def set_disconnected(self):
        self.connect_button.setText("Connect")
        self.connect_button.set_default_style_sheet()




EMULATION_BTN_TIP           = "Track selected file for changes. If file is modified all changed bytes will be send to EMUBT SRAM memory"
STORE_FLASH_BANK_BTN_TIP    = "This button commits selected binary file to permanent memory in currently selected bank"
READ_SRAM_BTN_TIP           = "SRAM: this memory is visible to your ECU. This button will get its content." \
                            "\nBut beware that during read process Emulator is not accessible to ECU" \
                            "\nEmulation will stop"
READ_BANK_BTN_TIP           = "Read and save to file content of currently selected bank, which is stored in internal flash"
AUTO_OPEN_CHECK_BOX_TIP     = "If checked it will automatically open a saved file with new binary image downloaded from BT emulator\n"
OVERWRITE_CHECK_BOX_TIP     = "If checked it will overwrte current file without asking\n"
RELOAD_SRAM_CHECK_BOX_TIP   = "If checked it will reload FLASH bank to sram\n"

class EmulationPanel(QtGui.QGroupBox):
    def __init__(self, parent, event_handler=DummyEventHandler(), read_sram_allowed=False):
        super(EmulationPanel, self).__init__(parent)
        #self.parent = parent
        self.setTitle("Emulation")
        self.event_handler = event_handler
        emulation_frame_FrameGrid = QtGui.QGridLayout()
        emulation_frame_FrameGrid.setSpacing(0.5)

        self.read_sram_allowed = read_sram_allowed

        if read_sram_allowed == False:
            _PushButton = SmallPushButton
        else:
            _PushButton = PushButton


        self.emulate_button = _PushButton("LIVE", tip_msg=EMULATION_BTN_TIP)
        if self.read_sram_allowed:
            self.read_sram_button = _PushButton("READ SRAM", tip_msg=READ_SRAM_BTN_TIP)
            self.read_sram_button.raise_()
        self.read_bank_button = _PushButton("READ", tip_msg=READ_BANK_BTN_TIP)
        self.save_button = _PushButton("UPLOAD", tip_msg=STORE_FLASH_BANK_BTN_TIP)
        self.auto_open_checkbox = CheckBox("auto open", tip_msg=AUTO_OPEN_CHECK_BOX_TIP)
        self.reload_sram_checkbox = CheckBox("reload sram on save", tip_msg=RELOAD_SRAM_CHECK_BOX_TIP)

        self.read_bank_button.raise_()
        self.emulate_button.raise_()
        self.save_button.raise_()
        self.raise_()

        if read_sram_allowed == True:
            widgets_layout = [
                (self.emulate_button, 0, 0),
                (self.read_bank_button, 1, 0),
                (self.read_sram_button, 1, 1),
                (self.save_button, 0, 1),
                (self.auto_open_checkbox, 3, 0, 1, 2),
                (self.reload_sram_checkbox, 4, 0, 1, 2),
            ]
        else:
            widgets_layout = [
                (self.emulate_button, 0, 0),
                (self.read_bank_button, 0, 1),
                (self.save_button, 0, 2),
                (self.auto_open_checkbox, 2, 0, 1, 2),
                (self.reload_sram_checkbox, 3, 0, 1, 2),
            ]

        for wl in widgets_layout:
            emulation_frame_FrameGrid.addWidget(*wl)

        self.setLayout(emulation_frame_FrameGrid)

        self.save_button.clicked.connect(event_handler.save_button_slot)
        self.emulate_button.clicked.connect(event_handler.emulate_button_slot)
        if self.read_sram_allowed:
            self.read_sram_button.clicked.connect(event_handler.read_sram_button_slot)
        self.read_bank_button.clicked.connect(event_handler.read_bank_button_slot)

    def set_event_handler(self, event_handler):
        self.event_handler = event_handler
        self.save_button.clicked.connect(event_handler.save_button_slot)
        self.emulate_button.clicked.connect(event_handler.emulate_button_slot)
        if self.read_sram_allowed:
            self.read_sram_button.clicked.connect(event_handler.read_sram_button_slot)
        self.read_bank_button.clicked.connect(event_handler.read_bank_button_slot)


LCD_WEAR_DISPLAY_TIP        = "Bank wear counter. Will increase if any of 256bytes page of given bank was rewritten in given bank slot.\n" \
                              "It helps to keep track of how many times flash memory was overwritten.\n" \
                              "There is a check if a given page was modified, if no it is not erased to extend its life.\n" \
                              "To refresh just click 'bank' button."
AUTO_DOWNLOAD_CHECKBOX_TIP  = "Automatic download of selected bank"
BANK_TIP               = "Select bank. If auto download checkbox marked it will download bank autmatically"

class BanksPanel(QtGui.QGroupBox):
    def __init__(self, parent, event_handler=DummyEventHandler()):
        super(BanksPanel, self).__init__(parent)
        frame_grid = QtGui.QGridLayout()
        frame_grid.setSpacing(1)

        self.event_handler = event_handler
        self.bank_name_max_len = 25

        self.setTitle("Banks")
        self.bank1_wear_lcd = LcdDisplay(tip_msg=LCD_WEAR_DISPLAY_TIP)
        self.bank2_wear_lcd = LcdDisplay(tip_msg=LCD_WEAR_DISPLAY_TIP)
        self.bank3_wear_lcd = LcdDisplay(tip_msg=LCD_WEAR_DISPLAY_TIP)

        self.auto_download_checkbox = CheckBox("auto download", tip_msg=AUTO_DOWNLOAD_CHECKBOX_TIP)

        self.bank1pushButton = PushButton("bank 1", tip_msg=BANK_TIP)
        self.bank2pushButton = PushButton("bank 2", tip_msg=BANK_TIP)
        self.bank3pushButton = PushButton("bank 3", tip_msg=BANK_TIP)

        self.bank_name_line_edit = LineEdit(tip_msg="Provide new bank name. ENTER accepts",
                                            focus_event=event_handler.bank_name_line_edit_event,
                                            focus_out_event = event_handler.bank_name_line_focus_out_event)


        frame_grid.addWidget(self.bank1pushButton, 0, 0)
        frame_grid.addWidget(self.bank2pushButton, 1, 0)
        frame_grid.addWidget(self.bank3pushButton, 2, 0)
        frame_grid.addWidget(self.bank1_wear_lcd, 0, 2)
        frame_grid.addWidget(self.bank2_wear_lcd, 1, 2)
        frame_grid.addWidget(self.bank3_wear_lcd, 2, 2)
        frame_grid.addWidget(self.bank_name_line_edit, 3, 0, 1, 3)
        frame_grid.addWidget(self.auto_download_checkbox, 4, 0)
        self.setLayout(frame_grid)

        self.bank1pushButton.clicked.connect(event_handler.bank1set_slot)
        self.bank2pushButton.clicked.connect(event_handler.bank2set_slot)
        self.bank3pushButton.clicked.connect(event_handler.bank3set_slot)

        #self.bank_name_line_edit.editingFinished.connect(self.bank_name_line_edit_slot)
        self.bank_name_line_edit.returnPressed.connect(self.bank_name_line_edit_slot)

    def put_bank_name(self, name):
        self.bank_name_line_edit.setText(name[0:self.bank_name_max_len])

    def get_bank_name_text(self):
        return self.bank_name_line_edit.text()[0:self.bank_name_max_len]


    def set_default_style_sheet_for_buttons(self):
        self.bank1pushButton.set_default_style_sheet()
        self.bank2pushButton.set_default_style_sheet()
        self.bank3pushButton.set_default_style_sheet()

    def bank_name_line_edit_slot(self):
        bank_name = self.bank_name_line_edit.text()[0:self.bank_name_max_len]
        self.bank_name_line_edit.setText(bank_name)
        self.event_handler.set_bank_name()
        self.bank_name_line_edit.clearFocus()

    def disable_active_button(self):
        to_signal(self.bank1pushButton.set_default_style_sheet)()
        to_signal(self.bank2pushButton.set_default_style_sheet)()
        to_signal(self.bank3pushButton.set_default_style_sheet)()


    def set_active_button(self, bank_no):
        to_signal(self.bank1pushButton.set_default_style_sheet)()
        to_signal(self.bank2pushButton.set_default_style_sheet)()
        to_signal(self.bank3pushButton.set_default_style_sheet)()
        set_green_style = \
            [
            self.bank1pushButton.set_green_style_sheet,
            self.bank2pushButton.set_green_style_sheet,
            self.bank3pushButton.set_green_style_sheet,
            ][bank_no]
        to_signal(set_green_style).emit()



class BinFilePanel(QtGui.QGroupBox):
    def __init__(self, parent, app_status_file, event_handler=DummyEventHandler(), max_width=600):
        super(BinFilePanel, self).__init__(parent)
        frame_grid = QtGui.QGridLayout()
        frame_grid.setSpacing(1)

        self.combo_box = ComboBox(self, tip_msg="???")
        self.combo_box.setFixedWidth(max_width)
        #self.combo_box.size

        self.browse_btn = PushButton("...", tip_msg="browse for file")
        self.open_btn = PushButton("open", tip_msg="open file in editor")
        self.app_status_file = app_status_file

        self.last_browse_location = ''

        frame_grid.addWidget(self.combo_box,  0, 0, 1, 6)
        frame_grid.addWidget(self.open_btn,   0, 7, 1, 1)
        frame_grid.addWidget(self.browse_btn, 0, 8, 1, 1)
        self.setTitle("BIN FILE")
        self.setLayout(frame_grid)

        self.browse_btn.clicked.connect(self.browse_for_file)
        self.open_btn.clicked.connect(event_handler.open_bin_file)
        self.combo_box.setDuplicatesEnabled(False)
        self.combo_box.setMaxCount(10)
        self.combo_box.setEditable(True)

        self.event_handler = event_handler
        self.setAcceptDrops(True)
        self.combo_box.dragEnterEvent = self.dragEnterEvent
        self.combo_box.dropEvent = self.dropEvent
        

    def dragEnterEvent(self, event):
        file_path = event.mimeData().urls()[0].path()

        file_path = prepare_file_path_for_platform(file_path)
        if os.path.isfile(file_path):
            event.accept()

    def dropEvent(self, event):
        bin_path = event.mimeData().urls()[0].path()
        bin_path = prepare_file_path_for_platform(bin_path)
        self.insert_new_file(bin_path)

    def get_current_file(self):
        bin_path = str(self.combo_box.currentText())
        if os.path.exists(bin_path):
            self.combo_box.moveOnTop(bin_path)
            return bin_path
        else:
            message_box("no such file: {}\n".format(bin_path))
            self.combo_box.setEditText(self.combo_box.itemText(0))
            self.combo_box.removeByStr(bin_path)

    def browse_for_file(self):
        start_dir = self.last_browse_location
        file_path = QtGui.QFileDialog.getOpenFileName(self, 'Select bin file',
                                                start_dir, "hex files (*.bin *.BIN)")
        if platform != 'Linux':
            file_path = file_path.replace('/', '\\')
        return self.insert_new_file(file_path)

    def insert_new_file(self, file_path):
        if os.path.isfile(file_path) and file_path not in self.combo_box.getItems() and self.check_bin_size(file_path):
            self.combo_box.insertItem(0, file_path)
            self.combo_box.setCurrentIndex(0)
            self.last_browse_location = os.path.dirname(str(file_path))
        elif file_path in self.combo_box.getItems():
            self.combo_box.moveOnTop(file_path)
        elif not os.path.isfile(file_path):
            return False


    def check_bin_size(self, bin_path):
        with open(bin_path, 'rb') as f:
            size = len(f.read())
        if size != 0x8000:
            message_box("This is not valid 27c256 chip image.\nSize not match 0x{:X}!=0x{:X}".format(size, 0x8000))
            return False
        return True


