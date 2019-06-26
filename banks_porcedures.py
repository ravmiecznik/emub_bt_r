"""
author: Rafal Miecznik
contact: ravmiecznk@gmail.com
"""

import time
from event_handler import to_signal
from message_handler import Message
from my_gui_thread import GuiThread, thread_this_method

class BanksProcedures():
        """
        Dedicated Class to seperate Banks related procedures
        Must be inherited in MainWindow
        """
        @thread_this_method()
        def read_bank_info(self):
            timeout = 1
            t0 = time.time()
            raw_buff = ''
            to_signal(self.disable_objects_for_transmission)()

            def set_fail():
                self.banks_panel.bank_name_line_edit.setText("!!FAIL!!")
                to_signal(self.enable_objects_after_transmission)()

            while '<' not in raw_buff:
                try:
                    raw_buff = self.emulator.raw_buffer.read().split('>')[1]
                except IndexError:
                    set_fail()
                print raw_buff
                time.sleep(0.001)
                if time.time() - t0 > timeout:
                    to_signal(set_fail)()
                    to_signal(self.enable_objects_after_transmission)()
                    return False
            bank_name = raw_buff.split('|')[0]

            def set_text():
                self.banks_panel.bank_name_line_edit.setText(bank_name)

            to_signal(set_text)()
            to_signal(self.enable_objects_after_transmission)()

        def bank_name_line_focus_out_event(self):
            self.enable_objects_after_transmission()
            to_signal(self.get_bank_in_use)()

        def bank_name_line_edit_event(self):
            self.emulation_panel.setDisabled(True)
            self.banks_panel.bank1pushButton.setDisabled(True)
            self.banks_panel.bank2pushButton.setDisabled(True)
            self.banks_panel.bank3pushButton.setDisabled(True)
            self.control_panel.reflash_button.setDisabled(True)

        def set_green_style_get_bank_info(self, bank_button):
            def wrapper():
                to_signal(bank_button.set_green_style_sheet)()
                self.emulator.raw_buffer.flush()
                Message(id=Message.ID.get_bank_info, positive_signal=to_signal(self.read_bank_info.start))

            return GuiThread(wrapper).start

        def bank1set_slot(self):
            self.banks_panel.set_default_style_sheet_for_buttons()
            Message('bank1set',
                    positive_signal=to_signal(self.set_green_style_get_bank_info(self.banks_panel.bank1pushButton)),
                    negative_signal=to_signal(self.banks_panel.set_default_style_sheet_for_buttons))

        def bank2set_slot(self):
            self.banks_panel.set_default_style_sheet_for_buttons()
            Message('bank2set',
                    positive_signal=to_signal(self.set_green_style_get_bank_info(self.banks_panel.bank2pushButton)),
                    negative_signal=to_signal(self.banks_panel.set_default_style_sheet_for_buttons))

        def bank3set_slot(self):
            self.banks_panel.set_default_style_sheet_for_buttons()
            Message('bank3set',
                    positive_signal=to_signal(self.set_green_style_get_bank_info(self.banks_panel.bank3pushButton)),
                    negative_signal=to_signal(self.banks_panel.set_default_style_sheet_for_buttons))

        def get_bank_in_use(self):
            Message('bankinuse', positive_signal=to_signal(self.read_bank_in_use))

        def read_bank_in_use(self):
            raw_buffer = self.emulator.raw_buffer.read()
            to_signal(self.banks_panel.set_default_style_sheet_for_buttons)()
            print raw_buffer
            if 'bank1set' in raw_buffer:
                to_signal(self.set_green_style_get_bank_info(self.banks_panel.bank1pushButton))()
            elif 'bank2set' in raw_buffer:
                to_signal(self.set_green_style_get_bank_info(self.banks_panel.bank2pushButton))()
            elif 'bank3set' in raw_buffer:
                to_signal(self.set_green_style_get_bank_info(self.banks_panel.bank3pushButton))()

        def set_bank_name(self):
            new_bank_name = str(self.banks_panel.bank_name_line_edit.text())
            to_signal(self.disable_objects_for_transmission)

            def enable_objects_after_transmission_update_banks_status():
                self.enable_objects_after_transmission
                to_signal(self.get_bank_in_use)()

            Message(new_bank_name, id=Message.ID.setbankname,
                    positive_signal=to_signal(enable_objects_after_transmission_update_banks_status),
                    negative_signal=to_signal(self.enable_objects_after_transmission))
