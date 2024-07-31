import math

from caselawclient.search_parameters import RESULTS_PER_PAGE


def paginator(current_page, total):
    number_of_pagination_links = 5
    size_per_page = RESULTS_PER_PAGE
    number_of_pages = math.ceil(int(total) / size_per_page)

    half_range = number_of_pagination_links // 2

    if number_of_pages <= number_of_pagination_links:
        page_range = list(range(1, number_of_pages + 1))
    elif current_page - half_range < 1:
        page_range = list(range(1, number_of_pagination_links + 1))
    elif current_page + half_range > number_of_pages:
        page_range = list(range(number_of_pages - number_of_pagination_links + 1, number_of_pages + 1))
    else:
        page_range = list(range(current_page - half_range, current_page + half_range + 1))

    show_first_page = 1 not in page_range
    show_first_page_divider = number_of_pages > number_of_pagination_links and 2 not in page_range
    show_last_page = number_of_pages not in page_range
    show_last_page_divider = number_of_pages > number_of_pagination_links and number_of_pages - 1 not in page_range

    return {
        "show_first_page": show_first_page,
        "show_first_page_divider": show_first_page_divider,
        "show_last_page": show_last_page,
        "show_last_page_divider": show_last_page_divider,
        "current_page": current_page,
        "has_next_page": current_page < number_of_pages,
        "next_page": current_page + 1,
        "has_prev_page": current_page > 1,
        "prev_page": current_page - 1,
        "number_of_pages": number_of_pages,
        "page_range": page_range,
    }
