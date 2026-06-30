import inspect

from django.test import SimpleTestCase

from apps.subject.infrastructure.repositories.subject_list_query import SubjectListQueryRepository


class SubjectListQueryRepositoryTests(SimpleTestCase):
    def test_current_visit_subquery_orders_by_oldest_visit_id(self):
        source = inspect.getsource(SubjectListQueryRepository.build_current_visit_subquery)

        self.assertIn('.order_by("id")', source)
