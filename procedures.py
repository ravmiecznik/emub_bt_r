"""
author: Rafal Miecznik
contact: ravmiecznk@gmail.com
"""

import time, os
import struct
from event_handler import to_signal
from my_gui_thread import GuiThread, thread_this_method
from setup_emubt import warn, error, info, debug, BIN_PATH
from bin_handler import BinFilePacketGenerator, BinSenderInvalidBinSize, ReceptionFail, BinReceiver
from message_box import message_box
from bin_tracker import BinTracker
from message_handler import TransmissionStats, MessageSender, MessageReceiver, RxMessage
from io import BytesIO
from bin_handler import bin_repr
from call_tracker import method_call_track

EEPROM_SIZE = 0x8000
PACKET_SIZE = 256 * 8
PACKETS_NUM = EEPROM_SIZE / PACKET_SIZE

import platform, os

class SendTimeout(Exception):
    pass

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
        @thread_this_method(period=1, delay=1)
        def bank_in_use_monitor(self):
            debug("monitor bank in use")
            if self.bank_in_use is None:
                self.get_bank_in_use()
                debug("setting bank in use")

        @thread_this_method()
        def read_bank_info(self):
            timeout = 1
            t0 = time.time()
            raw_buff = ''
            #to_signal(self.disable_objects_for_transmission)()
            self.disable_objects_for_transmission_signal()

            def set_fail():
                self.banks_panel.bank_name_line_edit.setText("!!FAIL!!")
                self.enable_objects_after_transmission_signal()

            while '<' not in raw_buff:
                try:
                    raw_buff = self.emulator.raw_buffer.read().split('>')[1]
                except IndexError:
                    set_fail()
                    return False
                time.sleep(0.001)
                if time.time() - t0 > timeout:
                    to_signal(set_fail)()
                    self.enable_objects_after_transmission_signal()
                    return False
            bank_name = raw_buff.split('|')[0]

            def set_text():
                self.banks_panel.bank_name_line_edit.setText(bank_name)

            to_signal(set_text)()
            self.enable_objects_after_transmission_signal()


        def bank_name_line_edit_event(self):
            self.emulation_panel.setDisabled(True)
            self.banks_panel.bank1pushButton.setDisabled(True)
            self.banks_panel.bank2pushButton.setDisabled(True)
            self.banks_panel.bank3pushButton.setDisabled(True)
            self.control_panel.reflash_button.setDisabled(True)

        def set_green_style_get_bank_info(self, bank_button):
            self.bank_in_use = ['bank 1', 'bank 2', 'bank 3'].index(bank_button.text()) + 1
            #print "set bank in use", self.bank_in_use
            def wrapper():
                to_signal(bank_button.set_green_style_sheet)()
                self.emulator.raw_buffer.flush()
                Message(id=Message.ID.get_bank_info, positive_signal=to_signal(self.read_bank_info.start))

            return GuiThread(wrapper, delay=0.1).start


        def bank1set_slot(self):
            self.clear_bank_status()
            Message('bank1set',
                    positive_signal=to_signal(self.set_green_style_get_bank_info(self.banks_panel.bank1pushButton)),
                    negative_signal=to_signal(self.clear_bank_status))

        def bank2set_slot(self):
            self.clear_bank_status()
            Message('bank2set',
                    positive_signal=to_signal(self.set_green_style_get_bank_info(self.banks_panel.bank2pushButton)),
                    negative_signal=to_signal(self.clear_bank_status))

        def bank3set_slot(self):
            self.clear_bank_status()
            Message('bank3set',
                    positive_signal=to_signal(self.set_green_style_get_bank_info(self.banks_panel.bank3pushButton)),
                    negative_signal=to_signal(self.clear_bank_status))

        def get_bank_in_use(self):
            Message('bankinuse', positive_signal=to_signal(self.read_bank_in_use), negative_signal=to_signal(self.clear_bank_status))

        def clear_bank_status(self):
            self.bank_in_use = None
            to_signal(self.banks_panel.set_default_style_sheet_for_buttons)()

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
            def enable_objects_after_transmission_update_banks_status():
                self.enable_objects_after_transmission_signal()
                to_signal(self.get_bank_in_use)()

            Message(new_bank_name, id=Message.ID.setbankname,
                    positive_signal=to_signal(enable_objects_after_transmission_update_banks_status),
                    negative_signal=self.enable_objects_after_transmission_signal)
            self.disable_objects_for_transmission_signal()

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
        self.__disable_objects_for_transmission_signal = self.parent.disable_objects_for_transmission_signal
        self.__enable_objects_after_transmission_signal = self.parent.enable_objects_after_transmission_signal
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
        bin_name = os.path.basename(self.bin_packets.bin_path).split('.')[0].replace('received_', '')
        self.parent.set_new_bank_name_signal.emit(bin_name)
        if self.reload_sram:
            Message(id=Message.ID.reload_sram,
                    positive_signal=to_signal(self.parent.message_handler.print_rx_buffer_to_console))
        self.tear_down()
        self.get_writing_stats()
        self.parent.insert_new_file_signal.emit(bin_name)

    def tear_down(self):
        #self.blink_save_btn.kill()
        self.blink_save_btn.terminate()
        self.__progress_bar_hide_signal.emit()
        self.__enable_objects_after_transmission_signal.emit()




class ReadBinDataAbstract(RetxCount):
    """
    Abstract class for any data receiver class
    """
    def __init__(self, rx_buffer, max_retx=5, rx_file_name_template='received_'):
        self.__rx_buffer = rx_buffer
        self.__rx_file_template = rx_file_name_template + '{}'
        self.max_retx = max_retx
        self.progress_bar = self.parent.progress_bar
        self.show_progress = self.progress_bar.set_val_signal.emit
        self.console = self.parent.gui_communication_signal.emit
        self.disable_objects_for_transmission_signal = self.parent.disable_objects_for_transmission_signal
        self.enable_objects_after_transmission_signal = self.parent.enable_objects_after_transmission_signal
        #self.enable_objects_after_transmission = self.parent.enable_objects_after_transmission
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
        self.enable_objects_after_transmission_signal()


    def collect_packet(self):
        try:
            self.bin_receiver.receive_packet()  #check crc here
        except ReceptionFail:
            self.retx_cnt += 1
        if self.retx_cnt >= self.max_retx:
            return False
        self.__packet_received = True


    def save_received_file(self):
        rx_file_name = self.__rx_file_template.format(self.parent.banks_panel.bank_name_line_edit.text())
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
        self.disable_objects_for_transmission_signal()
        #to_signal(self.disable_objects_for_transmission)()
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
        ReadBinDataAbstract.__init__(self, rx_buffer=self.parent.rx_buffer, rx_file_name_template='received_sram_')

    def tear_down(self):
        ReadBinDataAbstract.tear_down(self)
        Message(id=Message.ID.reload_sram)

# class ReadBankProcedure_V2(ReadBinDataAbstract):
#     def __init__(self, parent):
#         self.parent = parent
#         self.msg_id = Message.ID.get_bank_packet
#         ReadBinDataAbstract.__init__(self, rx_buffer=self.parent.rx_buffer)


class SyncFileToSramProcedure():

    def emulate_button_slot(self):
        try:
            if self.bin_tracker.track_file.isRunning():
                #self.bin_tracker.track_file.kill()
                self.bin_tracker.track_file.terminate()
                GuiThread(to_signal(self.emulation_panel.emulate_button.set_default_style_sheet), delay=0.1).start()
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


class WritePackets():
    def __init__(self, parent, bin_packets):
        self.rx_message_buffer = parent.rx_message_buffer
        self.message_handler = parent.message_handler
        self.gui_communication_signal = parent.gui_communication_signal
        self.progress_bar = parent.progress_bar
        self.bin_packets = bin_packets
        self.tx_stats = TransmissionStats()
        self.write_thread = GuiThread(self.write_packets_procedure)
        self.parent_send_msg = parent.send_message
        self.set_bank_name = parent.set_bank_name
        self.disable_objects_for_transmission_signal = parent.disable_objects_for_transmission_signal
        self.enable_objects_after_transmission_signal = parent.enable_objects_after_transmission_signal

    def check_repsonse(self, context):
        retx_timeout = 0.5
        t0 = time.time()
        while context not in self.rx_message_buffer:
            if time.time() - t0 > retx_timeout:
                return RxMessage.rx_id_tuple.index('dtx')
            time.sleep(0.001)
        else:
            result = self.rx_message_buffer.pop(context).id  # gets message and returns id from buffer
        return result

    def send_packet(self, packet, packet_num):
        msg_body = struct.pack('B', packet_num) + packet
        _context = self.message_handler.send(MessageSender.ID.write_to_page, body=msg_body)
        return _context

    def __tear_down(self):
        self.gui_communication_signal.emit("Upload failed")
        to_signal(self.progress_bar.hide).emit()
        self.enable_objects_after_transmission_signal.emit()

    def write_packets_procedure(self):
        self.disable_objects_for_transmission_signal.emit()
        self.message_handler.send(MessageSender.ID.rxflush)
        time.sleep(0.5)
        max_timeout = 25
        t_start = time.time()
        bank_name_full = os.path.basename(self.bin_packets.bin_path)
        bank_name = os.path.splitext(bank_name_full)[0]
        self.progress_bar.set_title("SENDING: {}".format(bank_name_full))
        to_signal(self.progress_bar.display).emit()

        packet_num = 0
        packet = self.bin_packets.next()
        while self.progress_bar.isHidden(): time.sleep(0.1)
        while packet_num < 16:
            if self.progress_bar.isHidden():
                self.gui_communication_signal.emit("Upload procedure terminated")
                break
            self.check_resp_thr = GuiThread(self.check_repsonse, args=(MessageSender.context,))
            self.check_resp_thr.start()
            context = self.send_packet(packet, packet_num=packet_num)
            while self.check_resp_thr.returned() is None: time.sleep(0.001)
            response = self.check_resp_thr.returned()

            if response == RxMessage.rx_id_tuple.index('ack'):
                self.tx_stats.ack()
                self.progress_bar.set_val_signal.emit(float(packet_num) / 16 * 100)
                packet_num += 1
                try:
                    packet = self.bin_packets.next()
                except StopIteration:
                    pass
            else:
                self.tx_stats.nack()
            if time.time() - t_start > max_timeout:
                self.__tear_down()
                raise SendTimeout("TIMEOUT")
        else:
            self.parent_send_msg(MessageSender.ID.reload_sram, timeout=1)
            self.gui_communication_signal.emit("File transmitted in: {}".format(time.time() - t_start))
            self.gui_communication_signal.emit(self.tx_stats)
        to_signal(self.progress_bar.hide).emit()
        self.message_handler.send(m_id=MessageSender.ID.get_write_stats)
        self.set_bank_name(bank_name.replace('_sram', ''))
        self.enable_objects_after_transmission_signal.emit()



class ReadPackets():
    def __init__(self, parent, message_id):
        self.message_id = message_id
        self.rx_message_buffer = parent.rx_message_buffer
        self.message_handler = parent.message_handler
        self.gui_communication_signal = parent.gui_communication_signal
        self.progress_bar = parent.progress_bar
        self.tx_stats = TransmissionStats()
        self.read_thread = GuiThread(self.read_packets_procedure)
        self.received = BytesIO()
        self.get_bank_name = parent.banks_panel.get_bank_name_text
        self.update_file_list = parent.bin_file_panel.combo_box.moveOnTop
        self.disable_objects_for_transmission_signal = parent.disable_objects_for_transmission_signal
        self.enable_objects_after_transmission_signal = parent.enable_objects_after_transmission_signal
        self.auto_open = parent.emulation_panel.auto_open_checkbox.isChecked
        self.event_handler = parent.event_handler


    def extra_teardown(self):
        pass

    def check_repsonse(self, context):
        retx_timeout = 0.5
        t0 = time.time()
        while context not in self.rx_message_buffer:
            if time.time() - t0 > retx_timeout:
                return RxMessage.rx_id_tuple.index('dtx')
            time.sleep(0.0001)
        else:
            msg = self.rx_message_buffer.pop(context)  # gets message and returns id from buffer
            self.received.write(msg.msg)
            result = msg.id
        return result

    def get_packet(self, packet_num):
        msg_body = struct.pack('B', packet_num)
        _context = self.message_handler.send(self.message_id, body=msg_body)
        return _context

    def tear_down_on_fail(self):
        self.gui_communication_signal.emit("Read failed")
        to_signal(self.progress_bar.hide).emit()
        self.enable_objects_after_transmission_signal.emit()

    def read_packets_procedure(self):
        self.disable_objects_for_transmission_signal.emit()
        self.message_handler.send(MessageSender.ID.rxflush)
        time.sleep(0.5)
        max_timeout = 20
        t_start = time.time()
        self.progress_bar.set_title("RECEIVING")
        to_signal(self.progress_bar.display).emit()
        packet_num = 0
        while self.progress_bar.isHidden(): time.sleep(0.1)
        while packet_num < 16:
            if self.progress_bar.isHidden():
                self.gui_communication_signal.emit("Read procedure terminated")
                break

            self.check_resp_thr = GuiThread(self.check_repsonse, args=(MessageSender.context,))
            self.check_resp_thr.start()
            context = self.get_packet(packet_num=packet_num)
            while self.check_resp_thr.returned() is None: time.sleep(0.001)
            response = self.check_resp_thr.returned()
            if response == RxMessage.rx_id_tuple.index('ack'):
                self.tx_stats.ack()
                self.progress_bar.set_val_signal.emit(float(packet_num) / 16 * 100)
                packet_num += 1
            else:
                self.tx_stats.nack()
                time.sleep(0.5)
            if time.time() - t_start > max_timeout:
                self.tear_down_on_fail()
                break
        else:
            self.gui_communication_signal.emit("File reveived in: {}".format(time.time() - t_start))
            self.gui_communication_signal.emit(self.tx_stats)
            self.extra_teardown()
        to_signal(self.progress_bar.hide).emit()
        self.enable_objects_after_transmission_signal.emit()
        if self.auto_open():
            self.event_handler.open_bin_file()

        #print bin_repr(self.received)


class ReadSramProcedure(ReadPackets):
    def __init__(self, parent):
        ReadPackets.__init__(self, parent, message_id=MessageSender.ID.get_sram_packet)
        self.parent_send_msg = parent.send_message


    def extra_teardown(self):
        self.parent_send_msg(MessageSender.ID.reload_sram)
        rx_file_name = self.get_bank_name()
        try:
            f_path_bin = os.path.join(BIN_PATH, '{}_sram.bin'.format(rx_file_name))
        except:
            f_path_bin = os.path.join(BIN_PATH, '{}_sram.bin'.format('XXXX'))
        with open(f_path_bin, 'wb') as f:
            self.received.seek(0)
            f.write(self.received.read())
        self.gui_communication_signal.emit("Saved as: {}".format(f_path_bin))
        self.update_file_list(f_path_bin)

class ReadBankProcedure(ReadPackets):
    def __init__(self, parent):
        ReadPackets.__init__(self, parent, message_id=MessageSender.ID.get_bank_packet)

    def extra_teardown(self):
        rx_file_name = self.get_bank_name()
        f_path_bin = os.path.join(BIN_PATH, '{}.bin'.format(rx_file_name))
        with open(f_path_bin, 'wb') as f:
            self.received.seek(0)
            f.write(self.received.read())
        self.gui_communication_signal.emit("Saved as: {}".format(f_path_bin))
        self.update_file_list(f_path_bin)