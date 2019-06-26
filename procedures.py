"""
author: Rafal Miecznik
contact: ravmiecznk@gmail.com
"""

import time
import struct
from event_handler import to_signal
from message_handler import Message
from my_gui_thread import GuiThread, thread_this_method
from bin_handler import BinSender, BinSenderFileNotPresent, BinSenderInvalidBinSize

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


class StoreToFlashProcedure():

    def store_to_flash_button_slot(self):
        self.t0 = time.time()
        bin_path = self.bin_file_panel.get_current_file()
        if bin_path:
            try:
                self.bin_sender = BinSender(bin_path)
                #self._tmp_file = open(os.path.join(EMU_BT_PATH, 'tmp.bin'), 'wb')
                Message('rxflush', positive_signal=to_signal(self.send_data_packet.start),
                        negative_signal=self.console_msg_factory("rxflush failed"))
            except IOError as e:
                self.gui_communication_signal.emit("{}: {}".format(e.strerror, e.filename))
                raise e
            except BinSenderInvalidBinSize as e:
                self.gui_communication_signal.emit('{} {}'.format(e.__class__, e.message))
                raise e

    @thread_this_method()
    def send_data_packet(self):
        if not self.blink_save_btn.isRunning():
            self.blink_save_btn.start()
            self.progress_bar.set_title("sending...")
            to_signal(self.progress_bar.display)()
        to_signal(self.disable_objects_for_transmission)()
        try:
            next_packet = next(self.bin_sender)
        except StopIteration:
            self.get_writing_stats.start()
            return
        Message(struct.pack('H', self.bin_sender.packets_get - 1) + next_packet, id=Message.ID.write_to_page,
                positive_signal=to_signal(self.send_data_packet_on_ack), negative_signal=to_signal(self.send_data_packet_teardown_on_fail),
                extra_action_on_ack=to_signal(self.set_blue_status_for_progress_bar),
                extra_action_on_nack=to_signal(self.set_red_status_for_progress_bar)
                )

    def set_blue_status_for_progress_bar(self):
        self.progress_bar.set_blue_style()

    def set_red_status_for_progress_bar(self):
        self.progress_bar.set_red_style()

    def send_data_packet_on_ack(self):
        try:
            progress = 100*self.bin_sender.packets_get/self.bin_sender.tot_packests
        except ZeroDivisionError:
            progress = 0
        to_signal(self.console.console_text_browser.clear)()
        self.gui_communication_signal.emit("\n\nUpdating: {}%".format(progress))
        self.progress_bar.setValue(progress)
        self.send_data_packet.start()

    def send_data_packet_teardown_on_fail(self):
        self.blink_save_btn.kill()
        self.gui_communication_signal.emit("SAVE operation failed. Check error log")
        to_signal(self.enable_objects_after_transmission)()
        self.progress_bar.hide()

    @thread_this_method()
    def get_writing_stats(self):
        to_signal(self.enable_objects_after_transmission)()
        self.blink_save_btn.kill()
        self.gui_communication_signal.emit("DONE in time {}".format(time.time() - self.t0))
        Message("writingtime")
        self.progress_bar.hide()



