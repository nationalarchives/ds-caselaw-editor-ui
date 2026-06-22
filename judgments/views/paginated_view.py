from django.views.generic import TemplateView


class PaginatedView(TemplateView):
    def get_pagination_context(self, request, paginator):
        query_params = request.GET.copy()
        query_params.pop("page", None)

        query_string = query_params.urlencode()
        base_qs = f"{request.path}?{query_string}&" if query_string else f"{request.path}?"

        def page_href(page_number):
            return f"{base_qs}page={page_number}"

        items = []

        if paginator.get("show_first_page", False):
            items.append(
                {
                    "number": 1,
                    "href": page_href(1),
                },
            )

        if paginator.get("show_first_page_divider", False):
            items.append(
                {
                    "ellipsis": True,
                },
            )

        for page in paginator.get("page_range", []):
            item = {
                "number": page,
                "href": page_href(page),
            }

            if page == paginator.get("current_page", None):
                item["current"] = True

            items.append(item)

        if paginator.get("show_last_page_divider", False):
            items.append(
                {
                    "ellipsis": True,
                },
            )

        if paginator.get("show_last_page", False):
            items.append(
                {
                    "number": paginator.get("number_of_pages", 0),
                    "href": page_href(paginator.get("number_of_pages", 0)),
                },
            )

        previous_page = (
            paginator.get("prev_page", None)
            if paginator.get("has_prev_page", False)
            else paginator.get("current_page", 0)
        )

        next_page = (
            paginator.get("next_page", None)
            if paginator.get("has_next_page", False)
            else paginator.get("current_page", 0)
        )

        return {
            "previous": {
                "html": "Previous",
                "href": page_href(previous_page),
            },
            "items": items,
            "next": {
                "html": "Next",
                "href": page_href(next_page),
            },
        }
