import json
from typing import Optional

from caselawclient.Client import api_client
from caselawclient.responses.search_result import EditorPriority
from django.contrib import messages
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import redirect

from judgments.utils import ensure_local_referer_url


def hold_judgment_button(request):
    judgment_uri = request.POST["judgment_uri"]
    # we probably shouldn't hold if the judgment isn't assigned but we won't check
    hold = request.POST["hold"]
    if hold not in ["false", "true"]:
        raise RuntimeError("Hold value must be '0' or '1'")
    api_client.set_property(judgment_uri, "editor-hold", hold)
    if hold == "true":
        word = "held"
    else:
        word = "released"
    messages.success(request, f"Judgment {word}.")
    return redirect(ensure_local_referer_url(request))


def assign_judgment_button(request):
    judgment_uri = request.POST["judgment_uri"]
    assigned_to = request.POST.get("assigned_to", request.user.username)
    api_client.set_property(judgment_uri, "assigned-to", assigned_to)
    if assigned_to == request.user.username:
        msg = "Document assigned to you."
    elif assigned_to == "":
        msg = "Document unassigned."
    else:
        msg = f"Judgment assigned to {assigned_to}."
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return HttpResponse(
            json.dumps({"assigned_to": request.user.username, "message": msg}),
            content_type="application/json",
        )
    else:
        messages.success(request, msg)
        return redirect(ensure_local_referer_url(request))


def prioritise_judgment_button(request):
    """Editors can let other editors know that some judgments are more important than others."""

    def parse_priority(priority: str) -> Optional[str]:
        # note: use 09 if using numbers less than 10.
        priorities = {
            "low": EditorPriority.LOW.value,
            "medium": EditorPriority.MEDIUM.value,
            "high": EditorPriority.HIGH.value,
        }
        priority_string = priority.lower().strip()
        return priorities.get(priority_string)

    judgment_uri = request.POST["judgment_uri"]
    priority = parse_priority(request.POST["priority"])
    if priority:
        api_client.set_property(judgment_uri, "editor-priority", priority)

        messages.success(request, "Judgment priority set.")
        return redirect(ensure_local_referer_url(request))

    return HttpResponseBadRequest("Priority string not recognised")
