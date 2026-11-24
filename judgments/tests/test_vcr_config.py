from config.vcr_config import cassette_name_for_request


def test_cassette_name_ignores_waffle_flag_overrides():
    assert cassette_name_for_request("GET", "/eat/2023/1", "metadata_aside_judges=1") == "eat_2023_1_get"
    assert cassette_name_for_request(
        "GET",
        "/results",
        "query=Imperial&document_list_queue=1",
    ) == cassette_name_for_request("GET", "/results", "query=Imperial")
