"""
author: Rafal Miecznik
contact: ravmiecznk@gmail.com
"""

import main_logger
import types

ENABLE_TRACKING = True

log_format = '[%(asctime)s]: %(levelname)s %(message)s'
logger_name = "call_tracker"

logger = main_logger.create_logger(logger_name, log_format, log_to_file=True)

info = logger.info
debug = logger.debug
error = logger.error
warn = logger.warn

def cut_args(a, size=100):
    """
    If argument is too long it will limit its output
    :param a:
    :param size:
    :return:
    """
    s = str(a)
    if len(s) > size:
        return s[0:size] + '...'
    return s

#-----------------------NEW APPROACH-----------------------#

def method_call_track(class_obj):
    def getattribute(self, item):
        info("")
        info("get attribute: {}.{}".format(self, item))
        attr = object.__getattribute__(self, item)
        try:
            attr_name = attr.__name__
        except AttributeError:
            attr_name = repr(attr)
        class _wrapper(object):
            def __call__(self, *args, **kwargs):
                _args, _kwargs = cut_args(args), cut_args(kwargs)
                info("{} called with: args: {}, kwargs: {}".format(attr, _args, _kwargs))
                to_return = attr(*args, **kwargs)
                info("{} returns: {}".format(attr_name, cut_args(to_return)))
                return to_return

            def __getattr__(self, item):
                """
                Call this method if attr of class_obj has its own attribute
                :param item:
                :return:
                """
                info("{} get sub-attribute {}".format(attr_name, item))
                return getattr(attr, item)

        if callable(attr):
            return _wrapper()
        else:
            return attr
    if ENABLE_TRACKING:
        class_obj.__getattribute__ = getattribute
    return class_obj


#-----------------------OLD APPROACH-----------------------#
def track_call(method, class_name=None):
    if ENABLE_TRACKING:
        try:
            method_name = method.__name__
        except AttributeError:
            method_name = str(method)
        info("Adding to tracker: method {}".format(method_name))
        def track_wrapper(*args, **kwargs):
            call_name = "{}.{}".format(class_name, method_name) if class_name else method_name
            _args, _kwargs = cut_args(args), cut_args(kwargs)
            info("Call {} with args: {}, kwargs {}".format(call_name, _args, _kwargs))
            result = method(*args, **kwargs)
            info("{} returns: {}\n".format(call_name, cut_args(result)))
            return result
        track_wrapper.__name__ = method_name
        return track_wrapper
    else:
        return method
#
# def check_for_static_methods(class_object):
#     static_methods = []
#     for attr in class_object.__dict__:
#         if attr == 'suspend_all_threads':
#             print type(class_object.__dict__[attr])
#         if type(class_object.__dict__[attr]) == staticmethod:
#             print attr
#             static_methods.append(attr)
#     return static_methods
#
def track_all_class_methods_calls_generic(get_namspace):
    def wrapper(class_obj):
        if ENABLE_TRACKING:
            class_name = class_obj.__name__
            info("Adding to tracker: class {}".format(class_name))
            attrs = get_namspace(class_obj)
            for attr in attrs:
                attr_type = type(getattr(class_obj, attr))
                if (attr not in ['__new__', '__class__']) and (attr_type in [types.MethodType, types.FunctionType, types.MethodType, types.BuiltinMethodType, types.BuiltinFunctionType, "<type 'wrapper_descriptor'>"]):
                    method = track_call(getattr(class_obj, attr), class_name)
                    if attr_type:
                        setattr(class_obj, attr, method)
            return class_obj
        else:
            return class_obj
    return wrapper


def getattribute(obj, item):
    typ = type(object.__getattribute__(obj, item))
    def call_track(method):
        def wrapper(*args, **kwargs):
            info("Call: {} with args: {}, kwargs: {}".format(item, args, kwargs))
            return method(*args, **kwargs)
        return wrapper
    if typ is types.FunctionType:
        setattr(obj, item, call_track(object.__getattribute__(obj, item)))

    #elif callable(object.__getattribute__(obj, item)):
    #    info("Other type: {}:{}".format(item, object.__getattribute__(obj, item).__name__))
    return object.__getattribute__(obj, item)


def next_call_tracker(class_obj):
    # info("Wrapping: {}".format(class_obj))
    # for key in class_obj.__dict__:
    #     attr = class_obj.__dict__[key]
    #     typ = type(attr)
    #     info("{}: {}".format(key, typ))
    #     if typ is types.FunctionType:
    #         info("FunctionType: {}".format(key))
    #     elif str(typ) == "<type 'staticmethod'>":
    #         info("StaticMethod: {}".format(key))
    class_obj.__getattribute__ = getattribute
    return class_obj

#shallow_track_class_calls = CallTrack
#shallow_track_class_calls = track_all_class_methods_calls_generic(lambda obj: getattr(obj, '__dict__'))
shallow_track_class_calls = next_call_tracker
method_call_track = next_call_tracker
#deep_track_class_calls = track_all_class_methods_calls_generic(lambda obj: dir(obj))

if not ENABLE_TRACKING:
    logger.warn("Tracking disabled")
    logger.warn("Check {}".format(__file__))

logger.info("{p}{name}{p}".format(p=30*'*', name=__file__))

if __name__ == "__main__":
    pass