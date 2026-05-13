
from django.apps import apps


def get_subject_list_row_model():
    return apps.get_model("subject", "Subject")
