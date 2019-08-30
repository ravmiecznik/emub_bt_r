"""
author: Rafal Miecznik
contact: ravmiecznk@gmail.com
"""

import time, os
import struct
from event_handler import to_signal
from message_handler import Message
from my_gui_thread import GuiThread, thread_this_method
from setup_emubt import warn, error, info, debug, BIN_PATH
from bin_handler import BinFilePacketGenerator, BinSenderFileNotPresent, BinSenderInvalidBinSize, ReceptionFail, PacketReceptionTimeout, BinReceiver
from message_box import message_box
from bin_tracker import BinTracker
from call_tracker import method_call_track

EEPROM_SIZE = 0x8000
PACKET_SIZE = 256 * 8
PACKETS_NUM = EEPROM_SIZE / PACKET_SIZE

import platform


class RetxCount():
    def __init__(self):
        self.__retx_sum = 0

    def add_retx_sum(self):
        self.__retx_sum += 1

    def retx_sum(self):
        return self.__retx_sum

    def disp_retx_count(self, console):
        """
        gui communication signal must be part of Child class
        :return:
        """
        console("Num of retx {}".format(self.__retx_sum))

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
            to_signal(self.enable_objects_after_transmission())()
            to_signal(self.get_bank_in_use)()

        def bank_name_line_edit_event(self):
            self.emulation_panel.setDisabled(True)
            self.banks_panel.bank1pushButton.setDisabled(True)
            self.banks_panel.bank2pushButton.setDisabled(True)
            self.banks_panel.bank3pushButton.setDisabled(True)
            self.control_panel.reflash_button.setDisabled(True)

        def set_green_style_get_bank_info(self, bank_button):
            self.bank_in_use = ['bank 1', 'bank 2', 'bank 3'].index(bank_button.text()) + 1
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
            if 'bank1set' in raw_buffer:
                self.bank_in_use = 1
                to_signal(self.set_green_style_get_bank_info(self.banks_panel.bank1pushButton))()
            elif 'bank2set' in raw_buffer:
                self.bank_in_use = 2
                to_signal(self.set_green_style_get_bank_info(self.banks_panel.bank2pushButton))()
            elif 'bank3set' in raw_buffer:
                self.bank_in_use = 3
                to_signal(self.set_green_style_get_bank_info(self.banks_panel.bank3pushButton))()

        def set_bank_name(self):
            new_bank_name = str(self.banks_panel.bank_name_line_edit.text())
            to_signal(self.disable_objects_for_transmission)()

            def enable_objects_after_transmission_update_banks_status():
                to_signal(self.enable_objects_after_transmission)()
                to_signal(self.get_bank_in_use)()

            Message(new_bank_name, id=Message.ID.setbankname,
                    positive_signal=to_signal(enable_objects_after_transmission_update_banks_status),
                    negative_signal=to_signal(self.enable_objects_after_transmission))

class StoreToFlashProcedure(RetxCount):

    def __init__(self, parent, max_retry=4):
        self.parent = parent
        self.send_data_thread()
        #self.__get_writing_stats_thread()
        self.__max_retry = max_retry
        self.__console_msg_factory = self.parent.console_msg_factory
        self.__get_current_file = self.parent.bin_file_panel.get_current_file
        self.__console = self.parent.gui_communication_signal.emit
        self.__save_button = self.parent.emulation_panel.save_button
        self.blink_save_btn()
        self.blink_save_btn.on_terminate = to_signal(self.__save_button.set_default_style_sheet)
        self.__progress_bar = self.parent.progress_bar
        self.__progress_bar_display_signal = to_signal(self.__progress_bar.display)
        self.__progress_bar_hide_signal = to_signal(self.__progress_bar.hide)
        self.__disable_objects_for_transmission_signal = to_signal(self.parent.disable_objects_for_transmission)
        self.__enable_objects_after_transmission_signal = to_signal(self.parent.enable_objects_after_transmission)
        self.__display_progress = self.__progress_bar.set_val_signal.emit
        self.timeout = 10


    def save_button_slot(self):
        self.reload_sram = self.parent.emulation_panel.reload_sram_checkbox.isChecked()
        bin_path = self.__get_current_file()
        try:
            self.bin_packets = BinFilePacketGenerator(bin_path)
            Message('rxflush', positive_signal=to_signal(self.send_data_thread.start),
                    negative_signal=self.__console_msg_factory("rxflush failed"))

        except IOError as e:
            self.__gui_communication_signal.emit("{}: {}".format(e.strerror, e.filename))
            raise e
        except BinSenderInvalidBinSize as e:
            self.__gui_communication_signal.emit('{} {}'.format(e.__class__, e.message))
            self.parent.bin_file_panel.combo_box.removeByStr(bin_path)
            self.parent.bin_file_panel.update_app_status_file()
            message_box("This is not 27c256 bin image: {}".format(bin_path))
            raise e

    def setup_gui_for_transmission(self):
        RetxCount.__init__(self)
        self.blink_save_btn.start()
        self.__progress_bar.set_title("sending...")
        self.__progress_bar_display_signal.emit()
        self.__disable_objects_for_transmission_signal.emit()

    def check_if_timeout(self, t0, timeout):
        if time.time() - t0 > timeout:
            self.__console("SAVE operation failed. Check error log")
            self.tear_down()
            raise Exception("Save fail")


    def __negative_feedback_slot(self):
        if self.timeout - (time.time() - self.t0) >= 0:
            self.__console("Retransmitting packet: {} [{:.0f}s]".format(self.packet_no, self.timeout - (time.time() - self.t0)))
        self.__feedback_received = True

    def __positive_feedback_slot(self):
        self.t0 = time.time()
        self.packets_to_send.remove(self.packets_to_send[0])
        self.__feedback_received = True

    #@thread_this_method(delay=0.5)
    def get_writing_stats(self):
        self.parent.send_data_suceeded = True
        debug("..executing")
        self.__console("Done in time {:.2f}".format(time.time() - self.start_time))
        self.__console("Num of retx {}".format(self.retx_sum()))
        Message("writingtime", positive_signal=to_signal(self.parent.message_handler.print_rx_buffer_to_console))

    @thread_this_method(period=0.4)
    def blink_save_btn(self):
        to_signal(self.__save_button.blink)()

    @thread_this_method()
    def send_data_thread(self):
        self.parent.send_data_suceeded = False
        debug("started {}".format(self.send_data_thread.__name__))
        timeout = self.timeout
        self.setup_gui_for_transmission()
        self.t0 = time.time()
        self.start_time = time.time()
        self.packets_to_send = range(0, len(self.bin_packets))
        while self.packets_to_send:
            self.check_if_timeout(self.t0, timeout)
            self.packet_no = self.packets_to_send[0]
            packet = self.bin_packets[self.packet_no]
            self.__feedback_received = False
            Message(struct.pack('B', self.packet_no) + packet, id=Message.ID.write_to_page,
                    positive_signal=self.__positive_feedback_slot,
                    negative_signal=self.__negative_feedback_slot,
                    extra_action_on_nack=self.add_retx_sum)
            self.__display_progress(((PACKETS_NUM-len(self.packets_to_send))*100)/PACKETS_NUM)
            while not self.__feedback_received:
                time.sleep(0.001)
                self.check_if_timeout(self.t0, timeout)
        if self.reload_sram:
            Message(id=Message.ID.reload_sram,
                    positive_signal=to_signal(self.parent.message_handler.print_rx_buffer_to_console))
        self.tear_down()
        self.get_writing_stats()

    def tear_down(self):
        self.blink_save_btn.kill()
        self.__progress_bar_hide_signal.emit()
        self.__enable_objects_after_transmission_signal.emit()




class ReadBinDataAbstract(RetxCount):
    """
    Abstract class for any data receiver class
    """
    def __init__(self, rx_buffer, max_retx=5):
        self.__rx_buffer = rx_buffer
        self.max_retx = max_retx
        self.progress_bar = self.parent.progress_bar
        self.show_progress = self.progress_bar.set_val_signal.emit
        self.console = self.parent.gui_communication_signal.emit
        self.disable_objects_for_transmission = self.parent.disable_objects_for_transmission
        self.enable_objects_after_transmission = self.parent.enable_objects_after_transmission
        self.autoopen_file = self.parent.emulation_panel.auto_open_checkbox.isChecked   #this is callable method
        self.open_bin_file = self.parent.event_handler.open_bin_file                    #this is callable method
        self.update_file_list = self.parent.bin_file_panel.combo_box.moveOnTop          #this is callable method
        self.read_data_thread()

    def read_data_button_slot(self):
        self.read_data_thread.start()

    def read_failure_slot(self):
        self.console("Read procedure failed")
        self.tear_down()

    def tear_down(self):
        debug("..executing")
        to_signal(self.progress_bar.hide)()
        to_signal(self.enable_objects_after_transmission)()


    def collect_packet(self):
        try:
            self.bin_receiver.receive_packet()  #check crc here
        except ReceptionFail:
            self.retx_cnt += 1
        if self.retx_cnt >= self.max_retx:
            return False
        self.__packet_received = True


    def save_received_file(self):
        rx_file_name = "reveived_{}".format(self.parent.banks_panel.bank_name_line_edit.text())
        if platform != 'Linux':
            rx_file_name = rx_file_name.replace('/', '\\')
        rx_file_name = rx_file_name.replace(' ', '_')
        f_path_bin = os.path.join(BIN_PATH, '{}.bin'.format(rx_file_name))
        f_path_hex = os.path.join(BIN_PATH, '{}.hex'.format(rx_file_name))
        self.bin_receiver.save_bin(file_path=f_path_bin)
        self.bin_receiver.save_hex(file_path=f_path_hex)
        self.console("Saved as:")
        self.console(f_path_hex)
        self.console(f_path_bin)
        self.update_file_list(f_path_bin)


    @thread_this_method()
    def read_data_thread(self):
        self.parent.receive_data_suceeded = False
        debug("..executing")
        timeout = 2
        t_start = time.time()
        self.bin_receiver = BinReceiver(self.__rx_buffer, timeout=2)
        self.progress_bar.set_title("receiving...")
        to_signal(self.progress_bar.display)()
        to_signal(self.disable_objects_for_transmission)()
        RetxCount.__init__(self)
        self.retx_cnt = 0
        while len(self.bin_receiver) <= self.bin_receiver.expected_packets_amount():
            tmp_len = len(self.bin_receiver)
            self.__packet_received = False
            t0 = time.time()
            Message(struct.pack('B', self.bin_receiver.packets_received()), id=self.msg_id,
                    positive_signal=self.collect_packet,
                    negative_signal=self.read_failure_slot)
            while not self.__packet_received:
                time.sleep(0.001)
                if time.time() - t0 > timeout:
                    self.read_failure_slot()
                    return False
            if len(self.bin_receiver) > tmp_len:
                self.retx_cnt = 0

            self.show_progress(100*len(self.bin_receiver)/self.bin_receiver.expected_packets_amount())

        self.disp_retx_count(self.console)
        self.console("Read done in {:.2f}".format(time.time() - t_start))
        self.save_received_file()
        self.parent.receive_data_suceeded = True
        if self.autoopen_file() == True:
            self.open_bin_file()
        self.tear_down()


class ReadSramProcedure_V2(ReadBinDataAbstract):
    def __init__(self, parent):
        self.parent = parent
        self.msg_id = Message.ID.get_sram_packet
        ReadBinDataAbstract.__init__(self, rx_buffer=self.parent.rx_buffer)

    def tear_down(self):
        ReadBinDataAbstract.tear_down(self)
        Message(id=Message.ID.reload_sram)

class ReadBankProcedure_V2(ReadBinDataAbstract):
    def __init__(self, parent):
        self.parent = parent
        self.msg_id = Message.ID.get_bank_packet
        ReadBinDataAbstract.__init__(self, rx_buffer=self.parent.rx_buffer)


class SyncFileToSramProcedure():

    def emulate_button_slot(self):
        try:
            if self.bin_tracker.track_file.isRunning():
                self.bin_tracker.track_file.kill()
                self.emulation_panel.emulate_button.set_default_style_sheet()
                return
        except AttributeError:
            pass
        bin_path = self.bin_file_panel.get_current_file()
        self.bin_tracker = BinTracker(bin_path, self.event_handler, to_signal(self.emulation_panel.emulate_button.blink))
        self.bin_tracker.start()

    def emulation_diffs_present_slot(self):
        Message('rxflush', positive_signal=to_signal(self.send_sram_bytes),
                negative_signal=to_signal(self.diffs_pattern_negative_slot), timeout=0.5)

    def diffs_pattern_negative_slot(self):
        time.sleep(0.5)
        to_signal(self.bin_tracker.resume)()

    def send_sram_bytes(self):
        max_msg_len = 256 * 8   #single packet size
        msg_body = ''
        bytes_cnt = 0
        while self.bin_tracker.diffs:
            msg_body += self.bin_tracker.diffs.popitem()
            bytes_cnt += 1
            if len(msg_body) >= max_msg_len - 3:
                break
        Message(id=Message.ID.send_sram_bytes, raw_msg=msg_body, positive_signal=self.console_msg_factory("Updated sram of {} bytes\nRemaining: {} bytes".format(bytes_cnt, len(self.bin_tracker.diffs))),
                extra_action_on_nack=to_signal(self.bin_tracker.resume),
                extra_action_on_ack=to_signal(self.bin_tracker.resume))


