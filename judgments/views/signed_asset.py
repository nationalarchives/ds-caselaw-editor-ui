from caselawclient.models.utilities.aws import generate_signed_asset_url
from django.shortcuts import redirect


def redirect_to_signed_asset(request, key):
    return redirect(generate_signed_asset_url(key))
