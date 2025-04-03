from django.contrib.auth.models import Group

def get_edzo_emails():
    edzo_group = Group.objects.get(name="edzo")
    return list(edzo_group.user_set.values_list("email", flat=True))

from allauth.socialaccount.models import SocialAccount

def get_facebook_name(user):
    try:
        social_account = SocialAccount.objects.get(user=user, provider='facebook')
        return social_account.extra_data.get('name')
    except SocialAccount.DoesNotExist:
        return None
