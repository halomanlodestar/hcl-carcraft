from django.conf import settings
from django.db import models
from django.utils import timezone


class Notification(models.Model):
    class Kind(models.TextChoices):
        INFO = "INFO", "Info"
        SUCCESS = "SUCCESS", "Success"
        WARNING = "WARNING", "Warning"

    KIND_ICONS = {"INFO": "bi-info-circle", "SUCCESS": "bi-check-circle", "WARNING": "bi-exclamation-triangle"}

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    kind = models.CharField(max_length=7, choices=Kind.choices, default=Kind.INFO)
    icon = models.CharField(max_length=40, blank=True)
    message = models.CharField(max_length=200)
    link = models.CharField(max_length=200, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.message

    @property
    def display_icon(self):
        return self.icon or self.KIND_ICONS[self.kind]


def notify(user, message, link="", kind=Notification.Kind.INFO, icon=""):
    return Notification.objects.create(user=user, message=message, link=link, kind=kind, icon=icon)
