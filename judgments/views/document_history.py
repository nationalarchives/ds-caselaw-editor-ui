import json
from datetime import datetime
from typing import Any, Literal, NotRequired, TypedDict
from uuid import uuid4

from caselawclient.client_helpers import VersionType
from caselawclient.models.documents import Document

from judgments.utils.view_helpers import DocumentView

VersionAnnotationDict = dict[str, Any]


class EventDict(TypedDict):
    data: VersionAnnotationDict
    datetime: datetime
    document: Document
    marklogic_version: int
    event_sequence_number: int
    agent: NotRequired[str]
    agent_email: NotRequired[str]


class SubmissionDict(TypedDict):
    events: NotRequired[list[EventDict]]


class StructuredSubmissionDict(SubmissionDict):
    submission_type: Literal["structured"]
    submission_data: VersionAnnotationDict
    document: Document
    marklogic_version: int
    submission_sequence_number: int


class OrphanSubmissionDict(SubmissionDict):
    submission_type: Literal["orphan"]
    orphan_submission_identifier: str


class LegacySubmissionDict(SubmissionDict):
    submission_type: Literal["legacy"]
    annotation: str
    marklogic_version: int
    submission_sequence_number: int
    event_sequence_number: int
    datetime: datetime


class DocumentHistorySequencer:
    structured_history: list[SubmissionDict]
    submission: SubmissionDict | None
    event_sequence_number: int
    submission_sequence_number: int

    def __init__(self, history: list[Document]) -> None:
        # An empty stack of submissions to begin with
        self.structured_history = []

        # Start from the point of there being no valid submission in progress
        self.submission = None

        # Event sequence number increments on each new event
        self.event_sequence_number = 0

        # Submission sequence only gets incremented for new submissions
        self.submission_sequence_number = 0

        # These are all MarkLogic versions, not necessarily our concept of submissions... so unpack it!
        for version in history:
            self.add_event_to_structured_history(version)

        # We're now done with events, so make sure the current submission is closed out.
        self.append_current_submission_to_structured_history()

    def add_event_to_structured_history(self, event: Document) -> None:
        """The `event` parameter currently _has_ to be a `Document`. This won't hold true in future when we get
        integrated events, but it is for now."""
        # Iterate this at the beginning of the loop because 1-index is nicer for humans
        self.event_sequence_number += 1

        try:
            structured_data = json.loads(event.annotation)

            # If we're here, we can unpack the structured data and that means we can figure out what next.

            # The event being a submission is one of two cases where we need to open a new submission.
            if structured_data["type"] == VersionType.SUBMISSION.value:
                # This version is a submission

                # If a submission is already open, pop it on the stack.
                if self.submission:
                    self.append_current_submission_to_structured_history()

                # Open a new submission ready for events.
                self.submission_sequence_number += 1
                self.submission = StructuredSubmissionDict(
                    {
                        "submission_type": "structured",
                        "submission_data": structured_data,
                        "document": event,
                        "events": [],
                        "submission_sequence_number": self.submission_sequence_number,
                        "marklogic_version": event.version_number,
                    },
                )

            # The second case for opening a new submission is if we reach a structured event which _isn't_ a submission
            # (which would have been caught by the first case) _and_ there isn't already an open submission. If that's
            # the case, open a new 'orphan' submission.
            elif not self.submission:
                self.submission = OrphanSubmissionDict(
                    {
                        "submission_type": "orphan",
                        "orphan_submission_identifier": str(uuid4()),
                        "events": [],
                    },
                )

            # At this point we've started a new submission if we need to, so go ahead and assemble the event object
            # and push it into the submission's event stack
            self.submission["events"].append(
                build_event_object(
                    event_sequence_number=self.event_sequence_number,
                    event_data=structured_data,
                    event_document=event,
                ),
            )

        # Catch both a TypeError (this thing has no annotation) and JSON Decode (it's not structured)
        except (TypeError, json.JSONDecodeError):
            # This is a legacy unstructured annotation!

            # If there is already an open submission, we don't know where it ends. Pop it on the stack, make sure we
            # unset it.
            if self.submission:
                self.append_current_submission_to_structured_history()

            # Pop a new submission onto the stack for the legacy. Don't use the submission variable in the process,
            # since this will upset the next loop.

            self.submission_sequence_number += 1
            self.structured_history.append(
                LegacySubmissionDict(
                    {
                        "submission_type": "legacy",
                        "annotation": event.annotation,
                        "marklogic_version": event.version_number,
                        "submission_sequence_number": self.submission_sequence_number,
                        "event_sequence_number": self.event_sequence_number,
                        "datetime": event.version_created_datetime,
                    },
                ),
            )

    def append_current_submission_to_structured_history(self):
        """Append current submission to structured history (if one is open), then set current submission to `None`."""
        if self.submission:
            self.structured_history.append(self.submission)

        self.submission = None


def build_event_object(
    event_sequence_number: int,
    event_data: VersionAnnotationDict,
    event_document: Document,
) -> EventDict:
    event_object: EventDict = {
        "data": event_data,
        "datetime": event_document.version_created_datetime,
        "document": event_document,
        "event_sequence_number": event_sequence_number,
        "marklogic_version": event_document.version_number,
    }

    if "payload" in event_data and "submitter" in event_data["payload"]:
        event_object["agent"] = event_data["payload"]["submitter"]["name"]
        event_object["agent_email"] = event_data["payload"]["submitter"]["email"]

    return event_object


class DocumentHistoryView(DocumentView):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # The versions _usually_ come back from MarkLogic in an inverse list, but it's not guaranteed.
        # Forcibly put them in an ordered list so we can neatly process them.
        sorted_ml_versions: list[Document] = sorted(
            context["document"].versions_as_documents,
            key=lambda x: x.version_number,
        )

        context["structured_history"] = DocumentHistorySequencer(
            sorted_ml_versions,
        ).structured_history

        return context

    template_name = "judgment/history.html"
