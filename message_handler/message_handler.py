"""
author: Rafal Miecznik
contact: ravmiecznk@gmail.com
"""

from my_gui_thread import GuiThread
import struct
from crc import crc,unpack_crc
from my_gui_thread import GuiThread
from main_logger import info, debug, error, warn
import time
import abc
from event_handler import to_signal
from random import randrange

class MsgLockTimeout(Exception):
    pass

def default_handler(resp, req):
    def log():
        debug("{} received on req: {}".format(resp, req))
    return log

def default_abstract_method_exception(cls, method, method_type='static'):
    """
    method type: static or bound
    :param cls:
    :param method:
    :param method_type:
    :return:
    """
    def raise_exception():
        raise Exception("{}: {} method '{}' not implemented".format(cls, method.__name__, method_type))
    return raise_exception

class Message():
    class ID:
        txt_message     = 0
        write_to_page   = 1
        rxflush         = 2
        setbankname     = 3
        get_bank_info   = 4
    @staticmethod
    def send(msg):
        raise Exception("{}: static method '{}' not implemented".format(Message, Message.send.__name__))

    @staticmethod
    def flush_rx_buffer():
        raise Exception("{}: static method '{}' not implemented".format(Message, Message.flush_rx_buffer.__name__))

    @staticmethod
    def get_rx_buffer():
        return default_abstract_method_exception(Message, Message.get_rx_buffer)()

    @staticmethod
    def default_ack_handler():
        return default_abstract_method_exception(Message, Message.default_ack_handler)()

    lock = False
    default_negative_signal = lambda : None

    def __init__(self, raw_msg='', resp_positive='ack', resp_negative='nak', resp_dtx='dtx', positive_signal=None,
                 negative_signal=None, create_header=True, timeout=2, max_retx=5, id=0, fail_crc_factor=None,
                 extra_action_on_nack=lambda: None, extra_action_on_ack=lambda: None):
        #self.msg = create_message(id=id, body=raw_msg, fail_crc_factor=fail_crc_factor) if create_header else raw_msg
        self.create_header = create_header
        self.fail_crc_factor = fail_crc_factor
        self.raw_msg = raw_msg
        self.id = id
        self.resp_positive = resp_positive
        self.resp_negative = resp_negative
        self.resp_dtx = resp_dtx
        self.timeout = timeout
        self.expected_resp_len = len(resp_positive)
        self.max_retx = max_retx
        self.resp = 'NO RESP'
        self.catch_response_thrd = self.catch_response()
        self.extra_action_on_nack = extra_action_on_nack
        self.extra_action_on_ack = extra_action_on_ack
        #negative signal called when max_retx exceeded
        self.negative_signal = Message.default_negative_signal if negative_signal is None else negative_signal

        #self.positive_handler = positive_signal if positive_signal else Message.default_ack_handler
        #self.negative_handler = self.default_nak_dtx_handler
        self.__positive_signal = positive_signal

        self.actions = {
            self.resp_positive: self.positive_handler,
            self.resp_negative: self.nak_dtx_handler,
            self.resp_dtx: self.nak_dtx_handler
        }
        self.__send()

    def positive_handler(self):
        Message.lock = False
        self.extra_action_on_ack()
        if self.__positive_signal:
            self.__positive_signal()
        else:
            self.default_ack_handler()

    def __wait_for_unlock(self):
        t0 = time.time()
        if Message.lock:
            debug("wait for message sender unlock")
        while Message.lock:
            time.sleep(0.001)
            if time.time() - t0 > self.timeout:
                raise MsgLockTimeout("Timeout in msg lock")

    def nak_dtx_handler(self):
        """
        implement retx protocol here
        :return:
        """
        self.extra_action_on_nack()
        Message.flush_rx_buffer()
        if self.max_retx:
            warn("'{resp}' received on reg: '{req} id: {id}...' Trying retx {retx}...".format(resp=self.resp, req=self.raw_msg[0:40], id=self.id, retx=self.max_retx))
            self.__resend()
            self.max_retx -= 1
        else:
            Message.lock = False
            error("{req}... !!! send failed !!!".format(req=self.raw_msg[0:40]))
            try:
                self.negative_signal()
            except TypeError:
                self.negative_signal(self)


    def __send(self):
        try:
            self.__wait_for_unlock()
        except MsgLockTimeout as e:
            error("Timeout for: {}".format(self.raw_msg[0:40]))

            error(e.message)
            try:
                self.negative_signal(self)
            except TypeError:
                self.negative_signal()
                return False
        Message.lock = True
        Message.flush_rx_buffer()
        self.catch_response().start()
        debug("Send msg {}".format(self.raw_msg[0:20]))
        msg = create_message(id=self.id, body=self.raw_msg,
                             fail_crc_factor=self.fail_crc_factor) if self.create_header else self.raw_msg
        Message.send(msg)

    def __resend(self):
        Message.flush_rx_buffer()
        self.catch_response().start()
        debug("resend msg {}".format(self.raw_msg[0:20]))
        msg = create_message(id=self.id, body=self.raw_msg,
                             fail_crc_factor=self.fail_crc_factor) if self.create_header else self.raw_msg
        Message.send(msg)

    def unrecognized_resp_handler(self):
        error("Unhandable resp: '{}' on req: '{}...' Flushing rx buffer".format(self.resp + Message.rx_buffer.read(), self.raw_msg[0:40]))
        error(Message.rx_buffer.read())
        Message.flush_rx_buffer()
        self.nak_dtx_handler()

    def handle_resp(self):
        try:
            action = self.actions[self.resp]
            action()
        except KeyError:
            self.unrecognized_resp_handler()

    def catch_response(self):
            def wait_for_msg():
                t0 = time.time()
                while Message.rx_buffer.available() < self.expected_resp_len:
                    time.sleep(0.001)
                    if time.time() - t0 > self.timeout:
                        self.resp ='dtx'
                        return False
                self.resp = Message.rx_buffer.read(self.expected_resp_len)
            return GuiThread(wait_for_msg, action_when_done=to_signal(self.handle_resp), alias=self.raw_msg[0:20])

    # def catch_response(self):
    #     def wait_for_msg():
    #         t0 = time.time()
    #         while Message.rx_buffer.available() < self.expected_resp_len:
    #             time.sleep(0.001)
    #             if time.time() - t0 > self.timeout:
    #                 self.dtx_handler()
    #                 return False
    #         self.resp = Message.rx_buffer.read(self.expected_resp_len)
    #         try:
    #             print "call action on resp for id {}: {}".format(self.id, self.resp)
    #             self.actions[self.resp]()
    #         except KeyError:
    #             self.unrecognized_resp_handler()
    #     return GuiThread(wait_for_msg, action_when_done=to_signal(self.unlock_msg_send))


class MessageHandler():
    def __init__(self, serial_connection, event_handler, ):
        self.serial_connetion = serial_connection
        self.event_handler = event_handler
        self.rx_buffer = self.serial_connetion.rx_buffer
        self.event_handler.add_event(to_signal(lambda: None), 'get_emu_rx_buffer_slot')  #by default do nothing on get_emu_rx_buffer_signal
        self.console = self.event_handler.message

        #setup general Message attrs
        Message.rx_buffer = self.rx_buffer
        Message.send = self.serial_connetion.send
        Message.flush_rx_buffer = self.serial_connetion.rx_buffer.flush
        Message.default_ack_handler = self.print_rx_buffer
        Message.get_rx_buffer = self.get_rx_buffer

    def print_rx_buffer(self):
        """
        Overwrites get_emu_rx_buffer_slot in event handler
        :return:
        """
        self.event_handler.add_event(to_signal(self.print_rx_buffer_to_console), 'get_emu_rx_buffer_slot')

    def get_rx_buffer(self):
        time.sleep(0.5)
        return self.rx_buffer.read()

    def just_print(self):
        print self.rx_buffer.read()

    def send(self, message):
        return Message(message)  #, positive_signal=self.print_rx_buffer)()

    def print_rx_buffer_to_console(self):
        """
        This can be connected to get_emu_rx_buffer_slot in event handler to received random data and display
        in console window
        :return:
        """
        self.console("{s}EMU{s}".format(s=14*'-'))
        time.sleep(0.1)
        emu_buffer = ''
        tmp = self.serial_connetion.rx_buffer.read()
        while tmp:
            emu_buffer += tmp
            tmp = self.serial_connetion.rx_buffer.read()
            time.sleep(0.1)
        emu_buffer = emu_buffer.split('\n')
        for line in emu_buffer:
            self.console(line)
        self.console("{s}EMU END{s}".format(s=12*'-'))
        self.event_handler.add_event(to_signal(lambda: None),
                                     'get_emu_rx_buffer_slot')  # stop reading rx_buffer on signal


def create_message(id, body,max_packet_size=256*8 + 20, fail_crc_factor=None):
    """
    Create message with name, body_len, crc, id
    fail_crc_factor: propability factor to fail crc, value 4 means that 1 of 4 transmissions will fail crc, overwrites fail_crc
    :param name:
    :param body:
    :param max_packet_size:
    :return:
    """
    body_len = len(body)                            #integer type, 4 bytes long
    header_size = 10
    if body_len + header_size > max_packet_size:
        raise Exception("msg len to big: {}>{}".format(body_len + header_size, max_packet_size))
    body_len = struct.pack('I', body_len)
    id = struct.pack('H', id)                       #two bytes
    c = crc(body)                         #two bytes field
    if fail_crc_factor:
        if randrange(0, fail_crc_factor) == 0:
            c1 = c[0]
            c2 = chr(ord(c[1]) + 1) if ord(c[1]) < 256 else chr(ord(c[1]) - 1)
            c = c1 + c2
    return '>{id}{body_len}{crc}<{body}'.format(body_len=body_len, body=body, crc=c, id=id)

if __name__ == "__main__":
    print create_message('tmp', '123')