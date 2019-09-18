"""
author: Rafal Miecznik
contact: ravmiecznk@gmail.com

This module handles both message sending and message reception.

RxMessage structure:
 MESSAGE_BODY_BYTES<MSG_TAIL>

Because of Atmega128 limited ram memory there is a message body sent first and it's tail in the end.
Tail acts like a header but attached in msg tail with all information: ID, CONTEXT, LEN, CRC. All those fields
are calculated when each msg byte is transmitted. Using those fileds allows to verify msg integrity and with
given msg len it is possible to extract it from rx buffer


"""

import struct
from datetime import datetime
from crc import crc
from random import randrange
from call_tracker import method_call_track
from auxiliary_module import Uint16
from loggers import create_logger
import time, os
from setup_emubt import LOG_PATH

log_format = '[%(asctime)s]: %(levelname)s method:"%(funcName)s" %(message)s'
logger_name = "message_handler"
m_logger = create_logger(logger_name, log_path=LOG_PATH, format=log_format, log_to_file=True)


MAX_PACKET_SIZE = 256*8 + 20


class MsgLockTimeout(Exception):
    pass

class RxTimeout(Exception):
    pass

class TxTimeout(Exception):
    pass


class TransmissionStats:
    """
    Keeps track of ack/nack ratio
    """
    def __init__(self):
        self.__acks = 0
        self.__nacks = 0

    def ack(self):
        self.__acks += 1

    def nack(self):
        self.__nacks += 1

    def __repr__(self):
        try:
            err_rate = float(self.__nacks)/self.__acks
        except ZeroDivisionError:
            err_rate = 0
        return "acks: {}, nack: {}, err_rate: {}".format(self.__acks, self.__nacks, err_rate)


@method_call_track
class MessageSender:
    """
    static fileds:
        context: to keep track of msg req<->resp mechanism msg context is attached.
                 Thanks to this value it is possible to find right response for given request.
                 There are context ids reserved for particular messages handling:
                 0: free text which should be displayed in console window
                 1: digidiag frame data
                 Message sender cant assign reserved_context id when message is created and sent.
    """

    reserved_context = (
        0,
        1,
    )
    context = Uint16(len(reserved_context)) #start with value greater than reserved_context
    lock = False

    class ID:
        """
        Message IDs reperesenting given procedure in EMU BT board
        """
        txt_message     = 0
        write_to_page   = 1
        rxflush         = 2
        setbankname     = 3
        get_bank_info   = 4
        get_sram_packet = 5
        get_bank_packet = 6
        enable_sram     = 7
        reload_sram     = 8
        send_sram_bytes = 9
        handshake       = 10
        get_write_stats = 11
        bootloader      = 12
        disable_btlrd   = 13

    def __init__(self, tx_interface):
        self.__transmit = tx_interface

    def __send_m(self, msg):
        """
        Send createad message.
         Avoid using recovered context_ids
        """
        context = MessageSender.context
        MessageSender.context += 1
        while MessageSender.context in MessageSender.reserved_context:
            MessageSender.context += 1
        self.__transmit(msg)
        m_logger.debug("Sent message with context: {}".format(context))
        return context


    def send(self, m_id, body='NULL'):
        """
        Polymorphic method for send
        """
        return self.__send(m_id, body)


    def send_raw_msg(self, body):
        """
        Polymorphic method for send
        """
        return self.__send(m_id=None, body=body)


    def __send(self, m_id=None, body='NULL'):
        timeout = 2
        t0 = time.time()
        if MessageSender.lock: m_logger.debug("message sending locked, waiting")
        while MessageSender.lock:
            time.sleep(0.001)
            if time.time() - t0 > timeout:
                m_logger.error("TIMEOUT in wait for unlock")
                raise TxTimeout
        MessageSender.lock = True
        msg = create_message(id=m_id, body=body, context=MessageSender.context) if m_id is not None else body
        context = self.__send_m(msg)
        MessageSender.lock = False
        m_logger.debug("message sending unlocked")
        return context


class RxId(tuple):
    """
    This is auxiliary object which holds rx id value for RxMessage.
    It returns id of ack, nack or dtx but in case of any error
    it return dtx id.
    """
    def __getitem__(self, item):
        try:
            try:
                return tuple.__getitem__(self, item)
            except IndexError as e:
                m_logger.error("{}: {}".format(e, item))
        except TypeError:
            print "Type error"
            return 'dtx'

class RxMessage(object):
    """
    Rx message ids (types)
    enum id{
        ack_feedback,
        nak_feedback,
    };
    """
    rx_id_tuple = ('ack', 'nack', 'dtx')
    rx_id = RxId(rx_id_tuple)
    class CRC_result():
        ack     = 0
        nack    = 1
        dtx     = 2


    def __init__(self, msg_id, context, crc_check, body, length):
        self.__id = msg_id
        self.__context = context
        self.__crc_result = self.__set_result(crc_check)        #crc calculated from msg raceived vs tail crc
        self.__body = self.__set_body(body)
        self.__tstamp = datetime.now().strftime("%H:%M:%S.%s")
        self.__len = length

    def __set_body(self, body):
        try:
            len(body)
            return body
        except TypeError:
            raise Exception("body is not iterable")

    def __set_result(self, result):
        valid_results = [RxMessage.CRC_result.ack, RxMessage.CRC_result.nack, RxMessage.CRC_result.dtx]
        if result not in valid_results:
            raise Exception("Result must be ACK {} | NACK {} | DTX {}".format(*valid_results))
        return result

    @property
    def id(self):
        return self.__id

    @property
    def context(self):
        return self.__context

    @property
    def crc_check(self):
        return ('ack', 'nack', 'dtx')[self.__crc_result]

    @property
    def msg(self):
        return self.__body

    def __repr__(self):
        return "i{}\n" \
               "id:         {m_id}\n" \
               "context:    {context}\n" \
               "crcresult:  {result}\n" \
               "length:     {lenght}\n" \
               "body:      '{body}'\n" \
               "tstamp:     {tstamp}".format(RxMessage,
                                             m_id=RxMessage.rx_id[self.__id],
                                             context=self.__context,
                                             result=['ack', 'nack', 'dtx'][self.__crc_result],
                                             lenght=self.__len,
                                             body=' '.join(self.__body[0:10].split()) + '...',
                                             tstamp=self.__tstamp)

MSG_RX_DBG_TEMPLATE = "\n--------------------\n"\
                      "Message received:\n" \
                      "{}\n" \
                      "--------------------"

class MessageReceiver():
    """"
    Checks given rx buffer if message is present there.
        struct  Tail
        {
            uint8_t     tail_start = TAIL_START_MARK; // '>'
            uint16_t    id = 0;
            uint16_t    context = 0;
            uint16_t    msg_len = 0;
            uint16_t    crc = 0;
            uint8_t     tail_end = TAIL_END_MARK; // '<'
        }
    """
    TAIL_LEN = 10
    TAIL_START_MARK = '<'
    TAIL_END_MARK = '>'
    ts = time.time()
    LOCKED = False
    def __init__(self, rx_buffer):
        self.rx_buffer = rx_buffer

    def check_tail(self, peek_buff):
        peek_buff_len = len(peek_buff)
        init_find = peek_buff.find(MessageReceiver.TAIL_START_MARK)
        for i in xrange(peek_buff_len - MessageReceiver.TAIL_LEN + init_find):
            latest_find = i + init_find
            try:
                tail_start_mark_pos = peek_buff[latest_find:].find(MessageReceiver.TAIL_START_MARK)
                tail_end_mark_pos = tail_start_mark_pos + MessageReceiver.TAIL_LEN - 1
                tail_end_mark = peek_buff[latest_find:][tail_end_mark_pos]
            except IndexError:
                return False
            if tail_end_mark == MessageReceiver.TAIL_END_MARK:
                tail = peek_buff[latest_find:][tail_start_mark_pos + 1: tail_end_mark_pos]
                _id = struct.unpack('H', tail[0:2])[0]
                _context = struct.unpack('H', tail[2:4])[0]
                _msg_len = struct.unpack('H', tail[4:6])[0]
                _crc = tail[6:8]
                if _id < len(RxMessage.rx_id_tuple) and _msg_len < MAX_PACKET_SIZE and _context < 0xffff and self.rx_buffer.available() > _msg_len:
                    return _id, _context, _msg_len, _crc, tail_start_mark_pos + latest_find, tail_end_mark_pos + latest_find
        return False

    def get_message(self):
        t0 = time.time()
        if not MessageReceiver.LOCKED and (self.rx_buffer.available() >= MessageReceiver.TAIL_LEN):
            MessageReceiver.LOCKED = True
            peek_buff = self.rx_buffer.peek()
            try:
                _check_tail = self.check_tail(peek_buff)
                if _check_tail:
                    _id, _context, _msg_len, _crc, tail_start_mark_pos, tail_end_mark_pos = _check_tail

                    msg_body = self.rx_buffer.read(tail_end_mark_pos + 1)[tail_start_mark_pos-_msg_len:tail_start_mark_pos]
                    MessageReceiver.ts = time.time()
                    crc_check = RxMessage.CRC_result.ack if _crc == crc(msg_body) else RxMessage.CRC_result.nack
                    rxmsg = RxMessage(msg_id=_id, crc_check=crc_check, length=len(msg_body), context=_context, body=msg_body)
                    m_logger.debug(MSG_RX_DBG_TEMPLATE.format(rxmsg))
                    MessageReceiver.LOCKED = False
                    if _crc == crc(msg_body):
                        m_logger.debug("Message got in: {}".format(time.time() - t0))
                        return rxmsg
            except ValueError as e:
                print e
                m_logger.error(e)
        MessageReceiver.LOCKED = False


def create_message(id, body, context=0, max_packet_size=MAX_PACKET_SIZE, fail_crc_factor=None):
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
    context = struct.pack('H', context)  # two bytes
    c = crc(body)                                   #two bytes field
    if fail_crc_factor:
        if randrange(0, fail_crc_factor) == 0:
            c1 = c[0]
            c2 = chr(ord(c[1]) + 1) if ord(c[1]) <= 0xff else chr(ord(c[1]) - 1)
            c = c1 + c2
    return '>{id}{context}{body_len}{crc}<{body}'.format(id=id, context=context, body_len=body_len, crc=c, body=body)

if __name__ == "__main__":
    rm = RxMessage(1, 2, 3, 'rafal')
    print rm