from django.utils import timezone

from .models import CircleMember, Invite, ShareGrant


def connect(a, b, relation_a="", relation_b=""):
    CircleMember.objects.get_or_create(owner=a, member=b, defaults={"relation": relation_a})
    CircleMember.objects.get_or_create(owner=b, member=a, defaults={"relation": relation_b})
    ShareGrant.objects.get_or_create(owner=a, viewer=b)
    ShareGrant.objects.get_or_create(owner=b, viewer=a)


def disconnect(a, b):
    CircleMember.objects.filter(owner=a, member=b).delete()
    CircleMember.objects.filter(owner=b, member=a).delete()
    ShareGrant.objects.filter(owner=a, viewer=b).delete()
    ShareGrant.objects.filter(owner=b, viewer=a).delete()


def claim_invites(user):
    Invite.objects.filter(email__iexact=user.email, invitee__isnull=True, status="pending").update(invitee=user)


def grant(owner, viewer):
    return ShareGrant.objects.filter(owner=owner, viewer=viewer).first()


def notify_rough_day(user):
    from notify.services import queue
    count = 0
    for g in ShareGrant.objects.filter(owner=user, rough_day=True).select_related("viewer"):
        queue(g.viewer, "care", f"{user.display_name} is having a rough day",
              "No details, just a heads up. Maybe check in or send a little love.", f"/care/person/{user.id}",
              timezone.now(), dedupe=f"rough:{user.id}:{g.viewer_id}:{timezone.now().date()}", respect_quiet=True)
        count += 1
    return count
