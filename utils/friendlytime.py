import re
import datetime
from dateutil.relativedelta import relativedelta
import pytz

def time_formatter(time_str: str) -> datetime.datetime:
    units = {
        'years': 'years?|y(?:ears?)?|y(?:ear)?|y|y(?:rs?)?|y(?:r)?|y|yrs?|yr|y',
        'months': 'months?|m(?:onths?)?|m(?:onth)?|m|m(?:ths?)?|m(?:th)?|m|mths?|mth|m',
        'weeks': 'weeks?|w(?:eeks?)?|w(?:eek)?|w|w(?:ks?)?|w(?:k)?|w',
        'days': 'days?|d(?:ays?)?|d(?:ay)?|d|days?|day|d|days?|day|d|da?|d',
        'hours': 'hours?|hr?s?|h|hrs?|h(?:rs?)?|h(?:r)?|h',
        'minutes': 'minutes?|m(?:inutes?)?|m(?:inute)?|m|m(?:ins?)?|m(?:in)?|m|mi?|minu?|mins?|m|minu?|mins?|min',
        'seconds': 'seconds?|s(?:ecs?)?|s(?:ec)?|s|s(?:ecs?)?|s(?:ec)?|s|secs?|sec|s|secs?|sec|s'
    }

    patterns = []
    for unit, pattern in units.items():
        patterns.append(fr"(?:(?P<{unit}>\d+)\s*(?:{pattern})(?=\s+|$))")

    compiled = re.compile('|'.join(patterns))

    match = compiled.match(time_str)
    if match:
        time_units = {k: int(v) for k, v in match.groupdict().items() if v}
        time_delta = relativedelta(**time_units)
        current_time = datetime.datetime.now(tz=datetime.timezone.utc)
        future_time = current_time + time_delta
        return future_time
    else:
        raise ValueError('Invalid time format provided')

def format_datetime_human_readable(dt: datetime.datetime) -> str:
    dt = dt.astimezone(pytz.timezone('Asia/Kolkata'))
    return dt.strftime('%d-%m-%Y at %I:%M %p')
