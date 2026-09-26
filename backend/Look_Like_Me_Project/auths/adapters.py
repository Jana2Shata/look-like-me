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

    def get_reset_password_from_key_url(self, key: str) -> str:
        return settings.HEADLESS_FRONTEND_URLS["account_reset_password_from_key"]
    # .format(uid=self.request.GET.get("uid"), token=key)


    # SOURCE: https://stackoverflow.com/questions/75900209/handling-mail-verification-using-dj-rest-auth
    def get_email_confirmation_url(self, request, emailconfirmation):

        """
            Changing the confirmation URL to point to the frontend instead of the default allauth backend URL.
        """

        url = (
            settings.HEADLESS_FRONTEND_URLS["email_verification"]
            + emailconfirmation.key
        )
        return url


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