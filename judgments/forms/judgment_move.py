import ds_caselaw_utils as caselawutils
from django import forms
from django.core.exceptions import ValidationError


class NeutralCitationField(forms.CharField):
    def validate(self, value):
        super().validate(value)

        new_uri = caselawutils.neutral_url(value)

        # if a URI is not generated, the citation is probably invalid
        if not new_uri:
            raise ValidationError(
                f"Unable to parse neutral citation '{value}'", "invalid_citation"
            )


class MoveJudgmentForm(forms.Form):
    neutral_citation = NeutralCitationField(label="New Neutral Citation")


class OverwriteJudgmentForm(forms.Form):
    neutral_citation = NeutralCitationField(
        widget=forms.HiddenInput(), label="New Neutral Citation"
    )
