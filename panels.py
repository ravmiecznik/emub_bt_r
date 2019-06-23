"""
author: Rafal Miecznik
contact: ravmiecznk@gmail.com
"""
import platform
platform = platform.system()
from PyQt4 import QtCore, QtGui
from dummy_event_handler import DummyEventHandler
from objects_with_help import PushButton, CheckBox, LcdDisplay, LineEdit, ComboBox
from call_tracker import method_call_track
import os
import configparser
from main_logger import debug
from event_handler import to_signal

CONNECT_BTN_HELP = "Connect or Disconnect from EMU_BT"
REFLASH_BTN_HELP = "Upload new firmware to EMU_BT"
DISCOVER_BTN_HELP = "Discover EMU_BT among bluetooth devices and store result"
DBG_CHECKBOX_HELP = "Collect debug information to file"
CONFIG_BTN_HELP = "Update config file"

@method_call_track
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
        self.setLayout(control_frame_FrameGrid)
        self.dbg_checkbox = CheckBox("DBG", tip_msg=DBG_CHECKBOX_HELP)


        control_frame_FrameGrid.addWidget(self.connect_button, 0, 0)
        control_frame_FrameGrid.addWidget(self.reflash_button, 0, 1)
        control_frame_FrameGrid.addWidget(self.discover_button, 1, 0)
        control_frame_FrameGrid.addWidget(self.config_button, 1, 1)
        control_frame_FrameGrid.addWidget(self.dbg_checkbox, 2, 0, 1, 2)

        #connect buttons
        self.connect_button.clicked.connect(event_handler.connect_button_slot)
        self.discover_button.clicked.connect(event_handler.discover_emu_bt_slot)
        self.reflash_button.clicked.connect(event_handler.reflash_button_slot)
        self.config_button.clicked.connect(event_handler.config_button_slot)
        self.event_handler = event_handler
        self.event_handler.add_event(self.set_connected)
        self.event_handler.add_event(self.set_disconnected)

    def set_connected(self):
        self.connect_button.setText("disconnect")
        self.connect_button.set_green_style_sheet()

    def set_disconnected(self):
        self.connect_button.setText("Connect")
        self.connect_button.set_default_style_sheet()




EMULATION_BTN_TIP           = "This is very long test string to check if line wrapping will work to avoid main window expansion and segmantation fault eventually, hope will wokr, bye bye bye bye friends"
STORE_FLASH_BANK_BTN_TIP    = "This button commits selected binary file to permanent memory in currently selected bank"
READ_SRAM_BTN_TIP           = "SRAM: this memory is visible to your ECU. This button will get its content." \
                            "\nBut beware that during read process Emulator is not accessible to ECU" \
                            "\nEmulation will stop"
READ_BANK_BTN_TIP           = "Read and save to file content of currently selected bank, which is stored in internal flash"
AUTO_OPEN_CHECK_BOX_TIP     = "If checked it will automatically open a saved file with new binary image downloaded from BT emulator\n"
OVERWRITE_CHECK_BOX_TIP     = "If checked it will overwrte current file without asking\n"

class EmulationPanel(QtGui.QGroupBox):
    def __init__(self, parent, event_handler=DummyEventHandler()):
        super(EmulationPanel, self).__init__(parent)
        #self.parent = parent
        self.setTitle("Emulation")
        self.event_handler = event_handler
        emulation_frame_FrameGrid = QtGui.QGridLayout()
        emulation_frame_FrameGrid.setSpacing(1)


        self.emulate_button = PushButton("EMULATE", tip_msg=EMULATION_BTN_TIP)
        self.read_sram_button = PushButton("READ SRAM", tip_msg=READ_SRAM_BTN_TIP)
        self.read_bank_button = PushButton("READ BANK", tip_msg=READ_BANK_BTN_TIP)
        self.store_to_flash_button = PushButton("SAVE", tip_msg=STORE_FLASH_BANK_BTN_TIP)
        self.auto_open_checkbox = CheckBox("auto open", tip_msg=AUTO_OPEN_CHECK_BOX_TIP)
        self.overwrite_checkbox = CheckBox("overwrite", tip_msg=OVERWRITE_CHECK_BOX_TIP)

        self.read_sram_button.raise_()
        self.read_bank_button.raise_()
        self.emulate_button.raise_()
        self.store_to_flash_button.raise_()
        self.raise_()

        emulation_frame_FrameGrid.addWidget(self.emulate_button, 0, 0)
        emulation_frame_FrameGrid.addWidget(self.read_bank_button, 1, 0)
        emulation_frame_FrameGrid.addWidget(self.read_sram_button, 1, 1)
        emulation_frame_FrameGrid.addWidget(self.store_to_flash_button, 0, 1)
        emulation_frame_FrameGrid.addWidget(self.auto_open_checkbox, 3, 0, 1, 2)
        emulation_frame_FrameGrid.addWidget(self.overwrite_checkbox, 4, 0, 1, 2)
        self.setLayout(emulation_frame_FrameGrid)

        self.store_to_flash_button.clicked.connect(event_handler.store_to_flash_button_slot)
        self.emulate_button.clicked.connect(event_handler.digidiag_on_slot)


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

    def set_default_style_sheet_for_buttons(self):
        self.bank1pushButton.set_default_style_sheet()
        self.bank2pushButton.set_default_style_sheet()
        self.bank3pushButton.set_default_style_sheet()

    def bank_name_line_edit_slot(self):
        bank_name = self.bank_name_line_edit.text()[0:25]
        self.bank_name_line_edit.setText(bank_name)
        self.event_handler.set_bank_name()
        self.bank_name_line_edit.clearFocus()

    # def bank_name_line_edit_return_pressed_slot(self):
    #     self.bank_name_line_edit.clearFocus()


class BinFilePanel(QtGui.QGroupBox):
    def __init__(self, parent, app_status_file, event_handler=DummyEventHandler()):
        super(BinFilePanel, self).__init__(parent)
        frame_grid = QtGui.QGridLayout()
        frame_grid.setSpacing(1)

        self.combo_box = ComboBox(self, tip_msg="???")
        self.browse_btn = PushButton("...", tip_msg="browse for file")
        self.app_status_file = app_status_file

        frame_grid.addWidget(self.combo_box,  0, 0, 1, 6)
        frame_grid.addWidget(self.browse_btn, 0, 7, 1, 1)
        self.setTitle("BIN FILE")
        self.setLayout(frame_grid)

        self.browse_btn.clicked.connect(self.browse_for_file)
        self.combo_box.setDuplicatesEnabled(False)
        self.combo_box.setMaxCount(10)
        self.combo_box.setEditable(True)

        self.last_bin_files_tag = "LAST BIN FILES"
        self.load_last_files()

    def get_current_file(self):
        bin_path = str(self.combo_box.currentText())
        if bin_path:
            return bin_path
        else:
            if self.browse_for_file():
                return self.get_current_file()

    def browse_for_file(self):
        start_dir = os.path.dirname('~/home/')
        file_path = QtGui.QFileDialog.getOpenFileName(self, 'Select bin file',
                                                start_dir, "hex files (*.bin *.BIN)")
        if platform != 'Linux':
            file_path = file_path.replace('/', '\\')
        if os.path.isfile(file_path) and file_path not in self.combo_box.getItems():
            self.combo_box.insertItem(0, file_path)
            self.combo_box.setCurrentIndex(0)
        elif not os.path.isfile(file_path):
            return False

    def __del__(self):
        self.update_app_status_file()

    def load_last_files(self):
        config = configparser.ConfigParser()
        config.read(self.app_status_file)
        try:
            last_files = eval(config[self.last_bin_files_tag]['files'])
            self.combo_box.insertItems(0, last_files)
        except KeyError:
            pass

    def update_app_status_file(self):
        debug("Updating latest files list")
        last_files_list = self.combo_box.getItems()
        config = configparser.ConfigParser()
        config.read(self.app_status_file)
        config[self.last_bin_files_tag] = {'files': last_files_list}
        with open(self.app_status_file, 'w') as cf:
           config.write(cf)

