# accounts/signals.py
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from allauth.socialaccount.models import SocialAccount
from .models import UserProfile


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)
        update_user_profile_name(instance)  # Facebook név frissítése új felhasználónál


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.userprofile.save()
    update_user_profile_name(instance)  # Facebook név frissítése profil mentésekor


def get_facebook_name(user):
    try:
        social_account = SocialAccount.objects.get(user=user, provider='facebook')
        return social_account.extra_data.get('name')
    except SocialAccount.DoesNotExist:
        return None


def update_user_profile_name(user):
    facebook_name = get_facebook_name(user)
    if facebook_name:
        user.userprofile.display_name = facebook_name
        user.userprofile.save()


def get_display_name(self):
    """Ha van Facebook fiók, azt használja, különben a felhasználónevet."""
    facebook_name = get_facebook_name(self)
    if facebook_name:
        return facebook_name
    if hasattr(self, 'userprofile') and self.userprofile.display_name:
        return self.userprofile.display_name
    return self.username


User.add_to_class("get_display_name", get_display_name)
