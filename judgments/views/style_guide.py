from django.shortcuts import redirect
from django.views.generic import TemplateView


class StyleGuideComponents(TemplateView):
    template_name = "pages/style_guide_components.html"


class StyleGuideBranding(TemplateView):
    template_name = "pages/style_guide_branding.html"


def style_guide_redirect(_request):
    return redirect("style_guide_components")
