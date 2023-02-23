from judgments.utils.paginator import paginator


class TestPaginator:
    def test_paginator_2500(self):
        expected_result = {
            "current_page": 10,
            "has_next_page": True,
            "has_prev_page": True,
            "next_page": 11,
            "prev_page": 9,
            "next_pages": [11, 12, 13, 14, 15, 16, 17, 18, 19, 20],
            "number_of_pages": 250,
        }
        assert paginator(10, 2500) == expected_result

    def test_paginator_25(self):
        # 25 items has 5 items on page 3.
        expected_result = {
            "current_page": 1,
            "has_next_page": True,
            "has_prev_page": False,
            "next_page": 2,
            "prev_page": 0,
            "next_pages": [2, 3],
            "number_of_pages": 3,
        }
        assert paginator(1, 25) == expected_result

    def test_paginator_5(self):
        expected_result = {
            "current_page": 1,
            "has_next_page": False,
            "has_prev_page": False,
            "next_page": 2,  # Note: remember to check has_next_page
            "prev_page": 0,
            "next_pages": [],
            "number_of_pages": 1,
        }
        assert paginator(1, 5) == expected_result
