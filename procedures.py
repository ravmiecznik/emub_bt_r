"""
author: Rafal Miecznik
contact: ravmiecznk@gmail.com
"""

import time
import struct
from event_handler import to_signal
from message_handler import Message
from my_gui_thread import GuiThread, thread_this_method
from bin_handler import BinSender, BinSenderFileNotPresent, BinSenderInvalidBinSize, CrcFail, PacketReceptionTimeout, BinReceiver

EEPROM_SIZE = 0x8000
PACKET_SIZE = 256 * 8
PACKETS_NUM = EEPROM_SIZE / PACKET_SIZE


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


class StoreToFlashProcedure(RetxCount):
    """
    Simplified version of StoreToFLash procedure
    """
    def __init__(self, max_retry = 2):
        #init threads
        self.send_data()
        #self.get_writing_stats()

        self.__was_ack = False

        self.__max_retry = max_retry
        self.__try = 0

    def __set_ack(self):
        self.__was_ack = True

    def __set_nack(self):
        self.__was_ack = False

    def store_to_flash_button_slot(self):
        self.t0 = time.time()
        bin_path = self.bin_file_panel.get_current_file()
        self.__try = 0
        if bin_path:
            try:
                self.bin_sender = BinSender(bin_path)
                Message('rxflush', positive_signal=to_signal(self.send_data.start),
                        negative_signal=self.console_msg_factory("rxflush failed"))
            except IOError as e:
                self.gui_communication_signal.emit("{}: {}".format(e.strerror, e.filename))
                raise e
            except BinSenderInvalidBinSize as e:
                self.gui_communication_signal.emit('{} {}'.format(e.__class__, e.message))
                raise e


    @thread_this_method()
    def send_data(self):
        RetxCount.__init__(self)
        self.__try += 1
        self.blink_save_btn.start()
        self.progress_bar.set_title("sending...")
        to_signal(self.progress_bar.display)()
        to_signal(self.progress_bar.display)()
        to_signal(self.disable_objects_for_transmission)()

        for packet_no, packet in enumerate(self.bin_sender):
            if packet_no < PACKETS_NUM:
                self.__set_nack()
                Message(struct.pack('B', packet_no) + packet, id=Message.ID.write_to_page,
                        positive_signal=to_signal(self.__set_ack),
                        negative_signal=to_signal(self.send_data_packet_teardown_on_fail),
                        extra_action_on_nack=self.add_retx_sum)
                while not self.__was_ack: time.sleep(0.001)
                self.progress_bar.set_val_signal.emit(packet_no * 100 / PACKETS_NUM)
            else:
                break

        to_signal(self.progress_bar.hide)()
        to_signal(self.enable_objects_after_transmission)()
        self.get_writing_stats()
        self.blink_save_btn.kill()

    #@thread_this_method()
    def get_writing_stats(self):
        to_signal(self.enable_objects_after_transmission)()
        self.blink_save_btn.kill()
        self.gui_communication_signal.emit("Done in time {:.2f}".format(time.time() - self.t0))
        self.disp_retx_count()
        Message("writingtime")
        to_signal(self.progress_bar.hide)()
        to_signal(self.progress_bar.hide)()
        to_signal(self.enable_objects_after_transmission)()


    def send_data_packet_teardown_on_fail(self):
        self.send_data.kill()
        self.blink_save_btn.kill()
        to_signal(self.enable_objects_after_transmission)()
        to_signal(self.progress_bar.hide)()
        if self.__try <= self.__max_retry:
            self.gui_communication_signal.emit("SAVE operation failed. Retry: {}/{}".format(self.__try, self.__max_retry))
            GuiThread(self.send_data.start, delay=1).start()
        else:
            self.gui_communication_signal.emit("SAVE operation failed. Check error log")
            raise Exception("Save fail")


class ReadSramProcedure(RetxCount):
    """
    This class is isolated from MainWindow but it is a part of it.
    It is iherited in MainWindow so all objects are shared between this class and MainWindow
    """
    def __init__(self, rx_buffer, max_retx=5):
        self.bin_receiver = BinReceiver(rx_buffer, timeout=2)
        self.max_retx = max_retx

        #convert method to thread by calling it
        self.read_sram_thread()


    def read_sram_button_slot(self):
        RetxCount.__init__(self)
        self.read_sram_thread.start()


    @thread_this_method()
    def read_sram_thread(self):
        t0 = time.time()
        self.bin_receiver.reset()
        self.gui_communication_signal.emit("{:X}".format(len(self.bin_receiver)))
        self.progress_bar.set_title("receiving...")
        to_signal(self.progress_bar.display)()
        to_signal(self.disable_objects_for_transmission)()
        RetxCount.__init__(self)

        def tear_down():
            to_signal(self.progress_bar.hide)()
            to_signal(self.enable_objects_after_transmission)()
            print self.bin_receiver

        def get_packet(packet_count, max_retx=self.max_retx):
            """
            This inner function keeps control of retransmissions in case of CrcFail or timeout in repception
            :param packet_count:
            :param max_retx:
            :return:
            """
            try:
                Message(struct.pack('B', packet_count), id=Message.ID.get_sram_packet, positive_signal=lambda: None)
                self.bin_receiver.receive_packet()
                return True
            except (PacketReceptionTimeout, CrcFail) as e:
                if max_retx <= 0:
                    self.gui_communication_signal.emit("Reception failed")
                    tear_down()
                    raise Exception("Reception failed")
                time.sleep(0.5)

                self.add_retx_sum()
                #recursive call until max_retx not reached
                get_packet(packet_count, max_retx - 1)

        packet_count = 0
        self.emulator.rx_buffer.flush()
        self.progress_bar.set_title("receiving...")
        to_signal(self.progress_bar.show)()
        self.progress_bar.set_val_signal.emit(packet_count * 100 / PACKETS_NUM)

        while len(self.bin_receiver) < 0x8000:
            assert packet_count < PACKETS_NUM
            if get_packet(packet_count):
                packet_count += 1
                self.progress_bar.set_val_signal.emit(packet_count * 100 / PACKETS_NUM)
        self.gui_communication_signal.emit("SRAM read done in {:.2f}".format(time.time() - t0))
        self.disp_retx_count()
        tear_down()
