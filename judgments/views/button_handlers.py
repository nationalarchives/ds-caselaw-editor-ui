from __future__ import annotations

from django.contrib import messages
from django.shortcuts import redirect

from judgments.utils import api_client, ensure_local_referer_url


def hold_judgment_button(request):
    judgment_uri = request.POST["judgment_uri"]
    hold = request.POST["hold"]
    if hold not in ["false", "true"]:
        msg = "Hold value must be '0' or '1'"
        raise RuntimeError(msg)
    api_client.set_property(judgment_uri, "editor-hold", hold)
    word = "held" if hold == "true" else "released"
    messages.success(request, f"Document {word}.")
    return redirect(ensure_local_referer_url(request))
