from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ManualPermissionSpec:
    codename: str
    name: str


# Permissions are provisioned manually by project-owned SQL/commands.
# They must be curated explicitly by developers together with business owners.
# They intentionally live under the identity.User content type so permission
# checks stay in the "identity.*" namespace.
IDENTITY_PERMISSION_SPECS = (
    ManualPermissionSpec(
        codename="manage_users",
        name="Can manage identity users",
    ),
    ManualPermissionSpec(
        codename="manage_groups",
        name="Can manage permission groups",
    ),
    ManualPermissionSpec(
        codename="assign_groups",
        name="Can assign permission groups to users",
    ),
    ManualPermissionSpec(
        codename="assign_permissions",
        name="Can assign permissions to users and groups",
    ),
    ManualPermissionSpec(
        codename="view_access_control",
        name="Can view access control configuration",
    ),
)
