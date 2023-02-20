import factory

from judgments.models import Judgment


class JudgmentFactory(factory.Factory):
    class Meta:
        model = Judgment

    uri = "test/1234"
    neutral_citation = "2023/test/1234"
    court = "Court of Testing"
    name = "Test Judgment v Test Judgement"
    judgment_date_as_string = "2023-02-03"

    published = True
    sensitive = False
    supplemental = False
    anonymised = False

    source_name = "A. N. Uploader"
    source_email = "anuploader@example.com"

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        return model_class.objects.get_by_uri(cls.uri)
