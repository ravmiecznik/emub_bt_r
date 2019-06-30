"""
author: Rafal Miecznik
contact: ravmiecznk@gmail.com
"""

import configparser
from main_logger import info, warn, debug, error, create_logger
import bluetooth
from circ_io_buffer import CircIoBuffer
import time

rx_logger = create_logger('rx_data')
rx_debug = rx_logger.debug

class Emulator():
    def __init__(self, port, address, event_handler=None, timeout=1):
        debug("Init of {}".format(Emulator.__name__))
        self.__lock = False
        self.connected = False
        self.event_handler = event_handler
        self.emu_timeout = timeout

        self.port = port
        self.address = address
        self.rx_buffer = CircIoBuffer(byte_size=256*16)
        self.raw_buffer = CircIoBuffer(byte_size=256 * 8 + 2)

    def lock(self):
        #get remaining data first
        time.sleep(self.emu_timeout)
        if self.rx_buffer.available():
            self.event_handler.get_emu_rx_buffer_slot()
        self.__lock = True

    def is_locked(self):
        return self.__lock

    def unlock(self):
        info("Unlock emu buffer")
        self.__lock = False

    def receive_data_amount(self, amount=1, timeout=2, rcv_ready_signal=None, failed_signal=None, period=0.5, unlock_emu=True):
        if not rcv_ready_signal:
            rcv_ready_signal = self.event_handler.get_emu_rx_buffer_slot()
        tstamp = time.time()
        while self.rx_buffer.available() < amount:
            time.sleep(period)
            if time.time() - tstamp > timeout:
                if failed_signal:
                    failed_signal()
                return False
        rcv_ready_signal()
        return True

    def set_event_handler(self, event_handler):
        self.event_handler = event_handler

    def connect(self, port, address):
        self.address = address
        self.port = port
        if not self.connected:
            self._connect()
        else:
            self.event_handler.message("Already connected")

    def disconnect(self):
        try:
            if self.bt_connection:
                self.bt_connection.close()
                self.bt_connection = False
                self.connected = False
                self.event_handler.message("disconnected from emu device")
        except AttributeError as A:
            if A.message != "Emulator instance has no attribute 'bt_connection'":
                raise AttributeError(A)

    def _connect(self):
        msg = "Connecting to bt device addr: {}, port: {}".format(self.address, self.port)
        self.event_handler.message(msg)
        try_num = 0
        num_of_tries = 3
        while try_num < num_of_tries:
            try:
                emu = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
                emu.connect((self.address, int(self.port)))
                self.bt_connection = emu
                emu.settimeout(self.emu_timeout)
                self.event_handler.message("connected to emu device")
                self.connected = True
                return
            except (bluetooth.btcommon.BluetoothError, IOError) as err:
                try_num += 1
                self.event_handler.message(err)
                self.event_handler.message("Connection fail. Try: {}".format(try_num))
        self.event_handler.message("Could not connect")

    def get_connection_status(self):
        return self.connected

    def __try_get_data(self):
        try:
            rcv = self.bt_connection.recv(100)
            rx_debug("Received data amount: {}".format(len(rcv)))
            rx_debug("rcv: {} ..".format(rcv[0:50]))
            return rcv
        except (bluetooth.btcommon.BluetoothError, IOError):
            #Linux and Windows support different exceptions here
            return None

    def receive_data(self):
        """
        :param rx_buffer:
        :param rx_buffer_ready_slot:
        :return:
        """

        tmp_buff = self.__try_get_data()
        if tmp_buff:
            self.rx_buffer.write(tmp_buff)
            self.raw_buffer.write(tmp_buff)
        while tmp_buff:
            tmp_buff = self.__try_get_data()
            if tmp_buff:
                self.rx_buffer.write(tmp_buff)
                self.raw_buffer.write(tmp_buff)
        if self.rx_buffer.available():
            self.event_handler.get_emu_rx_buffer_slot()
        if self.raw_buffer.available():
            self.event_handler.get_raw_rx_buffer_slot()


    def send(self, data):
        if not self.__lock:
            if self.bt_connection:
                try:
                    self.bt_connection.send(data)
                except bluetooth.btcommon.BluetoothError:
                    error("LOST BT CONNECTION")
                    self.event_handler.lost_connection_slot()
            else:
                error("No bt_connection established")
        else:
            debug("Trying send: '{}', but emulator locked".format(data))

