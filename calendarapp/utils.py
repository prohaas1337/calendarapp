from django.contrib.auth.models import Group

def get_edzo_emails():
    edzo_group = Group.objects.get(name="edzo")
    return list(edzo_group.user_set.values_list("email", flat=True))
