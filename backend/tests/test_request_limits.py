"""Limits on how much a caller may send.

The machine serving the shop has a few hundred megabytes of memory, and a
request is held while it is handled. Measuring a body after reading it offers
no protection, because the memory has already been spent by then.
"""

import asyncio
import uuid

import pytest
import requests
from starlette.requests import Request
from starlette.responses import Response

from app.config import MAX_REQUEST_BODY_BYTES, MAX_UPLOAD_BYTES
from app.middleware import (
    MULTIPART_OVERHEAD_BYTES,
    UPLOAD_PATH,
    limit_for,
    limit_request_size,
)


UPLOAD_BOUNDARY = "----nayara-test-boundary"


class TestConfiguredLimits:
    def test_ordinary_requests_have_a_modest_ceiling(self):
        assert MAX_REQUEST_BODY_BYTES == 1024 * 1024

    def test_uploads_are_allowed_more(self):
        assert MAX_UPLOAD_BYTES > MAX_REQUEST_BODY_BYTES

    def test_only_the_upload_route_gets_the_larger_ceiling(self):
        assert limit_for(UPLOAD_PATH) == MAX_UPLOAD_BYTES + MULTIPART_OVERHEAD_BYTES
        assert limit_for("/api/orders") == MAX_REQUEST_BODY_BYTES
        assert limit_for("/api/products") == MAX_REQUEST_BODY_BYTES


class TestOversizedBodies:
    def test_a_large_body_is_refused(self, base_url, anon_client):
        oversized = "x" * (MAX_REQUEST_BODY_BYTES + 1024)

        response = anon_client.post(
            f"{base_url}/api/contact",
            json={
                "name": "Too Much",
                "email": "toomuch@example.com",
                "subject": "Oversized",
                "message": oversized,
            },
        )

        assert response.status_code == 413

    def test_the_refusal_uses_the_standard_error_shape(self, base_url, anon_client):
        response = anon_client.post(
            f"{base_url}/api/contact",
            json={"message": "x" * (MAX_REQUEST_BODY_BYTES + 1024)},
        )

        body = response.json()
        assert isinstance(body["detail"], str)
        assert "too large" in body["detail"].lower()
        assert "request_id" in body

    def test_the_body_is_never_read(self, base_url, anon_client):
        """A refusal must not depend on parsing what was sent."""
        response = anon_client.post(
            f"{base_url}/api/auth/register",
            data=b"{" + b"x" * (MAX_REQUEST_BODY_BYTES + 1024),
            headers={"Content-Type": "application/json"},
        )

        # Unparseable, yet still refused on size rather than on syntax.
        assert response.status_code == 413

    def test_a_request_within_the_limit_is_handled(self, base_url, anon_client):
        response = anon_client.post(
            f"{base_url}/api/contact",
            json={
                "name": "Reasonable Sender",
                "email": "fine@example.com",
                "subject": "Within the limit",
                "message": "y" * 1000,
            },
        )

        assert response.status_code != 413


class TestMalformedLength:
    """A length that is not a number cannot be sent through a normal client:
    the HTTP library recomputes it and the server rejects a broken one before
    any application code runs. The branch is still reachable in principle, so
    it is exercised directly rather than through a request that would never
    arrive in that state."""

    def call_middleware(self, headers, path="/api/contact"):
        async def exercise():
            scope = {
                "type": "http",
                "http_version": "1.1",
                "method": "POST",
                "scheme": "http",
                "server": ("testserver", 80),
                "path": path,
                "raw_path": path.encode(),
                "query_string": b"",
                "root_path": "",
                "headers": [
                    (key.encode(), value.encode()) for key, value in headers.items()
                ],
                "client": ("testclient", 1234),
            }

            async def call_next(_request):
                return Response(status_code=200)

            return await limit_request_size(Request(scope), call_next)

        return asyncio.run(exercise())

    @pytest.mark.parametrize("value", ["abc", "not-a-number", "1.5"])
    def test_an_unreadable_length_is_refused(self, value):
        response = self.call_middleware({"content-length": value})

        assert response.status_code == 400

    def test_a_negative_length_is_refused(self):
        response = self.call_middleware({"content-length": "-5"})

        assert response.status_code == 400

    def test_a_missing_length_is_allowed_through(self):
        """A chunked body declares no length; the route counts those bytes."""
        response = self.call_middleware({})

        assert response.status_code == 200

    def test_a_length_within_the_limit_is_allowed_through(self):
        response = self.call_middleware({"content-length": "100"})

        assert response.status_code == 200

    def test_a_length_over_the_limit_is_refused(self):
        response = self.call_middleware(
            {"content-length": str(MAX_REQUEST_BODY_BYTES + 1)}
        )

        assert response.status_code == 413


class TestReadsAreNotLimited:
    def test_browsing_is_unaffected(self, base_url, anon_client):
        assert anon_client.get(f"{base_url}/api/products").status_code == 200

    def test_health_is_unaffected(self, base_url, anon_client):
        assert anon_client.get(f"{base_url}/api/health").status_code == 200


def multipart_stream(total_bytes, boundary=UPLOAD_BOUNDARY):
    """Yield a multipart body in pieces, so no Content-Length is sent."""
    yield (
        f"--{boundary}\r\n"
        'Content-Disposition: form-data; name="file"; filename="oversized.png"\r\n'
        "Content-Type: image/png\r\n\r\n"
    ).encode()
    sent = 0
    while sent < total_bytes:
        piece = b"x" * min(64 * 1024, total_bytes - sent)
        sent += len(piece)
        yield piece
    yield f"\r\n--{boundary}--\r\n".encode()


class TestUploadLimits:
    def test_an_oversized_upload_is_refused_on_its_declared_length(
        self, base_url, admin_session
    ):
        """Refused before the file reaches disk or memory."""
        payload = b"x" * (MAX_UPLOAD_BYTES + MULTIPART_OVERHEAD_BYTES + 1024)

        response = requests.post(
            f"{base_url}{UPLOAD_PATH}",
            files={"file": ("oversized.png", payload, "image/png")},
            headers={"Authorization": f"Bearer {admin_session['token']}"},
        )

        assert response.status_code == 413

    def test_an_oversized_upload_without_a_length_is_still_refused(
        self, base_url, admin_session
    ):
        """A chunked sender declares no length, so the route has to count.

        This is the case the previous check missed: it read the whole file
        first and only then compared its size.
        """
        response = requests.post(
            f"{base_url}{UPLOAD_PATH}",
            data=multipart_stream(MAX_UPLOAD_BYTES + 512 * 1024),
            headers={
                "Authorization": f"Bearer {admin_session['token']}",
                "Content-Type": f"multipart/form-data; boundary={UPLOAD_BOUNDARY}",
            },
        )

        assert response.status_code == 413

    def test_an_upload_still_requires_an_administrator(self, base_url, user_client):
        response = user_client.post(
            f"{base_url}{UPLOAD_PATH}",
            files={"file": ("small.png", b"x" * 100, "image/png")},
        )

        assert response.status_code == 403

    def test_an_unsupported_type_is_still_refused(self, base_url, admin_session):
        response = requests.post(
            f"{base_url}{UPLOAD_PATH}",
            files={"file": (f"{uuid.uuid4().hex}.exe", b"x" * 100, "application/x-msdownload")},
            headers={"Authorization": f"Bearer {admin_session['token']}"},
        )

        assert response.status_code == 400
