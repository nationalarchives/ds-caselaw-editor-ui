import csv
from datetime import datetime

import pytz
from django.http import HttpResponse
from django.views.generic import TemplateView

from judgments.utils import api_client


class Stats(TemplateView):
    template_name = "pages/stats.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["page_title"] = "Stats"

        return context


class CSVStreamBuffer:
    def write(self, value):
        return value


def stream_combined_stats_table_as_csv(request):
    response = HttpResponse(
        content_type="text/csv",
        headers={
            "Content-Disposition": 'attachment; filename="tna-fcl-combined-stats-{datetime}.csv"'.format(
                datetime=datetime.now(pytz.timezone("Europe/London")).strftime(
                    "%Y%m%d%H%M%S",
                ),
            ),
        },
    )

    writer = csv.writer(response)

    for row in api_client.get_combined_stats_table():
        writer.writerow(row)

    return response
