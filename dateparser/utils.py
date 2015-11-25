# -*- coding: utf-8 -*-
import re
import logging
import logging.config
from functools import wraps

from dateutil.parser import parser


GROUPS_REGEX = re.compile(r'(?<=\\)(\d+|g<\d+>)')
G_REGEX = re.compile(r'g<(\d+)>')


def strip_braces(date_string):
    return re.sub(r'[{}()<>\[\]]+', '', date_string)


def is_dateutil_result_obj_parsed(date_string):
    res = parser()._parse(date_string)
    if not res:
        return False
    
    def get_value(obj, key):
        value = getattr(obj, key)
        return str(value) if value is not None else ''

    return any([get_value(res, k) for k in res.__slots__])


def wrap_replacement_for_regex(replacement, regex):
    # prepend group to replacement
    replacement = r"\g<1>%s" % increase_regex_replacements_group_positions(replacement, increment=1)

    # append group to replacement
    used_groups = re.compile(regex).groups
    new_group = used_groups + 2  # Consider that we already prepended replacement with one group
    replacement = "%s\\g<%d>" % (replacement, new_group)

    return replacement


def increase_regex_replacements_group_positions(replacement, increment):
    splitted = GROUPS_REGEX.split(replacement)
    for i in range(1, len(splitted), 2):
        group = splitted[i]
        if group.isdigit():
            splitted[i] = str(int(group) + increment)
        else:
            splitted[i] = "g<{}>".format(int(G_REGEX.match(group).group(1)) + increment)
    return u"".join(splitted)


def setup_logging():
    if len(logging.root.handlers):
        return

    config = {
        'version': 1,
        'disable_existing_loggers': True,
        'formatters': {
            'console': {
                'format': "%(asctime)s %(levelname)s: [%(name)s] %(message)s",
            },
        },
        'handlers': {
            'console': {
                'level': logging.DEBUG,
                'class': "logging.StreamHandler",
                'formatter': "console",
                'stream': "ext://sys.stdout",
            },
        },
        'root': {
            'level': logging.DEBUG,
            'handlers': ["console"],
        },
    }
    logging.config.dictConfig(config)


def get_logger():
    setup_logging()
    return logging.getLogger('dateparser')


def find_date_separator(format):
    m = re.search(r'(?:(?:%[dbBmaA])(\W))+', format)
    if m:
        return m.group(1)


class Registry(object):

    _global_dict = {}
    _tag = 'from_registry'

    def __new__(cls, *args, **kwargs):
        key = cls.get_key(*args, **kwargs)

        if key in cls._global_dict:
            return cls._tag_instance(cls._global_dict[key])

        return cls._global_dict.setdefault(
            key,
            object.__new__(cls, *args, **kwargs)
        )

    @classmethod
    def _tag_instance(cls, instance):
        setattr(instance, cls._tag, True)
        return instance

    @classmethod
    def get_key(cls, *args, **kwargs):
        raise NotImplemented

    @classmethod
    def skip_init_if_instance_from_registry(cls, f):
        @wraps(f)
        def wrapper(self, *args, **kwargs):
            if not getattr(self, cls._tag, False):
                return f(self, *args, **kwargs)
        return wrapper
