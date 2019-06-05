
import struct
def crc(buffer):
    crc = 0
    for i in buffer:
        crc = crc_xmodem(crc, struct.unpack('b',i)[0])
    return struct.pack('H', crc)

def unpack_crc(crc):
    return struct.unpack('H', crc)[0]

def crc_xmodem(crc, data):
    crc = 0xffff&(crc ^ (data << 8))
    for i in range(0, 8):
        if crc & 0x8000:
            crc = 0xffff&((crc << 1) ^ 0x1021)
        else:
            crc = (0xffff&(crc<<1))
    return crc
