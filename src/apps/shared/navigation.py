from django.shortcuts import redirect
from django.urls import reverse

from apps.identity.infrastructure.persistence.models import MembershipStatus, StudyMembership, StudySiteMembership
from apps.identity.public import ContextualAuthorizationService
from apps.study.infrastructure.persistence.models import Site, Study


def user_can_access_permission(user, permission_code, *, study_id=None, site_id=None):
    if not getattr(user, "is_authenticated", False):
        return False
    if getattr(user, "is_superuser", False):
        return True
    if study_id is None:
        return False
    return ContextualAuthorizationService().can(
        user=user,
        permission=permission_code,
        study_id=study_id,
        study_site_id=site_id,
    ).allowed


def get_layout_nav_permissions(user, *, study_id=None, site_id=None):
    return {
        "subjects": user_can_access_permission(
            user,
            "subject.view_subject_list",
            study_id=study_id,
            site_id=site_id,
        ),
        "queries": user_can_access_permission(
            user,
            "reconcile.view_dataquery",
            study_id=study_id,
            site_id=site_id,
        ),
        "sites": user_can_access_permission(
            user,
            "site.view_site_list",
            study_id=study_id,
            site_id=site_id,
        ),
        "studies": user_can_access_permission(
            user,
            "study.view_study_list",
            study_id=study_id,
            site_id=site_id,
        ),
        "users": user_can_access_permission(
            user,
            "identity.view_user_list",
            study_id=study_id,
            site_id=site_id,
        ),
        "dashboard": user_can_access_global_permission(user, "dashboard.view_dashboard"),
    }


def user_can_access_global_permission(user, permission_code):
    return getattr(user, "is_authenticated", False) and user.has_perm(permission_code)


def get_default_authenticated_url(request):
    study_id = get_default_study_id(request)
    site_id = get_default_site_id(request, study_id=study_id)
    if getattr(request.user, "is_superuser", False):
        if study_id is not None:
            return reverse("subject:subject_list", kwargs={"study_id": study_id})
        return reverse("study:study_list")

    if study_id is not None and user_can_access_permission(
        request.user,
        "subject.view_subject_list",
        study_id=study_id,
        site_id=site_id,
    ):
        return reverse("subject:subject_list", kwargs={"study_id": study_id})

    if user_can_access_permission(request.user, "identity.view_user_list", study_id=study_id):
        return reverse("identity:users")

    if user_can_access_permission(
        request.user,
        "dashboard.view_dashboard",
        study_id=study_id,
    ):
        return reverse("dashboard:main")

    return reverse("identity:current_user_profile")


def get_default_site_id(request, *, study_id):
    if study_id is None:
        return None

    cookie_site_id = _int_or_none(request.COOKIES.get("site_dropdown"))
    if cookie_site_id is not None and _user_can_select_site(request.user, study_id, cookie_site_id):
        return cookie_site_id

    if getattr(request.user, "is_superuser", False):
        return (
            Site.objects.filter(study_id=study_id, is_active=True, deleted=False)
            .order_by("id")
            .values_list("id", flat=True)
            .first()
        )

    return (
        StudySiteMembership.objects.filter(
            user=request.user,
            study_id=study_id,
            deleted=False,
            status=MembershipStatus.ACTIVE,
            site_id__in=Site.objects.filter(study_id=study_id, is_active=True, deleted=False).values("id"),
        )
        .order_by("site_id")
        .values_list("site_id", flat=True)
        .first()
    )


def redirect_to_default_application_page(request):
    if not getattr(request.user, "is_authenticated", False):
        return redirect("identity:login")
    return redirect(get_default_authenticated_url(request))


def get_default_study_id(request):
    cookie_study_id = _int_or_none(request.COOKIES.get("study_dropdown"))
    if cookie_study_id is not None and _user_can_select_study(request.user, cookie_study_id):
        return cookie_study_id

    if getattr(request.user, "is_superuser", False):
        return (
            Study.objects.filter(is_active=True, deleted=False)
            .order_by("id")
            .values_list("id", flat=True)
            .first()
        )

    return (
        StudyMembership.objects.filter(
            user=request.user,
            deleted=False,
            status=MembershipStatus.ACTIVE,
            study_id__in=Study.objects.filter(is_active=True, deleted=False).values("id"),
        )
        .order_by("study_id")
        .values_list("study_id", flat=True)
        .first()
    )


def _user_can_select_study(user, study_id):
    if getattr(user, "is_superuser", False):
        return Study.objects.filter(pk=study_id, is_active=True, deleted=False).exists()
    return StudyMembership.objects.filter(
        user=user,
        study_id=study_id,
        deleted=False,
        status=MembershipStatus.ACTIVE,
    ).exists()


def _user_can_select_site(user, study_id, site_id):
    if getattr(user, "is_superuser", False):
        return Site.objects.filter(pk=site_id, study_id=study_id, is_active=True, deleted=False).exists()
    return StudySiteMembership.objects.filter(
        user=user,
        study_id=study_id,
        site_id=site_id,
        deleted=False,
        status=MembershipStatus.ACTIVE,
    ).exists()


def _int_or_none(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
