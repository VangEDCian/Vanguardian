from abc import ABC, abstractmethod


class FormBuilderCommandRepository(ABC):
    @abstractmethod
    def get_form_by_scope(self, *, study_id, form_id):
        raise NotImplementedError

    @abstractmethod
    def get_field_by_scope(self, *, study_id, form_id, field_id):
        raise NotImplementedError

    @abstractmethod
    def exists_field_key(self, *, form_id, field_key, exclude_field_id=None):
        raise NotImplementedError

    @abstractmethod
    def save_field_aggregate(self, *, form_id, field_id, aggregate, actor_user_id):
        raise NotImplementedError


class FormBuilderQueryRepository(ABC):
    @abstractmethod
    def get_form_with_translations(self, *, study_id, form_id):
        raise NotImplementedError

    @abstractmethod
    def list_fields_for_form(self, *, form_id):
        raise NotImplementedError
