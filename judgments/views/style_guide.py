from django.views.generic import TemplateView


class StyleGuide(TemplateView):
    template_name = "pages/style_guide.html"
