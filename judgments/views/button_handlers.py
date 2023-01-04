import json
from typing import Optional, Union

from caselawclient.Client import api_client
from django.contrib import messages
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import redirect


def hold_judgment_button(request):
    judgment_uri = request.POST["judgment_uri"]
    # we probably shouldn't hold if the judgment isn't assigned but we won't check
    hold = request.POST["hold"]
    if hold not in ["false", "true"]:
        raise RuntimeError("Hold value must be '0' or '1'")
    api_client.set_property(judgment_uri, "editor-hold", hold)
    target_uri = request.META.get("HTTP_REFERER") or "/"
    if hold == "true":
        word = "held"
    else:
        word = "released"
    messages.success(request, f"Judgment {word}.")
    return redirect(target_uri)


def assign_judgment_button(request):
    judgment_uri = request.POST["judgment_uri"]
    api_client.set_property(judgment_uri, "assigned-to", request.user.username)
    target_uri = request.META.get("HTTP_REFERER") or "/"
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return HttpResponse(
            json.dumps({"assigned_to": request.user.username}),
            content_type="application/json",
        )
    else:
        messages.success(request, "Judgment assigned to you.")
        return redirect(target_uri)


def prioritise_judgment_button(request):
    """Editors can let other editors know that some judgments are more important than others."""

    def parse_priority(priority: Union[str, int]) -> Optional[str]:
        # note: use 09 if using numbers less than 10.
        priorities = {"low": "10", "medium": "20", "high": "30"}
        priority_string = priority.lower().strip()
        return priorities.get(priority_string)

    judgment_uri = request.POST["judgment_uri"]
    priority = parse_priority(request.POST["priority"])
    if priority:
        api_client.set_property(judgment_uri, "editor-priority", priority)
        target_uri = request.META.get("HTTP_REFERER") or "/"

        messages.success(request, "Judgment priority set.")
        return redirect(target_uri)

    return HttpResponseBadRequest("Priority string not recognised")
