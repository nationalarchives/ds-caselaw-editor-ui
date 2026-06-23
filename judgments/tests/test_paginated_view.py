from django.test import RequestFactory, TestCase

from judgments.views.paginated_view import PaginatedView


class TestPaginatedView(TestCase):
    def test_get_pagination_context_builds_pagination_data(self):
        self.request_factory = RequestFactory()
        self.view = PaginatedView()
        request = self.request_factory.get("/search/?query=test&sort=date&page=3")

        paginator = {
            "show_first_page": True,
            "show_first_page_divider": True,
            "page_range": [3, 4, 5],
            "current_page": 4,
            "show_last_page_divider": True,
            "show_last_page": True,
            "number_of_pages": 10,
            "prev_page": 3,
            "has_prev_page": True,
            "next_page": 5,
            "has_next_page": True,
        }

        result = self.view.get_pagination_context(
            request=request,
            paginator=paginator,
        )

        assert result == {
            "previous": {
                "html": "Previous",
                "href": "/search/?query=test&sort=date&page=3",
            },
            "items": [
                {
                    "number": 1,
                    "href": "/search/?query=test&sort=date&page=1",
                },
                {
                    "ellipsis": True,
                },
                {
                    "number": 3,
                    "href": "/search/?query=test&sort=date&page=3",
                },
                {
                    "number": 4,
                    "href": "/search/?query=test&sort=date&page=4",
                    "current": True,
                },
                {
                    "number": 5,
                    "href": "/search/?query=test&sort=date&page=5",
                },
                {
                    "ellipsis": True,
                },
                {
                    "number": 10,
                    "href": "/search/?query=test&sort=date&page=10",
                },
            ],
            "next": {
                "html": "Next",
                "href": "/search/?query=test&sort=date&page=5",
            },
        }
