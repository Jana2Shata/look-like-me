
from allauth.account.signals import email_confirmed, email_confirmation_sent  # instead of user_signed_up, because it directs to a non-existing template
from django.dispatch import receiver
from allauth.account.models import EmailAddress

from .models import User

from allauth.account.models import EmailConfirmationHMAC # has-based message auth, does NOT rely on DB records

@receiver(email_confirmation_sent, sender=EmailConfirmationHMAC)
def deactivate_on_confirmation_sent(request, confirmation, signup, **kwargs):
    if signup:  # only deactivate on signup, not on email change
        user = confirmation.email_address.user
        user.is_active = False
        user.save()



# FROM Source - https://stackoverflow.com/a/24817474

@receiver(email_confirmed, sender=EmailAddress)
def email_confirmed_(request, email_address, **kwargs):

    user = User.objects.get(email=email_address.email)
    user.is_active = True

    user.save()

