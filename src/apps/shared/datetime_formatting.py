from datetime import datetime

from django.utils import timezone
from django.utils.formats import date_format as django_date_format


def localize_datetime(value):
    if isinstance(value, datetime) and timezone.is_aware(value):
        return timezone.localtime(value)
    return value


def date_format(value, format_name):
    return django_date_format(localize_datetime(value), format_name)


__all__ = ["date_format", "localize_datetime"]
