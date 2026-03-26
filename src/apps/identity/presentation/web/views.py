from django.contrib.auth import logout
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views import View

from apps.identity.forms import StyledAuthenticationForm


class IdentityLoginView(LoginView):
    template_name = "identity/login.html"
    authentication_form = StyledAuthenticationForm
    redirect_authenticated_user = True
    next_page = reverse_lazy("dashboard:main")


class IdentityLogoutView(View):
    def get(self, request, *args, **kwargs):
        logout(request)
        return redirect("identity:login")

    def post(self, request, *args, **kwargs):
        return self.get(request, *args, **kwargs)
