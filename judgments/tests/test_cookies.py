from django.test import TestCase

from judgments.context_processors import cookie_domain_from_host


class TestCookieDomainFromHost(TestCase):
    def test_keeps_localhost_unchanged(self):
        assert cookie_domain_from_host("localhost") == "localhost"
        assert cookie_domain_from_host("localhost:3000") == "localhost"

    def test_keeps_single_label_hosts_unchanged(self):
        assert cookie_domain_from_host("django") == "django"

    def test_keeps_ip_addresses_unchanged(self):
        assert cookie_domain_from_host("127.0.0.1") == "127.0.0.1"
        assert cookie_domain_from_host("[::1]:3000") == "::1"

    def test_returns_root_domain_for_subdomains(self):
        assert cookie_domain_from_host("www.example.com") == ".example.com"
        assert cookie_domain_from_host("service.sub.example.com") == ".example.com"

    def test_returns_root_domain_for_country_code_domains(self):
        assert cookie_domain_from_host("www.nationalarchives.gov.uk") == ".nationalarchives.gov.uk"
        assert cookie_domain_from_host("caselaw.nationalarchives.gov.uk") == ".nationalarchives.gov.uk"
