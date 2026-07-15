from allauth.account.adapter import DefaultAccountAdapter
from django.conf import settings
from django.contrib.sites.shortcuts import get_current_site


# Custom adapter to enable passing the expiry dates to the email template
    # FROM: CLAUDE https://claude.ai/share/8b142b17-5011-4ed7-a357-dc7fce9274d2

class CustomAllauthAccountAdapter(DefaultAccountAdapter):

    def format_email_subject(self, subject):
        # Get the site name dynamically
        site = get_current_site(self.request)
        # Return your custom format: "Site Name - Subject"
        return f"{site.name} - {subject}"



    # def send_confirmation_mail(self, request, emailconfirmation, signup):
    #     expire_days = getattr(settings, "ACCOUNT_EMAIL_CONFIRMATION_EXPIRE_DAYS", 3)
    #     self.send_mail(
    #         "account/email/email_confirmation_signup",
    #         emailconfirmation.email_address.email,
    #         {
    #             "user": emailconfirmation.email_address.user,
    #             "activate_url": self.get_email_confirmation_url(request, emailconfirmation),
    #             "expire_days": expire_days,
    #             "expire_days_label": "day" if expire_days == 1 else "days",
    #         },
    #     )