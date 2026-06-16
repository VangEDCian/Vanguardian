from apps.subject.models import SubjectEventInstance, SubjectEventInstanceFile


class DjangoSubjectEventInstanceFileRepository:
    @staticmethod
    def get_event_instance(*, study_id, subject_id, event_instance_id):
        return SubjectEventInstance.objects.filter(
            pk=event_instance_id,
            study_id=study_id,
            subject_id=subject_id,
            deleted=False,
        ).first()

    @staticmethod
    def has_files(*, event_instance_id):
        return SubjectEventInstanceFile.objects.filter(
            event_instance_id=event_instance_id,
            deleted=False,
        ).exists()

    @staticmethod
    def list_files(*, event_instance_id):
        return SubjectEventInstanceFile.objects.filter(
            event_instance_id=event_instance_id,
            deleted=False,
        ).order_by("-created_at", "-id")

    @staticmethod
    def get_file(*, event_instance_id, file_id):
        return SubjectEventInstanceFile.objects.filter(
            pk=file_id,
            event_instance_id=event_instance_id,
            deleted=False,
        ).first()

    @staticmethod
    def create_file(
        *,
        study_id,
        subject_id,
        site_id,
        event_instance_id,
        original_file_name,
        stored_file_name,
        storage_relative_path,
        mime_type,
        file_size_bytes,
        checksum_sha256,
        actor_user_id,
        now,
    ):
        return SubjectEventInstanceFile.objects.create(
            study_id=study_id,
            subject_id=subject_id,
            site_id=site_id,
            event_instance_id=event_instance_id,
            original_file_name=original_file_name,
            stored_file_name=stored_file_name,
            storage_relative_path=storage_relative_path,
            mime_type=mime_type,
            file_size_bytes=file_size_bytes,
            checksum_sha256=checksum_sha256,
            created_at=now,
            updated_at=now,
            created_by_id=actor_user_id,
            updated_by_id=actor_user_id,
        )
