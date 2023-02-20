import factory

from judgments.models import Judgment


class JudgmentFactory(factory.Factory):
    class Meta:
        model = Judgment

    uri = "test/1234"
    neutral_citation = "2023/test/1234"
    court = "Court of Testing"
    name = "Test Judgment v Test Judgement"

    published = True

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        return model_class.objects.get_by_uri(cls.uri)
