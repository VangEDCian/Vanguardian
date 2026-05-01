import logging
from typing import Iterable

import aiosmtplib
from asgiref.sync import async_to_sync
from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend
from django.core.mail.message import EmailMessage


logger = logging.getLogger(__name__)


class AioSmtpEmailBackend(BaseEmailBackend):
    def send_messages(self, email_messages: Iterable[EmailMessage] | None):
        if not email_messages:
            return 0

        sent_messages = 0
        for email_message in email_messages:
            if self._send(email_message):
                sent_messages += 1
        return sent_messages

    def _send(self, email_message: EmailMessage):
        recipients = email_message.recipients()
        if not recipients:
            return False

        message = email_message.message()

        try:
            async_to_sync(aiosmtplib.send)(
                message,
                hostname=settings.EMAIL_HOST,
                port=settings.EMAIL_PORT,
                username=settings.EMAIL_HOST_USER or None,
                password=settings.EMAIL_HOST_PASSWORD or None,
                use_tls=bool(getattr(settings, "EMAIL_USE_TLS", False)),
                start_tls=bool(getattr(settings, "EMAIL_USE_STARTTLS", False)),
                timeout=float(getattr(settings, "EMAIL_TIMEOUT", 10.0)),
            )
        except Exception:
            if not self.fail_silently:
                raise
            logger.exception("Failed to send email to %s", recipients)
            return False

        return True
