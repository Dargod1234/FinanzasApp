from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import User, Profile


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Crea un Profile automáticamente cuando se registra un User."""
    if created:
        Profile.objects.create(user=instance)
