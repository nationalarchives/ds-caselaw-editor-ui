import json

from caselawclient.client_helpers import VersionType

from judgments.utils.view_helpers import DocumentView


def structure_document_history_by_submissions(history):
    # An empty stack of submissions to begin with
    structured_history: list = []

    # Start from the point of there being no valid submission in progress
    submission = None

    # Event sequence number increments on each new event
    event_sequence_number: int = 0

    # Submission sequence only gets incremented for new submissions
    submission_sequence_number: int = 0

    # These are all MarkLogic versions, not necessarily our concept of submissions... so unpack it!
    for version in history:
        # Iterate this at the beginning of the loop because 1-index is nicer for humans
        event_sequence_number += 1

        try:
            structured_data = json.loads(version.annotation)

            # If we're here, we can unpack the structured data and that means we can figure out what next.

            if structured_data["type"] == VersionType.SUBMISSION.value:
                # This version is a submission

                # If a submission is already open, pop it on the stack.
                if submission:
                    structured_history.append(submission)

                submission_sequence_number += 1

                submission = {
                    "type": "structured",
                    "submission_data": structured_data,
                    "document": version,
                    "events": [],
                    "sequence_number": submission_sequence_number,
                }

            elif not submission:
                # This isn't a submission, it's an event causing a new version. There's also a possibility that the
                # first structured event we see happens outside a submission, in which case it gets its own special
                # orphan submission.
                submission = {
                    "type": "structured",
                    "orphan": True,
                    "events": [],
                }

            # At this point we've started a new submission if we need to, so go ahead and assemble the event object
            # and push it into the submission's event stack
            event_object = {
                "data": structured_data,
                "datetime": version.version_created_datetime,
                "document": version,
                "sequence_number": event_sequence_number,
                "marklogic_version": version.version_number,
            }

            if (
                "payload" in structured_data
                and "submitter" in structured_data["payload"]
            ):
                event_object["agent"] = structured_data["payload"]["submitter"]["name"]
                event_object["agent_email"] = structured_data["payload"]["submitter"][
                    "email"
                ]

            submission["events"].append(event_object)

        # Catch both a TypeError (this thing has no annotation) and JSON Decode (it's not structured)
        except (TypeError, json.JSONDecodeError):
            # This is a legacy unstructured annotation!

            # If there is already an open submission, we don't know where it ends. Pop it on the stack, make sure we
            # unset it.
            if submission:
                structured_history.append(submission)
                submission = None

            # Pop a new submission onto the stack for the legacy. Don't use the submission variable in the process,
            # since this will upset the next loop.
            submission_sequence_number += 1
            structured_history.append(
                {
                    "type": "legacy",
                    "annotation": version.annotation,
                    "marklogic_version": version.version_number,
                    "sequence_number": submission_sequence_number,
                },
            )

    # We're now done with the version stack. If a submission is still open, pop it on the stack.
    if submission:
        structured_history.append(submission)

    return structured_history


class DocumentHistoryView(DocumentView):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # The versions _usually_ come back from MarkLogic in an inverse list, but it's not guaranteed.
        # Forcibly put them in an ordered list so we can neatly process them.
        sorted_ml_versions = sorted(
            context["document"].versions_as_documents,
            key=lambda x: x.version_number,
        )

        context["structured_history"] = structure_document_history_by_submissions(
            sorted_ml_versions,
        )

        return context

    template_name = "judgment/history.html"
