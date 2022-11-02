import json
import logging
import math
import re
import time
import xml.etree.ElementTree as ET
from typing import Optional, Union

import boto3
import botocore.client
import caselawclient.xml_tools as xml_tools
import environ
from caselawclient.Client import (
    RESULTS_PER_PAGE,
    MarklogicAPIError,
    MarklogicResourceNotFoundError,
    api_client,
)
from caselawclient.xml_tools import JudgmentMissingMetadataError
from django.contrib import messages
from django.contrib.auth.models import User
from django.http import Http404, HttpResponse, HttpResponseBadRequest
from django.shortcuts import redirect
from django.template import loader
from django.urls import reverse
from django.utils.translation import gettext
from django.views.generic import View
from requests_toolbelt.multipart import decoder

from judgments.models import SearchResult, SearchResults
from judgments.utils import (
    MoveJudgmentError,
    NeutralCitationToUriError,
    get_judgment_root,
    update_judgment_uri,
    uri_for_s3,
)

env = environ.Env()
akn_namespace = {"akn": "http://docs.oasis-open.org/legaldocml/ns/akn/3.0"}
uk_namespace = {"uk": "https://caselaw.nationalarchives.gov.uk/akn"}
VERSION_REGEX = r"(\d+)-(\d+|TDR)"


class EditJudgmentView(View):
    def get_judgment(self, uri: str):
        try:
            judgment_xml = api_client.get_judgment_xml(uri, show_unpublished=True)
            return ET.XML(bytes(judgment_xml, encoding="utf-8"))
        except MarklogicResourceNotFoundError as e:
            raise Http404(f"Judgment XML was not found at uri {uri}, {e}")

    def get_metadata(self, uri: str, judgment: ET.Element) -> dict:
        meta = dict()

        try:
            meta["published"] = api_client.get_published(uri)
            meta["sensitive"] = api_client.get_sensitive(uri)
            meta["supplemental"] = api_client.get_supplemental(uri)
            meta["anonymised"] = api_client.get_anonymised(uri)
            meta["metadata_name"] = xml_tools.get_metadata_name_value(judgment) or ""
            meta["page_title"] = meta["metadata_name"]
            meta["court"] = xml_tools.get_court_value(judgment) or ""
            meta["neutral_citation"] = (
                xml_tools.get_neutral_citation_name_value(judgment) or ""
            )
            meta["judgment_date"] = xml_tools.get_judgment_date_value(judgment) or ""
            meta["docx_url"] = generate_docx_url(uri_for_s3(uri))
            meta["pdf_url"] = generate_pdf_url(uri_for_s3(uri))
            meta["previous_versions"] = self.get_versions(uri)
            meta["consignment_reference"] = api_client.get_property(
                uri, "transfer-consignment-reference"
            )
            meta["source_name"] = api_client.get_property(uri, "source-name")
            meta["source_email"] = api_client.get_property(uri, "source-email")
            meta["assigned_to"] = api_client.get_property(uri, "assigned-to")
            meta["is_editable"] = True
        except JudgmentMissingMetadataError:
            meta[
                "error"
            ] = "The Judgment is missing correct metadata structure and cannot be edited"

        return meta

    def get_versions(self, uri: str):
        versions_response = api_client.list_judgment_versions(uri)
        try:
            decoded_versions = decoder.MultipartDecoder.from_response(versions_response)
            return render_versions(decoded_versions.parts)
        except AttributeError:
            return []

    def render(self, request, context):
        template = loader.get_template("judgment/edit.html")
        return HttpResponse(template.render({"context": context}, request))

    def get(self, request, *args, **kwargs):
        params = request.GET
        judgment_uri = params.get("judgment_uri")
        context = {"judgment_uri": judgment_uri}
        judgment = self.get_judgment(judgment_uri)
        context.update(self.get_metadata(judgment_uri, judgment))
        users = User.objects.all()
        users_dict = [
            {
                "name": u.get_username(),
                "print_name": u.get_full_name() or u.get_username(),
            }
            for u in users
        ]
        context.update({"users": users_dict})

        return self.render(request, context)

    def post(self, request, *args, **kwargs):
        judgment_uri = request.POST["judgment_uri"]
        published = bool(request.POST.get("published", False))
        sensitive = bool(request.POST.get("sensitive", False))
        supplemental = bool(request.POST.get("supplemental", False))
        anonymised = bool(request.POST.get("anonymised", False))

        context = {"judgment_uri": judgment_uri}
        try:
            api_client.set_published(judgment_uri, published)
            api_client.set_sensitive(judgment_uri, sensitive)
            api_client.set_supplemental(judgment_uri, supplemental)
            api_client.set_anonymised(judgment_uri, anonymised)

            if published:
                publish_documents(uri_for_s3(judgment_uri))
            else:
                unpublish_documents(uri_for_s3(judgment_uri))

            # Set name
            new_name = request.POST["metadata_name"]
            api_client.set_judgment_name(judgment_uri, new_name)

            # Set neutral citation
            new_citation = request.POST["neutral_citation"]
            api_client.set_judgment_citation(judgment_uri, new_citation)

            # Set court
            new_court = request.POST["court"]
            api_client.set_judgment_court(judgment_uri, new_court)

            # Date
            new_date = request.POST["judgment_date"]
            api_client.set_judgment_date(judgment_uri, new_date)

            # Assignment
            # TODO consider validating assigned_to is a user?
            if new_assignment := request.POST["assigned_to"]:
                api_client.set_property(judgment_uri, "assigned-to", new_assignment)

            # If judgment_uri is a `failure` URI, amend it to match new neutral citation and redirect
            if "failures" in judgment_uri and new_citation is not None:
                new_judgment_uri = update_judgment_uri(judgment_uri, new_citation)
                return redirect(reverse("edit") + f"?judgment_uri={new_judgment_uri}")

            if published:
                notify_status = "published"
            else:
                notify_status = "not published"
            notify_changed(
                uri=judgment_uri,
                status=notify_status,
                enrich=published,  # placeholder for now, should perhaps be "has this become published"
            )

            context["success"] = "Judgment successfully updated"

        except (MoveJudgmentError, NeutralCitationToUriError) as e:

            context[
                "error"
            ] = f"There was an error updating the Judgment's neutral citation: {e}"

        except MarklogicAPIError as e:
            context["error"] = f"There was an error saving the Judgment: {e}"

        xml = self.get_judgment(judgment_uri)
        context.update(self.get_metadata(judgment_uri, xml))
        invalidate_caches(judgment_uri)

        return self.render(request, context)


def detail(request):
    params = request.GET
    judgment_uri = params.get("judgment_uri", None)
    version_uri = params.get("version_uri", None)
    context = {"judgment_uri": judgment_uri, "is_failure": False}

    try:
        judgment_xml = api_client.get_judgment_xml(judgment_uri, show_unpublished=True)
        judgment_root = get_judgment_root(judgment_xml)
        context["is_editable"] = True
        if "failures" in judgment_uri:
            context["is_failure"] = True

        if "error" in judgment_root:
            context["is_editable"] = False
            judgment = judgment_xml
            metadata_name = judgment_uri
        else:
            results = api_client.eval_xslt(
                judgment_uri, version_uri, show_unpublished=True
            )
            metadata_name = api_client.get_judgment_name(judgment_uri)

            multipart_data = decoder.MultipartDecoder.from_response(results)
            judgment = multipart_data.parts[0].text
        context["judgment"] = judgment
        context["page_title"] = metadata_name
        context["docx_url"] = generate_docx_url(uri_for_s3(judgment_uri))
        context["pdf_url"] = generate_pdf_url(uri_for_s3(judgment_uri))

        if version_uri:
            try:
                version = re.search(VERSION_REGEX, version_uri).group(1)
            except AttributeError:
                version = None
            context["version"] = version
    except MarklogicResourceNotFoundError as e:
        raise Http404(f"Judgment was not found at uri {judgment_uri}, {e}")
    template = loader.get_template("judgment/detail.html")
    return HttpResponse(template.render({"context": context}, request))


def detail_xml(request):
    params = request.GET
    judgment_uri = params.get("judgment_uri", None)
    try:
        judgment_xml = api_client.get_judgment_xml(judgment_uri, show_unpublished=True)
    except MarklogicResourceNotFoundError as e:
        raise Http404(f"Judgment was not found at uri {judgment_uri}, {e}")

    response = HttpResponse(judgment_xml, content_type="application/xml")
    response["Content-Disposition"] = f"attachment; filename={judgment_uri}.xml"
    return response


def delete(request):
    judgment_uri = request.POST.get("judgment_uri", None)
    context = {
        "judgment_uri": judgment_uri,
        "page_title": gettext("judgment.delete_a_judgment"),
    }
    try:
        api_client.delete_judgment(judgment_uri)

        delete_documents(judgment_uri)
    except MarklogicResourceNotFoundError as e:
        raise Http404(f"Judgment was not found at uri {judgment_uri}, {e}")

    template = loader.get_template("judgment/deleted.html")

    messages.success(request, "Judgment deleted.")
    return HttpResponse(template.render({"context": context}, request))


def hold_judgment_button(request):
    judgment_uri = request.POST["judgment_uri"]
    # we probably shouldn't hold if the judgment isn't assigned but we won't check
    hold = request.POST["hold"]
    if hold not in ["false", "true"]:
        raise RuntimeError("Hold value must be '0' or '1'")
    api_client.set_property(judgment_uri, "editor-hold", hold)
    target_uri = request.META.get("HTTP_REFERER") or "/"
    if hold == "true":
        word = "held"
    else:
        word = "released"
    messages.success(request, f"Judgment {word}.")
    return redirect(target_uri)


def assign_judgment_button(request):
    judgment_uri = request.POST["judgment_uri"]
    api_client.set_property(judgment_uri, "assigned-to", request.user.username)
    target_uri = request.META.get("HTTP_REFERER") or "/"
    messages.success(request, "Judgment assigned to you.")
    return redirect(target_uri)


def prioritise_judgment_button(request):
    """Editors can let other editors know that some judgments are more important than others."""

    def parse_priority(priority: Union[str, int]) -> Optional[str]:
        # note: use 09 if using numbers less than 10.
        priorities = {"low": "10", "medium": "20", "high": "30"}
        priority_string = priority.lower().strip()
        return priorities.get(priority_string)

    judgment_uri = request.POST["judgment_uri"]
    priority = parse_priority(request.POST["priority"])
    if priority:
        api_client.set_property(judgment_uri, "editor-priority", priority)
        target_uri = request.META.get("HTTP_REFERER") or "/"

        messages.success(request, "Judgment priority set.")
        return redirect(target_uri)

    return HttpResponseBadRequest("Priority string not recognised")


def index(request):
    context = {}
    try:
        params = request.GET
        page = params.get("page") if params.get("page") else "1"
        order = (
            params.get("order") if params.get("order") in ["date", "-date"] else "-date"
        )
        model = perform_advanced_search(order=order, only_unpublished=True, page=page)
        search_results = [
            SearchResult.create_from_node(result) for result in model.results
        ]

        context["recent_judgments"] = list(filter(None, search_results))
        context["count_judgments"] = model.total
        context["paginator"] = paginator(int(page), model.total)
        context["order"] = order

    except MarklogicResourceNotFoundError as e:
        raise Http404(
            f"Search results not found, {e}"
        )  # TODO: This should be something else!
    template = loader.get_template("pages/home.html")
    return HttpResponse(template.render({"context": context}, request))


def results(request):
    context = {"page_title": gettext("results.search.title")}

    try:
        params = request.GET
        query = params.get("query")
        page = params.get("page") if params.get("page") else "1"

        if query:
            model = perform_advanced_search(query=query, page=page)

            context["search_results"] = [
                SearchResult.create_from_node(result) for result in model.results
            ]
            context["total"] = model.total
            context["paginator"] = paginator(int(page), model.total)
            context["query_string"] = f"query={query}"
        else:
            model = perform_advanced_search(order="-date", page=page)
            search_results = [
                SearchResult.create_from_node(result) for result in model.results
            ]
            context["recent_judgments"] = search_results

            context["total"] = model.total
            context["search_results"] = search_results
            context["paginator"] = paginator(int(page), model.total)
    except MarklogicAPIError as e:
        raise Http404(f"Search error, {e}")  # TODO: This should be something else!
    template = loader.get_template("judgment/results.html")
    return HttpResponse(template.render({"context": context}, request))


def get_parser_log(uri: str) -> str:
    s3 = create_s3_client()
    private_bucket = env("PRIVATE_ASSET_BUCKET", None)
    # Locally, we may not have an S3 bucket set up; continue as best we can.
    if not private_bucket:
        return ""

    try:
        parser_log = s3.get_object(Bucket=private_bucket, Key=f"{uri}/parser.log")
        return parser_log["Body"].read().decode("utf-8")
    except KeyError:
        return ""


def paginator(current_page, total):
    size_per_page = RESULTS_PER_PAGE
    number_of_pages = math.ceil(int(total) / size_per_page)
    next_pages = list(
        range(current_page + 1, min(current_page + 10, number_of_pages) + 1)
    )

    return {
        "current_page": current_page,
        "has_next_page": current_page < number_of_pages,
        "next_page": current_page + 1,
        "has_prev_page": current_page > 1,
        "prev_page": current_page - 1,
        "next_pages": next_pages,
        "number_of_pages": number_of_pages,
    }


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


def render_versions(decoded_versions):
    versions = [
        {
            "uri": part.text.rstrip(".xml"),
            "version": extract_version(part.text),
        }
        for part in decoded_versions
    ]
    sorted_versions = sorted(versions, key=lambda d: -d["version"])
    return sorted_versions


def extract_version(version_string: str) -> int:
    try:
        return int(re.search(VERSION_REGEX, version_string).group(1))
    except AttributeError:
        return 0


def delete_from_bucket(uri: str, bucket: str) -> None:
    client = create_s3_client()
    response = client.list_objects(Bucket=bucket, Prefix=uri)

    if response.get("Contents"):
        objects_to_delete = [
            {"Key": obj["Key"]} for obj in response.get("Contents", [])
        ]
        client.delete_objects(
            Bucket=bucket,
            Delete={
                "Objects": objects_to_delete,
            },
        )


def delete_documents(uri: str) -> None:
    unpublish_documents(uri)
    delete_from_bucket(uri, env("PRIVATE_ASSET_BUCKET"))


def publish_documents(uri: str) -> None:
    client = create_s3_client()

    public_bucket = env("PUBLIC_ASSET_BUCKET")
    private_bucket = env("PRIVATE_ASSET_BUCKET")

    response = client.list_objects(Bucket=private_bucket, Prefix=uri)

    for result in response.get("Contents", []):
        key = str(result["Key"])

        if not key.endswith("parser.log") and not key.endswith(".tar.gz"):
            source = {"Bucket": private_bucket, "Key": key}
            extra_args = {"ACL": "public-read"}
            try:
                client.copy(source, public_bucket, key, extra_args)
            except botocore.client.ClientError as e:
                logging.warning(
                    f"Unable to copy file {key} to new location {public_bucket}, error: {e}"
                )


def unpublish_documents(uri: str) -> None:
    delete_from_bucket(uri, env("PUBLIC_ASSET_BUCKET"))


def notify_changed(uri: str, status: str, enrich: bool = False) -> None:
    client = create_aws_client("sns")

    message_attributes = {}
    message_attributes["update_type"] = {
        "DataType": "String",
        "StringValue": status,
    }
    message_attributes["uri_reference"] = {
        "DataType": "String",
        "StringValue": uri,
    }
    if enrich:
        message_attributes["trigger_enrichment"] = {
            "DataType": "String",
            "StringValue": "1",
        }

    client.publish(
        TopicArn=env("SNS_TOPIC"),
        Message=json.dumps({"uri_reference": uri, "status": status}),
        Subject=f"Updated: {uri} {status}",
        MessageAttributes=message_attributes,
    )


def invalidate_caches(uri: str) -> None:
    if (
        env("CLOUDFRONT_INVALIDATION_ACCESS_KEY_ID", default=None) is None
        and env("CLOUDFRONT_INVALIDATION_ACCESS_SECRET", default=None) is None
    ):
        logging.warning(
            "Cannot invalidate cache: no cloudfront environment variables set"
        )
        return

    aws = boto3.session.Session(
        aws_access_key_id=env("CLOUDFRONT_INVALIDATION_ACCESS_KEY_ID", default=None),
        aws_secret_access_key=env(
            "CLOUDFRONT_INVALIDATION_ACCESS_SECRET", default=None
        ),
    )
    cloudfront = aws.client("cloudfront")
    cloudfront.create_invalidation(
        DistributionId=env("CLOUDFRONT_PUBLIC_DISTRIBUTION_ID"),
        InvalidationBatch={
            "Paths": {"Quantity": 1, "Items": ["/*"]},
            "CallerReference": str(time.time()),
        },
    )


def create_aws_client(service: str):  # service
    """@param: service The AWS service, e.g. 's3'"""
    aws = boto3.session.Session(
        aws_access_key_id=env("AWS_ACCESS_KEY_ID", default=None),
        aws_secret_access_key=env("AWS_SECRET_KEY", default=None),
    )
    return aws.client(
        service,
        endpoint_url=env("AWS_ENDPOINT_URL", default=None),
        region_name=env("PRIVATE_ASSET_BUCKET_REGION", default=None),
        config=botocore.client.Config(signature_version="s3v4"),
    )


def create_s3_client():
    """We can rename all the places this is called later"""
    return create_aws_client("s3")


def generate_docx_url(uri: str):
    # If there isn't a PRIVATE_ASSET_BUCKET, don't try to get the bucket.
    # This helps local environment setup where we don't use S3.
    bucket = env("PRIVATE_ASSET_BUCKET", None)
    if not bucket:
        return ""

    client = create_s3_client()

    key = f'{uri}/{uri.replace("/", "_")}.docx'

    return client.generate_presigned_url(
        "get_object", Params={"Bucket": bucket, "Key": key}
    )


def generate_pdf_url(uri: str):
    bucket = env("PRIVATE_ASSET_BUCKET", None)
    if not bucket:
        return ""

    client = create_s3_client()

    key = f'{uri}/{uri.replace("/", "_")}.pdf'

    return client.generate_presigned_url(
        "get_object", Params={"Bucket": bucket, "Key": key}
    )
