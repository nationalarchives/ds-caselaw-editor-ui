import factory

from judgments.models import Judgment


class JudgmentFactory(factory.Factory):
    class Meta:
        model = Judgment

    uri = "test/1234"
    name = "Test Judgment v Test Judgement"

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        return model_class.objects.get_by_uri(cls.uri)
