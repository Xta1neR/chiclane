from django.db.models.signals import post_save
from django.contrib.auth.models import User
from django.dispatch import receiver
from django.contrib.auth.signals import user_logged_in
from .models import CustomerProfile, LoginActivity

# Create CustomerProfile only if it doesn't exist
@receiver(post_save, sender=User)
def create_customer_profile(sender, instance, created, **kwargs):
    if created:
        # Avoid duplicates
        CustomerProfile.objects.get_or_create(user=instance)

# Record login activity
@receiver(user_logged_in)
def record_login(sender, user, request, **kwargs):
    ip = request.META.get("REMOTE_ADDR", "")
    ua = request.META.get("HTTP_USER_AGENT", "")[:300]
    LoginActivity.objects.create(user=user, ip_address=ip, user_agent=ua)
