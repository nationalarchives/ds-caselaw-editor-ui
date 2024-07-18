from django.views.generic import TemplateView


class StyleGuide(TemplateView):
    template_name = "pages/style_guide.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["menu_items"] = [
            {"label": "Colours", "href": "#colours"},
            {
                "label": "Components",
                "href": "#components",
                "children": [
                    {"label": "Buttons", "href": "#buttons"},
                    {"label": "Note", "href": "#note"},
                    {"label": "Notification messaging", "href": "#notification-messaging"},
                    {"label": "Search form", "href": "#search-form"},
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
