# Django
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import FormView, RedirectView
from django.contrib import messages

# Libs
from honeypot.forms import LoginForm
from honeypot.models.login_attempt import LoginAttempt
from app.utils.client import get_trusted_client_ip
from honeypot.app_settings import HONEYPOT_LOGIN_TRYOUT


class RedirectToLogin(RedirectView):
    pattern_name = "honeypot:login"


# A fake log-in: nothing to protect, and Django's csrfmiddlewaretoken field
# and csrftoken cookie would name the framework behind the bait.
@method_decorator(csrf_exempt, name="dispatch")
class LoginView(FormView):
    form_class = LoginForm
    template_name = "honeypot/login.html"
    success_url = reverse_lazy("honeypot:login")

    def form_valid(self, form):
        if (
            LoginAttempt.objects.filter(
                ip_address=get_trusted_client_ip(self.request)
            ).count()
            >= HONEYPOT_LOGIN_TRYOUT
        ):
            messages.error(
                self.request,
                "Please enter the correct email address and password for a staff account. Note that both fields may be case-sensitive.",
            )
        else:
            messages.error(
                self.request,
                "Please enter the correct email address and password for a staff account. Note that both fields may be case-sensitive.",
            )
            form.instance.user_agent = self.request.META.get("HTTP_USER_AGENT")
            form.instance.ip_address = get_trusted_client_ip(self.request)
            form.instance.session_key = self.request.session.session_key
            form.instance.path = self.request.path
            form.save()

        return super().form_valid(form)
