"""
author: Rafal Miecznik
contact: ravmiecznk@gmail.com
"""

#from call_tracker import method_call_track
#from setup_emubt import warn, info, error, debug
from loggers import create_logger
import setup_emubt

DBG = False

logger_name = "event_handler"
evh_logger = setup_emubt.create_logger(logger_name, log_path=setup_emubt.EMU_BT_PATH)
error = evh_logger.error
debug = evh_logger.debug

class EventHandler(object):

    def not_implemented_attribute(self, attr):
        def print_attr(*args, **kwargs):
            error("{}: {}: not implemented\n {} {}".format(self.__class__, attr, args, kwargs))
            debug(self.__dict__)
        return print_attr


    def add_event(self, event, name=''):
        name = name if name else event.__name__
        setattr(self, name, event)

    def __getattr__(self, item):
        return self.not_implemented_attribute(item)

    def __getattribute__(self, item):
        evh_logger.debug(item)
        return object.__getattribute__(self, item)


logger_name = "signal_calls"
signal_logger = setup_emubt.create_logger(logger_name, log_path=setup_emubt.EMU_BT_PATH)

def general_signal_factory(slot):
    """
    This functions will create a signal with slot argument
    :param signal:
    :param slot:
    :return:
    """
    def wrapper(*args):
        try:
            dbg_msg = "emit signal: name:{} id:{}".format(slot.__name__, slot)
            signal_logger.debug(dbg_msg)
            return general_signal_factory.signal.emit(slot, (), {})
        except AttributeError as e:
            raise Exception("{factory}: missing signal attribute. Set it up with {factory}.signal={slot}".format(factory=general_signal_factory.__name__, slot=slot))
    wrapper.__name__ = slot.__name__
    wrapper.emit = wrapper.__call__
    return wrapper


to_signal = general_signal_factory