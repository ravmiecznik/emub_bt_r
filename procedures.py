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

    def disp_retx_count(self):
        """
        gui communication signal must be part of Child class
        :return:
        """
        self.gui_communication_signal.emit("Num of retx {}".format(self.__retx_sum))

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
            self.enable_objects_after_transmission()
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
            to_signal(self.disable_objects_for_transmission)

            def enable_objects_after_transmission_update_banks_status():
                self.enable_objects_after_transmission
                to_signal(self.get_bank_in_use)()

            Message(new_bank_name, id=Message.ID.setbankname,
                    positive_signal=to_signal(enable_objects_after_transmission_update_banks_status),
                    negative_signal=to_signal(self.enable_objects_after_transmission))

class StoreToFlashProcedure_v2(RetxCount):

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

class StoreToFlashProcedure(RetxCount):
    """
    Simplified version of StoreToFLash procedure
    """
    def __init__(self, max_retry=4):
        #init threads
        self.send_data()
        self.get_writing_stats()
        #self.get_writing_stats()

        self.__was_ack = False

        self.__max_retry = max_retry
        self.__try = 0

    def __set_ack(self):
        self.__was_ack = True
        self.__tx_feedback_received = True

    def __set_nack(self):
        self.__was_ack = False

    def store_to_flash_button_slot(self):
        #self.send_data_suceeded = False
        self.t0 = time.time()
        bin_path = self.bin_file_panel.get_current_file()
        self.__try = 0
        if bin_path:
            try:
                self.bin_sender = BinFilePacketGenerator(bin_path)
                Message('rxflush', positive_signal=to_signal(self.send_data.start),
                        negative_signal=self.console_msg_factory("rxflush failed"))

            except IOError as e:
                self.gui_communication_signal.emit("{}: {}".format(e.strerror, e.filename))
                raise e
            except BinSenderInvalidBinSize as e:
                self.gui_communication_signal.emit('{} {}'.format(e.__class__, e.message))
                self.bin_file_panel.combo_box.removeByStr(bin_path)
                self.bin_file_panel.update_app_status_file()
                message_box("This is not 27c256 bin image: {}".format(bin_path))
                raise e


    @thread_this_method()
    def send_data(self):
        self.send_data_suceeded = False
        debug("started {}".format(self.send_data.__name__))
        RetxCount.__init__(self)
        #self.__try += 1
        self.blink_save_btn.start()
        self.progress_bar.set_title("sending...")
        to_signal(self.progress_bar.display)()
        to_signal(self.progress_bar.display)()
        to_signal(self.disable_objects_for_transmission)()

        self.__tx_feedback_received = False
        def send_packets(packets=None, progress=0):
            self.failed_tx_packets = []
            packets = xrange(0, len(self.bin_sender)) if packets is None else packets
            print "sending packets", packets
            for packet_no in packets:
                packet = self.bin_sender[packet_no]
                if packet_no < PACKETS_NUM:
                    debug("Call write to page message. Packet num: {}".format(packet_no))
                    self.__set_nack()
                    self.packet_no = packet_no
                    self.__tx_feedback_received = False
                    Message(struct.pack('B', packet_no) + packet, id=Message.ID.write_to_page,
                            positive_signal=to_signal(self.__set_ack),
                            #negative_signal=to_signal(self.send_data_packet_teardown_on_fail),
                            negative_signal=to_signal(self.collect_failed_tx_packets),
                            extra_action_on_nack=self.add_retx_sum)
                    while not self.__tx_feedback_received: time.sleep(0.001)
                    if self.__was_ack:
                        progress += 1
                    self.progress_bar.set_val_signal.emit(progress * 100 / PACKETS_NUM)
                else:
                    break
            check_result()

        def check_result():
            if not self.failed_tx_packets:
                self.get_writing_stats.start()
                if self.emulation_panel.reload_sram_checkbox.isChecked():
                    Message(id=Message.ID.reload_sram, positive_signal=to_signal(self.message_handler.print_rx_buffer_to_console))
            else:
                self.__max_retry -= 1
                print 'retx', self.__max_retry
                if self.__max_retry == 0:
                    to_signal(self.send_data_packet_teardown_on_fail).emit()
                send_packets(self.failed_tx_packets, progress=len(self.bin_sender) - len(self.failed_tx_packets))
            to_signal(self.progress_bar.hide)()
            to_signal(self.enable_objects_after_transmission)()
            self.blink_save_btn.kill()
        send_packets()

    def collect_failed_tx_packets(self):
        self.failed_tx_packets.append(self.packet_no)
        self.__tx_feedback_received = True

    @thread_this_method(delay=1)
    def get_writing_stats(self):
        self.send_data_suceeded = True
        debug("..executing")
        self.blink_save_btn.kill()
        self.gui_communication_signal.emit("Done in time {:.2f}".format(time.time() - self.t0))
        self.disp_retx_count()
        to_signal(self.progress_bar.hide)()
        to_signal(self.progress_bar.hide)()
        to_signal(self.enable_objects_after_transmission)()
        Message("writingtime", positive_signal=to_signal(self.message_handler.print_rx_buffer_to_console))


    def send_data_packet_teardown_on_fail(self):
        self.send_data.kill()
        self.blink_save_btn.kill()
        to_signal(self.enable_objects_after_transmission)()
        to_signal(self.progress_bar.hide)()
        self.gui_communication_signal.emit("SAVE operation failed. Check error log")
        raise Exception("Save fail")



class ReadBinDataFromEmu(RetxCount):
    """
    This class is isolated from MainWindow but it is a part of it.
    It is iherited in MainWindow so all objects are shared between this class and MainWindow
    """
    def __init__(self, rx_buffer, max_retx=5):
        self.__rx_buffer = rx_buffer
        self.bin_receiver = BinReceiver(self.__rx_buffer, timeout=2)
        self.max_retx = max_retx


    def read_data_thread(self):
        self.receive_data_suceeded = False
        debug("..executing")
        t0 = time.time()
        self.bin_receiver.reset()
        self.gui_communication_signal.emit("{:X}".format(len(self.bin_receiver)))
        self.progress_bar.set_title("receiving...")
        to_signal(self.progress_bar.display)()
        to_signal(self.disable_objects_for_transmission)()
        RetxCount.__init__(self)


        def get_packet(packet_count, max_retx=self.max_retx):
            """
            This inner function keeps control of retransmissions in case of CrcFail or timeout in repception
            :param packet_count:
            :param max_retx:
            :return:
            """

            try:
                Message(struct.pack('B', packet_count), id=self.msg_id, positive_signal=lambda: None)
                self.bin_receiver.receive_packet()
                debug("try statmentent returns True")
                return True
            except ReceptionFail as e:
                debug("..handling exception: {}".format(ReceptionFail))
                if max_retx <= 0:
                    self.gui_communication_signal.emit("Reception failed")
                    self.tear_down()
                    debug("raise final exception")
                    raise Exception("Reception failed")
                time.sleep(0.1)
                self.add_retx_sum()
                #recursive call until max_retx not reached
                return get_packet(packet_count, max_retx - 1)

        packet_count = 0
        self.__rx_buffer.flush()
        self.progress_bar.set_title("receiving...")
        to_signal(self.progress_bar.show)()
        self.progress_bar.set_val_signal.emit(packet_count * 100 / PACKETS_NUM)

        while len(self.bin_receiver) < 0x8000:
            assert packet_count < PACKETS_NUM
            if get_packet(packet_count):
                packet_count += 1
                self.progress_bar.set_val_signal.emit(packet_count * 100 / PACKETS_NUM)

        self.disp_retx_count()
        if platform != 'Linux':
            self.file_name = self.file_name.replace('/', '\\')
        self.file_name = self.file_name.replace(' ', '_')
        f_path_bin = os.path.join(BIN_PATH, '{}.bin'.format(self.file_name))
        f_path_hex = os.path.join(BIN_PATH, '{}.hex'.format(self.file_name))

        self.bin_receiver.save_bin(file_path=f_path_bin)
        self.bin_receiver.save_hex(file_path=f_path_hex)
        self.gui_communication_signal.emit("Read done in {:.2f}".format(time.time() - t0))
        self.gui_communication_signal.emit("Saved as:")
        self.gui_communication_signal.emit(f_path_hex)
        self.gui_communication_signal.emit(f_path_bin)
        self.bin_file_panel.combo_box.moveOnTop(f_path_bin)
        self.receive_data_suceeded = True
        if self.emulation_panel.auto_open_checkbox.isChecked():
            self.event_handler.open_bin_file()
        self.tear_down()

class ReadSramProcedure(ReadBinDataFromEmu):

    def __init__(self, *args, **kwargs):
        ReadBinDataFromEmu.__init__(self, *args, **kwargs)
        self.read_bin_data = GuiThread(self.read_data_thread)


    def read_sram_button_slot(self):
        self.msg_id = Message.ID.get_sram_packet
        self.file_name = 'received_sram'
        debug("..executing")
        RetxCount.__init__(self)
        self.read_bin_data.start()


    def tear_down(self):
        debug("..executing")
        to_signal(self.progress_bar.hide)()
        to_signal(self.enable_objects_after_transmission)()
        #Message(id=Message.ID.reload_sram, positive_signal=self.message_handler.print_rx_buffer_to_console)

class ReadBankProcedure(ReadBinDataFromEmu):

    def __init__(self, *args, **kwargs):
        ReadBinDataFromEmu.__init__(self, *args, **kwargs)
        self.read_bin_data = GuiThread(self.read_data_thread)


    def read_bank_button_slot(self):
        self.msg_id = Message.ID.get_bank_packet
        self.file_name = "reveived_{}".format(self.banks_panel.bank_name_line_edit.text())
        debug("..executing")
        RetxCount.__init__(self)
        self.read_bin_data.start()

    def tear_down(self):
        debug("..executing")
        to_signal(self.progress_bar.hide)()
        to_signal(self.enable_objects_after_transmission)()

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


