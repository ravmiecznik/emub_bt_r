"""
author: Rafal Miecznik
contact: ravmiecznk@gmail.com
"""

import configparser
from setup_emubt import info, warn, debug, error, create_logger, LOG_PATH
import bluetooth
from auxiliary_module import MeanCalculator
from circ_io_buffer import CircIoBuffer
import time, os

rx_logger = create_logger('rx_data', log_path=LOG_PATH)
rx_debug = rx_logger.debug


class Emulator():
    def __init__(self, port, address, event_handler=None, timeout=1, rcv_chunk_size=256):
        debug("Init of {}".format(Emulator.__name__))
        #TODO: add procedure in main window to estiamte best rcv_chunksize in loop
        self.__rcv_chunk_size = rcv_chunk_size
        self.__lock = False
        self.connected = False
        self.event_handler = event_handler
        self.emu_timeout = timeout

        self.port = port
        self.address = address
        self.init_rxbuffers()
        #self.__dump_file = open(os.path.join(LOG_PATH, 'rx_dump.dmp'), 'w')


    def set_rcv_chunk_size(self, value):
        self.__rcv_chunk_size = value

    def get_rcv_chunk_size(self):
        return self.__rcv_chunk_size

    def init_rxbuffers(self):
        self.raw_buffer = CircIoBuffer(byte_size=256 * 16 + 2)

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
                #emu.connect((self.address, int(self.port)))
                emu.connect((self.address, int(self.port)))
                self.bt_connection = emu
                #emu.settimeout((float(self.__rcv_chunk_size) * 9)/115200)
                emu.settimeout(0)
                self.event_handler.message("connected to emu device")
                self.connected = True
                return
            except (bluetooth.btcommon.BluetoothError, IOError) as err:
                try_num += 1
                self.event_handler.message(err)
                self.event_handler.message("Connection fail. Try: {}".format(try_num))
        self.event_handler.message("Could not connect")


    def set_timeout(self, value):
        self.bt_connection.settimeout(value)

    def get_connection_status(self):
        return self.connected

    def flush(self):
        #self.bt_connection.recv(256*16)
        self.raw_buffer.flush()
        self.rx_buffer.flush()

    def __try_get_data(self):
        try:
            rcv = self.bt_connection.recv(self.__rcv_chunk_size)
            rx_debug("Received data amount: {}".format(len(rcv)))
            rx_debug("rcv: {} ..".format(rcv[0:50]))
            #self.__dump_file.write(rcv)
            return rcv
        except (bluetooth.btcommon.BluetoothError, IOError) as e:
            #Linux and Windows support different exceptions here
            #print e
            return None

    def __get_data(self):
        try:
            rx_data = self.bt_connection.recv(self.__rcv_chunk_size)
            rx_debug("Received data amount: {}".format(len(rx_data)))
            rx_debug("rcv: {} ..".format(rx_data[0:50]))
            return rx_data
        except (bluetooth.btcommon.BluetoothError, IOError) as e:
            pass

    def receive_data(self):
        """
        :param rx_buffer:
        :param rx_buffer_ready_slot:
        :return:
        """
        rx_data = self.__get_data()
        while rx_data:
            self.raw_buffer.write(rx_data)
            rx_data = self.__get_data()
        if self.raw_buffer.available():
            self.event_handler.get_raw_rx_buffer_slot()

    def send(self, data):
        if not self.__lock:
            if self.bt_connection:
                try:
                    self.bt_connection.send(data)
                except bluetooth.btcommon.BluetoothError as e:
                    error("LOST BT CONNECTION")
                    self.event_handler.lost_connection_slot()
                    raise e
            else:
                error("No bt_connection established")
        else:
            debug("Trying send: '{}', but emulator locked".format(data))

