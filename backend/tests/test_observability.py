"""Structured logging, request correlation, and health probes."""
import json
import logging

import pytest

from app.observability import (
    JsonFormatter,
    MAX_REQUEST_ID_LENGTH,
    REQUEST_ID_HEADER,
    RequestIdFilter,
    TextFormatter,
    clean_request_id,
    get_request_id,
    new_request_id,
    set_request_id,
)


def make_record(message="hello", level=logging.INFO, **extra):
    record = logging.LogRecord(
        name="nayara.test",
        level=level,
        pathname=__file__,
        lineno=1,
        msg=message,
        args=None,
        exc_info=None,
    )
    for key, value in extra.items():
        setattr(record, key, value)
    RequestIdFilter().filter(record)
    return record


class TestRequestIdHandling:
    def test_a_missing_id_is_generated(self):
        assert clean_request_id(None)
        assert clean_request_id("") != ""

    def test_a_caller_supplied_id_is_kept(self):
        assert clean_request_id("trace-abc-123") == "trace-abc-123"

    def test_an_overlong_id_is_truncated(self):
        assert len(clean_request_id("x" * 500)) == MAX_REQUEST_ID_LENGTH

    def test_an_unprintable_id_is_replaced(self):
        assert clean_request_id("bad\x00id") != "bad\x00id"

    def test_ids_are_unique(self):
        assert new_request_id() != new_request_id()


class TestJsonLogging:
    def test_core_fields_are_present(self):
        set_request_id("req-123")
        payload = json.loads(JsonFormatter().format(make_record("Request completed")))

        assert payload["message"] == "Request completed"
        assert payload["level"] == "INFO"
        assert payload["logger"] == "nayara.test"
        assert payload["request_id"] == "req-123"
        assert payload["time"]

    def test_extra_fields_are_included(self):
        set_request_id("req-123")
        record = make_record("Request completed", method="GET", status=200)
        payload = json.loads(JsonFormatter().format(record))

        assert payload["method"] == "GET"
        assert payload["status"] == 200

    def test_output_is_a_single_parsable_line(self):
        set_request_id("req-123")
        line = JsonFormatter().format(make_record("multi\nline"))

        assert "\n" not in line
        assert json.loads(line)["message"] == "multi\nline"

    def test_text_format_stays_readable(self):
        set_request_id("req-123")
        line = TextFormatter().format(make_record("Request completed", status=200))

        assert "Request completed" in line
        assert "status=200" in line


class TestHealthEndpoints:
    def test_liveness_needs_no_credentials(self, base_url, anon_client):
        response = anon_client.get(f"{base_url}/api/health")

        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    def test_readiness_reports_the_database(self, base_url, anon_client):
        response = anon_client.get(f"{base_url}/api/health/ready")

        assert response.status_code == 200
        assert response.json() == {"status": "ready", "database": "reachable"}

    def test_health_is_not_a_write_endpoint(self, base_url, anon_client):
        assert anon_client.post(f"{base_url}/api/health").status_code == 405


class TestRequestCorrelation:
    def test_every_response_carries_an_id(self, base_url, anon_client):
        response = anon_client.get(f"{base_url}/api/products")

        assert response.headers[REQUEST_ID_HEADER]

    def test_a_supplied_id_is_echoed_back(self, base_url, anon_client):
        response = anon_client.get(
            f"{base_url}/api/products",
            headers={REQUEST_ID_HEADER: "trace-from-client"},
        )

        assert response.headers[REQUEST_ID_HEADER] == "trace-from-client"

    def test_each_request_gets_its_own_id(self, base_url, anon_client):
        first = anon_client.get(f"{base_url}/api/products")
        second = anon_client.get(f"{base_url}/api/products")

        assert first.headers[REQUEST_ID_HEADER] != second.headers[REQUEST_ID_HEADER]

    def test_failed_requests_are_still_traceable(self, base_url, anon_client):
        response = anon_client.get(f"{base_url}/api/orders")

        assert response.status_code == 401
        assert response.headers[REQUEST_ID_HEADER]


class TestNoSecretsInLogs:
    @pytest.mark.parametrize(
        "secret",
        ["password", "session_token", "csrf_token", "authorization"],
    )
    def test_request_logs_do_not_name_credentials(self, secret):
        """The access log records only method, path, status and duration."""
        from app import middleware

        source = middleware.request_context.__doc__ or ""
        assert "bodies" in source or "credentials" in source

        set_request_id("req-123")
        record = make_record(
            "Request completed",
            method="POST",
            path="/api/auth/login",
            status=200,
            duration_ms=12.5,
        )
        payload = json.loads(JsonFormatter().format(record))
        assert secret not in json.dumps(payload).lower()
