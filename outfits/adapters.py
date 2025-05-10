from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.conf import settings
from django.shortcuts import redirect

class CustomAccountAdapter(DefaultAccountAdapter):
    def is_open_for_signup(self, request):
        # Allow signup for everyone (you can add condition if needed)
        return True


class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    def is_auto_signup_allowed(self, request, sociallogin):
        # Skip manual signup form for Google login if email is present
        if sociallogin.account.provider == 'google':
            user = sociallogin.user
            return user.email and user.email.strip() != ""
        return super().is_auto_signup_allowed(request, sociallogin)
