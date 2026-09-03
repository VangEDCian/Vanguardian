from django.utils import timezone

from apps.crf.domain.exceptions import FormBuilderDomainValidationError
from apps.crf.infrastructure.repositories import DjangoCrfFieldTemplateImportRepository


class CrfFieldTemplateImportAmbiguousError(FormBuilderDomainValidationError):
    """Raised when an import row resolves to more than one CRF object."""


class CrfFieldTemplateImportNotFoundError(FormBuilderDomainValidationError):
    """Raised when an import row cannot resolve a referenced CRF object."""


class CrfFieldTemplateImportService:
    repository_class = DjangoCrfFieldTemplateImportRepository

    def __init__(self, repository=None):
        self.repository = repository or self.repository_class()

    def resolve_template_by_name_or_code(self, *, study_id, form_name):
        templates = list(
            self.repository.find_templates_by_name_or_code(
                study_id=study_id,
                form_name=form_name,
            )[:2]
        )
        if not templates:
            raise CrfFieldTemplateImportNotFoundError(
                f"Form Name '{form_name}' was not found in this study."
            )
        if len(templates) > 1:
            raise CrfFieldTemplateImportAmbiguousError(
                f"Form Name '{form_name}' is ambiguous in this study."
            )
        return templates[0]

    def resolve_section_by_name_or_code(self, *, crf_template_id, section_name):
        sections = list(
            self.repository.find_sections_by_name_or_code(
                crf_template_id=crf_template_id,
                section_name=section_name,
            )[:2]
        )
        if not sections:
            raise CrfFieldTemplateImportNotFoundError(
                f"Section Name '{section_name}' was not found in this form."
            )
        if len(sections) > 1:
            raise CrfFieldTemplateImportAmbiguousError(
                f"Section Name '{section_name}' is ambiguous in this form."
            )
        return sections[0]

    def reset_template_fields_for_import(self, *, crf_template_id, actor_user_id, now=None):
        now = now or timezone.now()
        return self.repository.reset_template_fields_for_import(
            crf_template_id=crf_template_id,
            actor_user_id=actor_user_id,
            now=now,
        )

    def list_field_templates_for_import(self, *, crf_template_id, field_keys):
        return self.repository.find_field_templates_for_import(
            crf_template_id=crf_template_id,
            field_keys=field_keys,
        )

    def upsert_template_fields(self, *, prepared_rows, actor_user_id, now=None, cached_field_templates=None):
        now = now or timezone.now()
        cached_field_templates = dict(cached_field_templates or {})
        if not prepared_rows:
            return []

        row_results = []
        field_by_cache_key = {}
        update_rows = []
        create_rows = []
        outcome_by_key = {}

        for row in prepared_rows:
            payload = row.payload
            field_key = payload["field_key"]
            cached = field_by_cache_key.get(field_key)
            if cached is None:
                cached = cached_field_templates.get(field_key)
            if cached is None:
                cached = self.repository.build_field_template(
                    crf_template_id=row.form_template.pk,
                    field_key=field_key,
                    created_at=now,
                    created_by_id=actor_user_id,
                )
                field_by_cache_key[field_key] = cached
                create_rows.append((row, field_key, cached))
                outcome_by_key[field_key] = "created"
            else:
                if field_key not in outcome_by_key:
                    outcome_by_key[field_key] = "updated"
            field_template = cached
            field_template.data_type = payload["data_type"]
            field_template.is_active = True
            field_template.display_order = payload["display_order"]
            field_template.section_template_id = row.section_template.pk
            field_template.deleted = False
            field_template.updated_at = now
            field_template.updated_by_id = actor_user_id
            if field_template.pk:
                update_rows.append((row, field_template))
            row_results.append((row, field_template))

        # ensure existing cache only keeps unique objects per field key
        for field_key, field_template in field_by_cache_key.items():
            cached_field_templates[field_key] = field_template

        if update_rows:
            self.repository.bulk_update_field_templates(
                field_templates=[
                    row_payload[1]
                    for row_payload in update_rows
                ],
                update_fields=(
                    "data_type",
                    "is_active",
                    "display_order",
                    "section_template_id",
                    "deleted",
                    "updated_at",
                    "updated_by_id",
                ),
            )

        created_field_templates = []
        if create_rows:
            create_payload = [item[2] for item in create_rows]
            created_field_templates = self.repository.bulk_create_field_templates(
                field_templates=create_payload
            )
            for (_, field_key, field_template), created_field_template in zip(create_rows, created_field_templates):
                field_by_cache_key[field_key] = created_field_template
                cached_field_templates[field_key] = created_field_template

        updated_definitions = []
        created_definitions = []
        updated_ui_configs = []
        created_ui_configs = []

        for row, field_template in row_results:
            payload = row.payload
            field_template_id = field_template.pk
            if not field_template_id:
                # not expected after create phase, keep safe for malformed flows
                continue

            definition = getattr(field_template, "definition", None)
            definition_values = {
                "created_at": now,
                "updated_at": now,
                "deleted": False,
                "sdtm": payload["sdtm"],
                "range_min": payload["range_min"],
                "range_max": payload["range_max"],
                "precision": payload["precision"],
                "allowed_missing_values": payload["allowed_missing_values"] or "",
                "data_semantic": payload["data_semantic"],
                "text_max_length": payload["text_max_length"],
                "text_min_length": payload["text_min_length"],
                "pattern": payload["pattern"],
                "created_by_id": actor_user_id,
                "updated_by_id": actor_user_id,
            }
            if definition is None:
                created_definitions.append(
                    (
                        field_template_id,
                        self.repository.build_field_definition(
                            field_template_id=field_template_id,
                            **definition_values,
                        ),
                    )
                )
            else:
                for key, value in definition_values.items():
                    setattr(definition, key, value)
                updated_definitions.append((field_template_id, definition))

            ui_config = getattr(field_template, "ui_config", None)
            ui_config_values = {
                "created_at": now,
                "updated_at": now,
                "deleted": False,
                "control_type": payload["control_type"],
                "control_layout": payload["control_layout"] or "normal",
                "layout": payload["layout"],
                "behavior": payload["behavior"],
                "style": payload["style"],
                "classes": payload["classes"],
                "created_by_id": actor_user_id,
                "updated_by_id": actor_user_id,
            }
            if ui_config is None:
                created_ui_configs.append(
                    (
                        field_template_id,
                        self.repository.build_field_ui_config(
                            field_template_id=field_template_id,
                            **ui_config_values,
                        ),
                    )
                )
            else:
                for key, value in ui_config_values.items():
                    setattr(ui_config, key, value)
                updated_ui_configs.append((field_template_id, ui_config))

        if updated_definitions:
            self.repository.bulk_update_field_definitions(
                definitions=[item[1] for item in updated_definitions],
                update_fields=(
                    "created_at",
                    "updated_at",
                    "deleted",
                    "sdtm",
                    "range_min",
                    "range_max",
                    "precision",
                    "allowed_missing_values",
                    "data_semantic",
                    "text_max_length",
                    "text_min_length",
                    "pattern",
                    "created_by_id",
                    "updated_by_id",
                ),
            )

        if created_definitions:
            created_definition_rows = self.repository.bulk_create_field_definitions(
                definitions=[item[1] for item in created_definitions]
            )

        if updated_ui_configs:
            self.repository.bulk_update_field_ui_configs(
                ui_configs=[item[1] for item in updated_ui_configs],
                update_fields=(
                    "created_at",
                    "updated_at",
                    "deleted",
                    "control_type",
                    "control_layout",
                    "layout",
                    "behavior",
                    "style",
                    "classes",
                    "created_by_id",
                    "updated_by_id",
                ),
            )

        if created_ui_configs:
            created_ui_config_rows = self.repository.bulk_create_field_ui_configs(
                ui_configs=[item[1] for item in created_ui_configs]
            )
            ui_config_map = {
                int(field_template_id): ui_config
                for (field_template_id, ui_config), ui_config in zip(created_ui_configs, created_ui_config_rows)
            }
            for row, field_template in row_results:
                field_template_id = field_template.pk
                if field_template_id in ui_config_map:
                    field_template.ui_config = ui_config_map[field_template_id]

        # map created definition rows back to their field template ids
        if created_definitions and created_definition_rows:
            definition_map = {
                int(field_template_id): definition
                for (field_template_id, definition), definition in zip(created_definitions, created_definition_rows)
            }
            for row, field_template in row_results:
                field_template_id = field_template.pk
                if field_template_id in definition_map:
                    field_template.definition = definition_map[field_template_id]

        translation_field_template_rows = []
        translation_definition_rows = []
        translation_ui_config_rows = []
        field_template_ids = tuple(
            dict.fromkeys(
                row[1].pk for row in row_results
                if row[1].pk is not None
            )
        )
        definition_ids = tuple(
            dict.fromkeys(
                getattr(row[1], "definition", None).pk
                for row in row_results
                if getattr(row[1], "definition", None) is not None
            )
        )
        ui_config_ids = tuple(
            dict.fromkeys(
                getattr(row[1], "ui_config", None).pk
                for row in row_results
                if getattr(row[1], "ui_config", None) is not None
            )
        )
        existing_field_template_translations = {
            (translation.master_id, translation.language_code): translation
            for translation in self.repository.find_field_template_translations(
                field_template_ids=field_template_ids,
                language_codes=("en", "vi"),
            )
        }
        existing_field_definition_translations = {
            (translation.master_id, translation.language_code): translation
            for translation in self.repository.find_field_definition_translations(
                definition_ids=definition_ids,
                language_codes=("en", "vi"),
            )
        }
        existing_field_ui_config_translations = {
            (translation.master_id, translation.language_code): translation
            for translation in self.repository.find_field_ui_config_translations(
                ui_config_ids=ui_config_ids,
                language_codes=("en", "vi"),
            )
        }

        for row, field_template in row_results:
            payload = row.payload
            fallback_label = payload["label_en"] or payload["label_vi"] or payload["field_key"]
            definition = getattr(field_template, "definition", None)
            ui_config = getattr(field_template, "ui_config", None)
            for language_code in ("en", "vi"):
                translation_key = (field_template.pk, language_code)
                label = payload[f"label_{language_code}"] or fallback_label
                existing_translation = existing_field_template_translations.get(translation_key)
                if existing_translation is not None:
                    existing_translation.label = label
                    translation_field_template_rows.append(existing_translation)
                else:
                    translation_field_template_rows.append(
                        self.repository.build_field_template_translation(
                            master_id=field_template.pk,
                            language_code=language_code,
                            label=label,
                        )
                    )

                if definition is not None:
                    definition_translation_values = {
                        "unit": payload[f"unit_{language_code}"],
                        "codelist": payload[f"codelist_{language_code}"],
                        "comments": payload[f"comments_{language_code}"],
                        "pattern_err_msg": payload[f"pattern_err_msg_{language_code}"],
                    }
                    definition_translation_key = (definition.pk, language_code)
                    existing_definition_translation = existing_field_definition_translations.get(
                        definition_translation_key
                    )
                    if existing_definition_translation is not None:
                        for definition_key, definition_value in definition_translation_values.items():
                            setattr(existing_definition_translation, definition_key, definition_value)
                        translation_definition_rows.append(existing_definition_translation)
                    else:
                        translation_definition_rows.append(
                            self.repository.build_field_definition_translation(
                                master_id=definition.pk,
                                language_code=language_code,
                                **definition_translation_values,
                            )
                        )

                if ui_config is not None:
                    ui_translation_values = {
                        "text": payload[f"text_{language_code}"],
                        "options": payload[f"options_{language_code}"],
                    }
                    ui_translation_key = (ui_config.pk, language_code)
                    existing_ui_translation = existing_field_ui_config_translations.get(ui_translation_key)
                    if existing_ui_translation is not None:
                        for ui_translation_key_name, ui_translation_value in ui_translation_values.items():
                            setattr(existing_ui_translation, ui_translation_key_name, ui_translation_value)
                        translation_ui_config_rows.append(existing_ui_translation)
                    else:
                        translation_ui_config_rows.append(
                            self.repository.build_field_ui_config_translation(
                                master_id=ui_config.pk,
                                language_code=language_code,
                                **ui_translation_values,
                            )
                        )

        field_template_translations_updates = {}
        field_template_translations_creates = []
        for translation in translation_field_template_rows:
            key = (translation.master_id, translation.language_code)
            field_template_translations_updates[key] = translation

        if field_template_translations_updates:
            translations = list(field_template_translations_updates.values())
            self.repository.bulk_update_field_template_translations(
                translations=[t for t in translations if t.pk],
                update_fields=("label",),
            )
            field_template_translations_creates.extend(
                [t for t in translations if not t.pk]
            )
            self.repository.bulk_create_field_template_translations(
                translations=field_template_translations_creates
            )

        definition_translations_updates = {}
        definition_translations_creates = []
        for translation in translation_definition_rows:
            key = (translation.master_id, translation.language_code)
            definition_translations_updates[key] = translation
        if definition_translations_updates:
            definition_translations = list(definition_translations_updates.values())
            self.repository.bulk_update_field_definition_translations(
                translations=[t for t in definition_translations if t.pk],
                update_fields=("unit", "codelist", "comments", "pattern_err_msg"),
            )
            definition_translations_creates.extend([t for t in definition_translations if not t.pk])
            self.repository.bulk_create_field_definition_translations(
                translations=definition_translations_creates
            )

        ui_config_translations_updates = {}
        ui_config_translations_creates = []
        for translation in translation_ui_config_rows:
            key = (translation.master_id, translation.language_code)
            ui_config_translations_updates[key] = translation
        if ui_config_translations_updates:
            ui_config_translations = list(ui_config_translations_updates.values())
            self.repository.bulk_update_field_ui_config_translations(
                translations=[t for t in ui_config_translations if t.pk],
                update_fields=("text", "options"),
            )
            ui_config_translations_creates.extend([t for t in ui_config_translations if not t.pk])
            self.repository.bulk_create_field_ui_config_translations(
                translations=ui_config_translations_creates
            )

        for row, field_template in row_results:
            field_key = row.payload["field_key"]
            action = outcome_by_key.get(field_key, "updated")
            yield action, field_template, row

    def upsert_template_field(
        self,
        *,
        crf_template_id,
        section_template_id,
        payload,
        actor_user_id,
        now=None,
        existing_field_template=None,
    ):
        now = now or timezone.now()
        field_template = existing_field_template
        if field_template is None:
            field_template = self.repository.get_field_template_for_import(
                crf_template_id=crf_template_id,
                field_key=payload["field_key"],
            )
        action = "updated"
        if field_template is None:
            action = "created"
            field_template = self.repository.build_field_template(
                crf_template_id=crf_template_id,
                field_key=payload["field_key"],
                created_at=now,
                created_by_id=actor_user_id,
            )

        field_template.data_type = payload["data_type"]
        field_template.is_active = True
        field_template.display_order = payload["display_order"]
        field_template.section_template_id = section_template_id
        field_template.deleted = False
        field_template.updated_at = now
        field_template.updated_by_id = actor_user_id
        is_created = action == "created"
        if is_created:
            self.repository.save_field_template(field_template)
        else:
            self.repository.save_field_template(
                field_template,
                update_fields=(
                    "data_type",
                    "is_active",
                    "display_order",
                    "section_template_id",
                    "deleted",
                    "updated_at",
                    "updated_by_id",
                ),
            )

        self._save_field_template_translations(
            field_template=field_template,
            payload=payload,
            is_created=is_created,
        )
        definition = self._save_definition(
            field_template=field_template,
            payload=payload,
            actor_user_id=actor_user_id,
            now=now,
            is_created=is_created,
        )
        ui_config = self._save_ui_config(
            field_template=field_template,
            payload=payload,
            actor_user_id=actor_user_id,
            now=now,
            is_created=is_created,
        )
        self._save_definition_translations(
            definition=definition,
            payload=payload,
            is_created=is_created,
        )
        self._save_ui_config_translations(
            ui_config=ui_config,
            payload=payload,
            is_created=is_created,
        )
        return action, field_template

    def upsert_field_review_policy(
        self,
        *,
        study_id,
        study_version,
        crf_template_id,
        field_template_id,
        review_type,
        is_required_for_page_verify,
        is_required_for_lock,
        is_blocking_if_missing,
        role_required,
        is_enabled,
        actor_user_id,
        existing_field_review_policy=None,
        force_create=False,
        now=None,
    ):
        now = now or timezone.now()
        defaults = {
            "updated_at": now,
            "deleted": False,
            "is_required_for_page_verify": is_required_for_page_verify,
            "is_required_for_lock": is_required_for_lock,
            "is_blocking_if_missing": is_blocking_if_missing,
            "role_required": role_required,
            "is_enabled": is_enabled,
            "updated_by_id": actor_user_id,
        }
        policy = existing_field_review_policy
        if policy is None:
            if force_create:
                return "created", self.repository.create_field_review_policy(
                    study_id=study_id,
                    study_version=study_version,
                    crf_template_id=crf_template_id,
                    field_template_id=field_template_id,
                    review_type=review_type,
                    created_at=now,
                    created_by_id=actor_user_id,
                    **defaults,
                )

            policy = self.repository.get_field_review_policy(
                study_id=study_id,
                study_version=study_version,
                crf_template_id=crf_template_id,
                field_template_id=field_template_id,
                review_type=review_type,
            )
        if policy is None:
            policy = self.repository.create_field_review_policy(
                study_id=study_id,
                study_version=study_version,
                crf_template_id=crf_template_id,
                field_template_id=field_template_id,
                review_type=review_type,
                created_at=now,
                created_by_id=actor_user_id,
                **defaults,
            )
            return "created", policy

        for field_name, value in defaults.items():
            setattr(policy, field_name, value)
        self.repository.save_field_review_policy(policy, update_fields=list(defaults.keys()))
        return "updated", policy

    def list_field_review_policies_for_import(
        self,
        *,
        study_id,
        crf_template_id,
        field_template_ids,
        study_versions,
        review_types,
    ):
        return self.repository.find_field_review_policies_for_import(
            study_id=study_id,
            crf_template_id=crf_template_id,
            field_template_ids=field_template_ids,
            study_versions=study_versions,
            review_types=review_types,
        )

    def _save_field_template_translations(self, *, field_template, payload, is_created):
        fallback_label = payload["label_en"] or payload["label_vi"] or payload["field_key"]
        translations = (
            ("en", payload["label_en"] or fallback_label),
            ("vi", payload["label_vi"] or fallback_label),
        )
        for language_code, label in translations:
            if is_created:
                self.repository.create_field_template_translation(
                    field_template=field_template,
                    language_code=language_code,
                    label=label,
                )
                continue
            updated = self.repository.update_field_template_translation(
                field_template=field_template,
                language_code=language_code,
                label=label,
            )
            if not updated:
                self.repository.create_field_template_translation(
                    field_template=field_template,
                    language_code=language_code,
                    label=label,
                )

    def _save_definition(self, *, field_template, payload, actor_user_id, now, is_created):
        values = {
            "created_at": now,
            "updated_at": now,
            "deleted": False,
            "sdtm": payload["sdtm"],
            "range_min": payload["range_min"],
            "range_max": payload["range_max"],
            "precision": payload["precision"],
            "allowed_missing_values": payload["allowed_missing_values"] or "",
            "data_semantic": payload["data_semantic"],
            "text_max_length": payload["text_max_length"],
            "text_min_length": payload["text_min_length"],
            "pattern": payload["pattern"],
            "created_by_id": actor_user_id,
            "updated_by_id": actor_user_id,
        }
        if is_created:
            return self.repository.create_field_definition(
                field_template=field_template,
                values=values,
            )
        definition = getattr(field_template, "definition", None)
        if definition is not None:
            self.repository.update_field_definition(field_definition=definition, values=values)
            return definition
        return self.repository.create_field_definition(
            field_template=field_template,
            values=values,
        )

    def _save_definition_translations(self, *, definition, payload, is_created):
        for language_code in ("en", "vi"):
            values = {
                    "unit": payload[f"unit_{language_code}"],
                    "codelist": payload[f"codelist_{language_code}"],
                    "comments": payload[f"comments_{language_code}"],
                    "pattern_err_msg": payload[f"pattern_err_msg_{language_code}"],
            }
            if is_created:
                self.repository.create_field_definition_translation(
                    definition=definition,
                    language_code=language_code,
                    values=values,
                )
                continue
            updated = self.repository.update_field_definition_translation(
                definition=definition,
                language_code=language_code,
                values=values,
            )
            if not updated:
                self.repository.create_field_definition_translation(
                    definition=definition,
                    language_code=language_code,
                    values=values,
                )

    def _save_ui_config(self, *, field_template, payload, actor_user_id, now, is_created):
        values = {
            "created_at": now,
            "updated_at": now,
            "deleted": False,
            "control_type": payload["control_type"],
            "control_layout": payload["control_layout"] or "normal",
            "layout": payload["layout"],
            "behavior": payload["behavior"],
            "style": payload["style"],
            "classes": payload["classes"],
            "created_by_id": actor_user_id,
            "updated_by_id": actor_user_id,
        }
        if is_created:
            return self.repository.create_field_ui_config(
                field_template=field_template,
                values=values,
            )
        ui_config = getattr(field_template, "ui_config", None)
        if ui_config is not None:
            self.repository.update_field_ui_config(ui_config=ui_config, values=values)
            return ui_config
        return self.repository.create_field_ui_config(
            field_template=field_template,
            values=values,
        )

    def _save_ui_config_translations(self, *, ui_config, payload, is_created):
        for language_code in ("en", "vi"):
            values = {
                    "text": payload[f"text_{language_code}"],
                    "options": payload[f"options_{language_code}"],
            }
            if is_created:
                self.repository.create_field_ui_config_translation(
                    ui_config=ui_config,
                    language_code=language_code,
                    values=values,
                )
                continue
            updated = self.repository.update_field_ui_config_translation(
                ui_config=ui_config,
                language_code=language_code,
                values=values,
            )
            if not updated:
                self.repository.create_field_ui_config_translation(
                    ui_config=ui_config,
                    language_code=language_code,
                    values=values,
                )


__all__ = [
    "CrfFieldTemplateImportAmbiguousError",
    "CrfFieldTemplateImportNotFoundError",
    "CrfFieldTemplateImportService",
]
