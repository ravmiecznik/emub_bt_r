"""
author: Rafal Miecznik
contact: ravmiecznk@gmail.com
"""

from call_tracker import method_call_track
from main_logger import warn, info, error

#@shallow_track_class_calls
class EventHandler(object):

    def not_implemented_attribute(self, attr):
        def print_attr(*args, **kwargs):
            error("{}: {}: not implemented\n {} {}".format(self.__class__, attr, args, kwargs))
            warn(self.__dict__)
        return print_attr


    def add_event(self, event, name=''):
        #print "event:{}  name:{}  t_event: {}  t_name: {}".format(event, name, type(event), type(name))
        name = name if name else event.__name__
        #print "event:{}  name:{}  t_event: {}  t_name: {}".format(event, name, type(event), type(name))
        setattr(self, name, event)

    def __getattr__(self, item):
            return self.not_implemented_attribute(item)

#@shallow_track_class_calls
def general_signal_factory(slot):
    """
    This functions will create a signal with slot argument
    :param signal:
    :param slot:
    :return:
    """
    def wrapper():
        try:
            return general_signal_factory.signal.emit(slot)
        except AttributeError:
            raise Exception("{factory}: missing signal attribute. Set it up with {factory}.signal=some_signal".format(factory=general_signal_factory.__name__))
    wrapper.__name__ = slot.__name__
    return wrapper

to_signal = general_signal_factory