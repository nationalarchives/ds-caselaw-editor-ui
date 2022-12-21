from caselawclient.Client import api_client
from requests_toolbelt.multipart import decoder
from judgments.models import SearchResults

def perform_advanced_search(
    query=None,
    court=None,
    judge=None,
    party=None,
    order=None,
    date_from=None,
    date_to=None,
    page=1,
    only_unpublished=False,
):
    response = api_client.advanced_search(
        q=query,
        court=court,
        judge=judge,
        party=party,
        page=page,
        order=order,
        date_from=date_from,
        date_to=date_to,
        show_unpublished=True,
        only_unpublished=only_unpublished,
    )
    multipart_data = decoder.MultipartDecoder.from_response(response)
    return SearchResults.create_from_string(multipart_data.parts[0].text)
