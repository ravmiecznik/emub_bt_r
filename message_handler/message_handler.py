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
        txt_message = 0
        write_to_page = 1
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

    def __init__(self, raw_msg, resp_positive='ack', resp_negative='nak', resp_dtx='dtx', positive_signal=None,
                 negative_signal=None, dtx_signal=None, create_header=True, timeout=1, max_retx=5, id=0):
        self.msg = create_message(id=id, body=raw_msg) if create_header else raw_msg
        self.raw_msg = raw_msg
        self.resp_positive = resp_positive
        self.resp_negative = resp_negative
        self.resp_dtx = resp_dtx
        self.timeout = timeout
        self.expected_resp_len = len(resp_positive)
        self.max_retx = max_retx
        self.resp = 'NO RESP'
        self.catch_response_thrd = self.catch_response()
        self.negative_signal = Message.default_negative_signal if negative_signal is None else negative_signal

        self.positive_handler = positive_signal if positive_signal else Message.default_ack_handler
        self.negative_handler = self.default_ack_handler
        self.dtx_handler = dtx_signal if dtx_signal else self.default_nak_dtx_handler

        self.actions = {
            self.resp_positive: self.positive_handler,
            self.resp_negative: self.default_nak_dtx_handler,
            self.resp_dtx: self.default_nak_dtx_handler
        }
        #if not Message.lock:
        #self.__wait_for_unlock()
        if not Message.lock:
            self.__send()
        #else:
        #    warn("Previous job not finished, can't send new msg.")

    def __wait_for_unlock(self):
        t0 = time.time()
        if Message.lock:
            debug("wait for message sender unlock")
        while Message.lock:
            time.sleep(0.001)
            if time.time() - t0 > self.timeout:
                raise Exception("Timeout")

    def default_nak_dtx_handler(self):
        """
        implement retx protocol here
        :return:
        """
        Message.flush_rx_buffer()
        if self.max_retx:
            #time.sleep(0.5)
            warn("'{resp}' received on reg: '{req}...' Trying retx {retx}...".format(resp=self.resp, req=self.raw_msg[0:40], retx=self.max_retx))
            self.__send()
            self.max_retx -= 1
        else:
            error("{req}... !!! send failed !!!".format(req=self.raw_msg[0:40]))
            try:
                self.negative_signal(self)
            except TypeError:
                self.negative_signal()

    def unlock_msg_send(self):
        Message.lock = False

    def __send(self):
        Message.lock = True
        Message.flush_rx_buffer()
        self.catch_response().start()
        debug("Send msg {}".format(self.raw_msg[0:20]))
        Message.send(self.msg)
        # i = 0
        # split = 10
        # tmp = self.msg[i:i+split]
        # while tmp:
        #     Message.send(tmp)
        #     i += split
        #     tmp = self.msg[i:i + split]
        #     #time.sleep(0.001)

    def unrecognized_resp_handler(self):
        error("Unhandable resp: '{}' on req: '{}...' Flushing rx buffer".format(self.resp + Message.rx_buffer.read(), self.raw_msg[0:40]))
        error(Message.rx_buffer.read())
        Message.flush_rx_buffer()
        self.dtx_handler()

    def catch_response(self):
        def wait_for_msg():
            t0 = time.time()
            while Message.rx_buffer.available() < self.expected_resp_len:
                time.sleep(0.001)
                if time.time() - t0 > self.timeout:
                    self.dtx_handler()
                    return False
            self.resp = Message.rx_buffer.read(self.expected_resp_len)
            try:
                self.actions[self.resp]()
            except KeyError:
                self.unrecognized_resp_handler()
        return GuiThread(wait_for_msg, action_when_done=to_signal(self.unlock_msg_send))


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


def create_message(id, body,max_packet_size=256*8 + 20):
    """
    Create message with name, body_len, crc, id

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
    return '>{id}{body_len}{crc}<{body}'.format(body_len=body_len, body=body, crc=c, id=id)

if __name__ == "__main__":
    print create_message('tmp', '123')