from django.contrib.auth.views import LoginView
from django.urls import reverse_lazy

from apps.identity.forms import StyledAuthenticationForm


class IdentityLoginView(LoginView):
    template_name = "identity/login.html"
    authentication_form = StyledAuthenticationForm
    redirect_authenticated_user = True
    next_page = reverse_lazy("admin:index")

