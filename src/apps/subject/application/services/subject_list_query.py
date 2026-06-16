from django.db.models import Subquery

from apps.subject.infrastructure.repositories.subject_list_query import SubjectListQueryRepository


def build_current_visit_subquery() -> Subquery:
    return SubjectListQueryRepository().build_current_visit_subquery()
