import bluetooth
import time

class DiscoverLog(object):

    def communicate(self, string):
        print "disc: {}".format(string)

    def discovery_success(self):
        print "discovery success"

def bt_search(device='BT_EEPROM_EMULATOR', event_handler=DiscoverLog):
    communicate = event_handler.communicate
    success_signal = event_handler.update_config_file
    timeout = 20
    device_name = ''
    t0 = time.time()
    while device_name != device:
        if time.time() - t0 > timeout:
            communicate("Disvovery timeout")
            return None, None
        communicate('discovering {}'.format(device))
        devices = bluetooth.discover_devices(lookup_names=True)
        for x in devices:
            device_name = x[1]
            device_address = x[0]
            communicate("Discovered device: {}".format(device_name))
            communicate(x)
            if device_name == device:
                if success_signal:
                    communicate("Discovery success")
                    success_signal(dict(bt_device_port='1', bt_device_address=device_address))
                return device_name, device_address
