import csv
import io
import re
from collections import defaultdict
from dataclasses import dataclass, field

from django.contrib.auth.models import Group, Permission
from django.db import transaction
from openpyxl import load_workbook

from apps.identity.models import Role, RoleScopeLevel  # noqa: DDD022

_REQUIRED_COLUMNS = {
    "role_name",
    "group_name",
    "access_level_from_dmp",
    "permission",
}


@dataclass
class RolePermissionImportResult:
    total_rows: int = 0
    imported_rows: int = 0
    skipped_rows: int = 0
    created_roles: int = 0
    updated_roles: int = 0
    group_permission_links: int = 0
    role_group_links: int = 0
    role_permission_links: int = 0
    issues: list[str] = field(default_factory=list)

    def as_dict(self):
        return {
            "total_rows": self.total_rows,
            "imported_rows": self.imported_rows,
            "skipped_rows": self.skipped_rows,
            "created_roles": self.created_roles,
            "updated_roles": self.updated_roles,
            "group_permission_links": self.group_permission_links,
            "role_group_links": self.role_group_links,
            "role_permission_links": self.role_permission_links,
            "issues": self.issues,
        }


class IdentityRolePermissionImportService:
    @transaction.atomic
    def import_workbook(self, *, study_id: int, import_file):
        rows = self._read_rows(import_file)
        result = RolePermissionImportResult(total_rows=len(rows))
        access_levels_by_role: dict[str, set[str]] = defaultdict(set)

        for row_number, row in rows:
            role_name = row.get("role_name", "").strip()
            group_name = row.get("group_name", "").strip()
            permission_key = row.get("permission", "").strip()
            access_levels = self._split_access_levels(row.get("access_level_from_dmp", ""))

            if not role_name or not group_name or not permission_key:
                result.skipped_rows += 1
                result.issues.append(f"Row {row_number}: missing role_name, group_name, or permission.")
                continue
            if "." not in permission_key:
                result.skipped_rows += 1
                result.issues.append(f"Row {row_number}: invalid permission '{permission_key}'.")
                continue

            group = Group.objects.filter(name=group_name).first()
            if group is None:
                result.skipped_rows += 1
                result.issues.append(f"Row {row_number}: group '{group_name}' does not exist.")
                continue

            app_label, codename = permission_key.split(".", 1)
            permission = Permission.objects.filter(
                content_type__app_label=app_label.strip(),
                codename=codename.strip(),
            ).first()
            if permission is None:
                result.skipped_rows += 1
                result.issues.append(f"Row {row_number}: permission '{permission_key}' does not exist.")
                continue

            role, created = Role.objects.get_or_create(
                study_id=study_id,
                name=role_name,
                defaults={
                    "code": self._role_code_from_name(role_name),
                    "description": self._description_from_access_levels(access_levels),
                    "scope_level": RoleScopeLevel.STUDY_SITE,
                },
            )
            if created:
                result.created_roles += 1
            else:
                result.updated_roles += self._update_role_description(
                    role,
                    existing_levels=access_levels_by_role[role_name],
                    incoming_levels=access_levels,
                )

            access_levels_by_role[role_name].update(access_levels)
            if not role.groups.filter(pk=group.pk).exists():
                role.groups.add(group)
                result.role_group_links += 1
            if not group.permissions.filter(pk=permission.pk).exists():
                group.permissions.add(permission)
                result.group_permission_links += 1
            if not role.permissions.filter(pk=permission.pk).exists():
                role.permissions.add(permission)
                result.role_permission_links += 1
            result.imported_rows += 1

        return result.as_dict()

    def build_summary(self, *, study_id: int):
        roles = [
            {
                "name": role.name,
                "description": role.description,
                "group_count": role.groups.count(),
                "permission_count": role.permissions.count(),
            }
            for role in Role.objects.filter(study_id=study_id).prefetch_related("groups", "permissions").order_by("name")
        ]
        return {"roles": roles, "role_count": len(roles)}

    def _read_rows(self, import_file):
        filename = getattr(import_file, "name", "")
        if filename.lower().endswith(".csv"):
            return self._read_csv_rows(import_file)
        return self._read_excel_rows(import_file)

    def _read_csv_rows(self, import_file):
        raw_data = import_file.read()
        text = raw_data if isinstance(raw_data, str) else raw_data.decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(text))
        return self._normalize_dict_rows(reader)

    def _read_excel_rows(self, import_file):
        workbook = load_workbook(import_file, read_only=True, data_only=True)
        sheet = workbook.active
        rows = list(sheet.iter_rows(values_only=True))
        if not rows:
            return []
        headers = [self._normalize_header(value) for value in rows[0]]
        dict_rows = []
        for raw_row in rows[1:]:
            row = {headers[index]: "" if value is None else str(value).strip() for index, value in enumerate(raw_row) if index < len(headers) and headers[index]}
            dict_rows.append(row)
        return self._normalize_dict_rows(dict_rows)

    def _normalize_dict_rows(self, rows):
        normalized_rows = []
        for row_number, raw_row in enumerate(rows, start=2):
            row = {self._normalize_header(key): str(value or "").strip() for key, value in raw_row.items()}
            missing = _REQUIRED_COLUMNS.difference(row)
            if missing:
                missing_text = ", ".join(sorted(missing))
                raise ValueError(f"Missing required import columns: {missing_text}")
            normalized_rows.append((row_number, row))
        return normalized_rows

    @staticmethod
    def _normalize_header(value):
        normalized = re.sub(r"[^a-z0-9]+", "_", str(value or "").strip().lower()).strip("_")
        if normalized in {"accss_level_from_dmp", "access_level_from_dmp"}:
            return "access_level_from_dmp"
        return normalized

    @staticmethod
    def _split_access_levels(value):
        return [item.strip() for item in str(value or "").split(";") if item.strip()]

    @staticmethod
    def _role_code_from_name(value):
        return re.sub(r"[^A-Z0-9]+", "_", str(value or "").strip().upper()).strip("_")

    @classmethod
    def _description_from_access_levels(cls, access_levels):
        description = "; ".join(dict.fromkeys(access_levels))
        return description[:255]

    def _update_role_description(self, role, *, existing_levels, incoming_levels):
        combined_levels = list(dict.fromkeys([*existing_levels, *incoming_levels]))
        description = self._description_from_access_levels(combined_levels)
        if description and role.description != description:
            role.description = description
            role.save(update_fields=["description"])
            return 1
        return 0
