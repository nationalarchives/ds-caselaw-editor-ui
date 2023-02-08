from django.shortcuts import redirect

from judgments.utils.aws import generate_signed_asset_url


def redirect_to_signed_asset(request, key):
    return redirect(generate_signed_asset_url(key))
