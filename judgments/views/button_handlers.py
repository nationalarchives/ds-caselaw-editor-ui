import json

from caselawclient.responses.search_result import EditorPriority
from django.contrib import messages
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import redirect

from judgments.utils import api_client, ensure_local_referer_url


def hold_judgment_button(request):
    judgment_uri = request.POST["judgment_uri"]
    # we probably shouldn't hold if the judgment isn't assigned but we won't check
    hold = request.POST["hold"]
    if hold not in ["false", "true"]:
        msg = "Hold value must be '0' or '1'"
        raise RuntimeError(msg)
    api_client.set_property(judgment_uri, "editor-hold", hold)
    word = "held" if hold == "true" else "released"
    messages.success(request, f"Document {word}.")
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
        msg = f"Document assigned to {assigned_to}."
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

    def parse_priority(priority: str) -> str | None:
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

        messages.success(request, "Document priority set.")
        return redirect(ensure_local_referer_url(request))

    return HttpResponseBadRequest("Priority string not recognised")
