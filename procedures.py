"""
author: Rafal Miecznik
contact: ravmiecznk@gmail.com
"""

import time, os
import struct
from event_handler import to_signal
from gui_thread import GuiThread, thread_this_method
from setup_emubt import warn, error, info, debug, BIN_PATH
from bin_handler import BinFilePacketGenerator, BinSenderInvalidBinSize, ReceptionFail, BinReceiver
from message_box import message_box
from bin_tracker import BinTracker
from message_handler import TransmissionStats, MessageSender, MessageReceiver, RxMessage
from io import BytesIO
import platform, os


EEPROM_SIZE = 0x8000
PACKET_SIZE = 256 * 8
PACKETS_NUM = EEPROM_SIZE / PACKET_SIZE


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


class WritePackets:
    def __init__(self, parent, bin_packets, retx_timeout=0.5):
        self.__retx_timeout = retx_timeout
        self.rx_message_buffer = parent.rx_message_buffer
        self.message_sender = parent.message_sender
        self.gui_communication_signal = parent.gui_communication_signal
        self.progress_bar = parent.progress_bar
        self.bin_packets = bin_packets
        self.tx_stats = TransmissionStats()
        self.write_thread = GuiThread(self.write_packets_procedure)
        self.parent_send_msg = parent.send_message
        self.set_bank_name = parent.set_bank_name
        self.disable_objects_for_transmission_signal = parent.disable_objects_for_transmission_signal
        self.enable_objects_after_transmission_signal = parent.enable_objects_after_transmission_signal
        self.reload_sram = parent.emulation_panel.reload_sram_checkbox.isChecked

    def check_repsonse(self, context):
        retx_timeout = self.__retx_timeout
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
        _context = self.message_sender.send(MessageSender.ID.write_to_page, body=msg_body)
        return _context

    def __tear_down(self):
        self.gui_communication_signal.emit("Upload failed")
        to_signal(self.progress_bar.hide).emit()
        self.enable_objects_after_transmission_signal.emit()

    def write_packets_procedure(self):
        self.disable_objects_for_transmission_signal.emit()
        self.message_sender.send(MessageSender.ID.rxflush)
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
            self.send_packet(packet, packet_num=packet_num)
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
            if self.reload_sram():
                self.parent_send_msg(MessageSender.ID.reload_sram)
            self.gui_communication_signal.emit("File transmitted in: {}".format(time.time() - t_start))
            self.gui_communication_signal.emit(self.tx_stats)
            self.message_sender.send(m_id=MessageSender.ID.get_write_stats)
            self.set_bank_name(bank_name.replace('_sram', ''))
        to_signal(self.progress_bar.hide).emit()
        self.enable_objects_after_transmission_signal.emit()


class ReadPackets:
    def __init__(self, parent, message_id, retx_timeout=1):
        self.__retx_timeout = retx_timeout
        self.message_id = message_id
        self.rx_message_buffer = parent.rx_message_buffer
        self.message_sender = parent.message_sender
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

    def check_response(self, context):
        retx_timeout = self.__retx_timeout
        t0 = time.time()
        while context not in self.rx_message_buffer:
            time.sleep(0.1)
            if time.time() - t0 > retx_timeout:
                return RxMessage.rx_id_tuple.index('dtx')
        else:
            msg = self.rx_message_buffer.pop(context)  # gets message and returns id from buffer
            self.received.write(msg.msg)
            result = msg.id
        return result

    def send_request(self, packet_num):
        msg_body = struct.pack('B', packet_num)
        _context = self.message_sender.send(self.message_id, body=msg_body)
        return _context

    def tear_down_on_fail(self):
        self.gui_communication_signal.emit("Read failed")
        to_signal(self.progress_bar.hide).emit()
        self.enable_objects_after_transmission_signal.emit()

    def read_packets_procedure(self):
        self.disable_objects_for_transmission_signal.emit()
        self.message_sender.send(MessageSender.ID.rxflush)
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

            self.check_resp_thr = GuiThread(self.check_response, args=(MessageSender.context,))
            self.check_resp_thr.start()
            self.send_request(packet_num=packet_num)
            while self.check_resp_thr.returned() is None:
                time.sleep(0.001)
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


class ReadSramProcedure(ReadPackets):
    def __init__(self, parent, retx_timeout=0.5):
        ReadPackets.__init__(self, parent, message_id=MessageSender.ID.get_sram_packet, retx_timeout=retx_timeout)
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
    def __init__(self, parent, retx_timeout=0.5):
        ReadPackets.__init__(self, parent, message_id=MessageSender.ID.get_bank_packet, retx_timeout=retx_timeout)

    def extra_teardown(self):
        rx_file_name = self.get_bank_name()
        f_path_bin = os.path.join(BIN_PATH, '{}.bin'.format(rx_file_name))
        with open(f_path_bin, 'wb') as f:
            self.received.seek(0)
            f.write(self.received.read())
        self.gui_communication_signal.emit("Saved as: {}".format(f_path_bin))
        self.update_file_list(f_path_bin)
