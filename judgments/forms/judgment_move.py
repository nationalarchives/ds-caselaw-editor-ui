from django import forms


class MoveJudgmentForm(forms.Form):
    neutral_citation = forms.CharField(label="New Neutral Citation")
