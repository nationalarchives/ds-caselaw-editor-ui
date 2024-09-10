from django.views.generic import TemplateView

from judgments.tests.factories import SearchResultFactory


class StyleGuide(TemplateView):
    template_name = "pages/style_guide.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        judgment = SearchResultFactory.build()
        context["judgment"] = judgment
        judgment_failed_to_parse = SearchResultFactory.build(failed_to_parse=True)
        judgment_on_hold = SearchResultFactory.build(metadata={"editor_hold": "true"})
        context["tabs"] = [
            {
                "selected": True,
                "label": "HTML view",
                "url": "#first-tab",
            },
            {
                "selected": False,
                "label": "PDF view",
                "url": "#second-tab",
            },
        ]
        context["judgments"] = [judgment, judgment_failed_to_parse, judgment_on_hold]
        context["document"] = judgment
        context["menu_items"] = [
            {"label": "Colours", "href": "#colours"},
            {
                "label": "Components",
                "href": "#components",
                "children": [
                    {"label": "Buttons", "href": "#buttons"},
                    {"label": "Judgment metadata form", "href": "#judgment-metadata-form"},
                    {"label": "Judgments list", "href": "#judgments-list"},
                    {"label": "Judgment toolbar", "href": "#judgment-toolbar"},
                    {"label": "Judgment toolbar button", "href": "#judgment-toolbar-button"},
                    {"label": "Note", "href": "#note"},
                    {"label": "Notification messaging", "href": "#notification-messaging"},
                    {"label": "Search form", "href": "#search-form"},
                    {"label": "Sidebar", "href": "#sidebar"},
                    {"label": "Summary panels", "href": "#summary-panels"},
                    {"label": "Tabs", "href": "#tabs"},
                ],
            },
            {
                "label": "Spacing",
                "href": "#spacing",
            },
            {
                "label": "Typography",
                "href": "#typography",
                "children": [
                    {"label": "Font family", "href": "#font-family"},
                    {"label": "Font sizes", "href": "#font-sizes"},
                    {"label": "Font weights", "href": "#font-weights"},
                    {"label": "Line heights", "href": "#line-heights"},
                ],
            },
        ]
        return context
