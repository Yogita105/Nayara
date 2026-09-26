"""Authorization coverage for every API endpoint.

Rather than listing a handful of endpoints by hand, this discovers the routes
the application actually registers and checks each one against its expected
audience. A new endpoint that nobody classified fails the suite, which forces
a deliberate decision about who may call it instead of letting an unprotected
route reach production unnoticed.

Discovery reads the generated OpenAPI schema, which is a supported interface
and survives FastAPI reorganising its internals. A route registered with
``include_in_schema=False`` would be absent from that schema, so hiding an
endpoint from the documentation also hides it from this check: such a route
has to be given an audience by hand.
"""

import re
import sys
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.main import app  # noqa: E402

# Substituted for path parameters. Deliberately cannot match a real record, so
# a route that wrongly allows the caller through fails on authorization rather
# than quietly acting on somebody's data.
PROBE_ID = "authz-probe-does-not-exist"

# Only administrators may call these.
ADMIN_ROUTES = {
    ("GET", "/api/admin/bulk-inquiries"),
    ("PUT", "/api/admin/bulk-inquiries/{inquiry_id}"),
    ("GET", "/api/admin/contacts"),
    ("GET", "/api/admin/orders"),
    ("PUT", "/api/admin/orders/{order_id}"),
    ("GET", "/api/admin/stats"),
    ("POST", "/api/admin/upload"),
    ("GET", "/api/admin/users"),
    ("PUT", "/api/admin/settings/business"),
    ("POST", "/api/products"),
    ("PUT", "/api/products/{product_id}"),
    ("DELETE", "/api/products/{product_id}"),
}

# Any signed-in customer may call these; anonymous callers may not.
AUTHENTICATED_ROUTES = {
    ("GET", "/api/auth/me"),
    ("POST", "/api/auth/logout-all"),
    ("POST", "/api/auth/password"),
    ("PUT", "/api/auth/profile"),
    ("GET", "/api/cart"),
    ("POST", "/api/cart"),
    ("DELETE", "/api/cart"),
    ("PUT", "/api/cart/{product_id}"),
    ("DELETE", "/api/cart/{product_id}"),
    ("GET", "/api/orders"),
    ("POST", "/api/orders"),
    ("GET", "/api/orders/{order_id}"),
    ("POST", "/api/products/{product_id}/reviews"),
    ("GET", "/api/wishlist"),
    ("POST", "/api/wishlist"),
    ("DELETE", "/api/wishlist/{product_id}"),
}

# Deliberately reachable without signing in.
PUBLIC_ROUTES = {
    ("GET", "/api/"),
    ("GET", "/api/health"),
    ("GET", "/api/health/ready"),
    ("POST", "/api/auth/login"),
    ("POST", "/api/auth/register"),
    # Signing out deliberately succeeds even without a valid session: it still
    # clears the browser's cookies, so an expired session cannot leave someone
    # stuck appearing signed in.
    ("POST", "/api/auth/logout"),
    ("POST", "/api/contact"),
    ("POST", "/api/bulk-inquiry"),
    ("GET", "/api/files/{file_id}"),
    ("GET", "/api/products"),
    ("GET", "/api/products/{product_id}"),
    # The footer on every page shows how to reach the shop, so a stranger has
    # to be able to read it.
    ("GET", "/api/settings/business"),
    ("GET", "/api/products/{product_id}/reviews"),
}

CLASSIFIED = ADMIN_ROUTES | AUTHENTICATED_ROUTES | PUBLIC_ROUTES


def _discover_api_routes():
    schema = app.openapi()
    return {
        (method.upper(), path)
        for path, operations in schema.get("paths", {}).items()
        if path.startswith("/api")
        for method in operations
        if method.upper() not in {"HEAD", "OPTIONS"}
    }


DISCOVERED = _discover_api_routes()


def _url(base_url, path):
    return base_url + re.sub(r"\{[^}]+\}", PROBE_ID, path)


def test_every_api_route_is_classified():
    """A new endpoint must be assigned an audience before it can ship."""
    unclassified = DISCOVERED - CLASSIFIED
    assert not unclassified, (
        "These endpoints are not listed in any audience group. Add each one to "
        "ADMIN_ROUTES, AUTHENTICATED_ROUTES or PUBLIC_ROUTES in this file after "
        f"deciding who may call it: {sorted(unclassified)}"
    )


def test_classification_has_no_stale_entries():
    """Keep the lists honest, so a deleted route cannot fake coverage."""
    missing = CLASSIFIED - DISCOVERED
    assert not missing, (
        "These endpoints are classified here but no longer exist. Remove them "
        f"from this file: {sorted(missing)}"
    )


def test_route_groups_do_not_overlap():
    assert not (ADMIN_ROUTES & AUTHENTICATED_ROUTES)
    assert not (ADMIN_ROUTES & PUBLIC_ROUTES)
    assert not (AUTHENTICATED_ROUTES & PUBLIC_ROUTES)


@pytest.mark.parametrize("method,path", sorted(ADMIN_ROUTES))
def test_admin_route_rejects_anonymous(anon_client, base_url, method, path):
    response = anon_client.request(method, _url(base_url, path))
    assert (
        response.status_code == 401
    ), f"{method} {path} should require signing in, got {response.status_code}"


@pytest.mark.parametrize("method,path", sorted(ADMIN_ROUTES))
def test_admin_route_rejects_regular_user(user_client, base_url, method, path):
    response = user_client.request(method, _url(base_url, path))
    assert (
        response.status_code == 403
    ), f"{method} {path} should be refused to a customer, got {response.status_code}"


@pytest.mark.parametrize("method,path", sorted(AUTHENTICATED_ROUTES))
def test_authenticated_route_rejects_anonymous(anon_client, base_url, method, path):
    response = anon_client.request(method, _url(base_url, path))
    assert (
        response.status_code == 401
    ), f"{method} {path} should require signing in, got {response.status_code}"


@pytest.mark.parametrize("method,path", sorted(PUBLIC_ROUTES))
def test_public_route_does_not_demand_credentials(anon_client, base_url, method, path):
    """Guards against a public route being locked down by accident."""
    response = anon_client.request(method, _url(base_url, path))
    assert response.status_code not in (
        401,
        403,
    ), f"{method} {path} is meant to be public, got {response.status_code}"


def test_admin_rejection_does_not_reveal_whether_record_exists(user_client, base_url):
    """A customer probing admin endpoints learns nothing about the data."""
    response = user_client.request(
        "PUT", _url(base_url, "/api/admin/orders/{order_id}"), json={"status": "shipped"}
    )
    assert response.status_code == 403
    body = response.json()
    assert PROBE_ID not in str(body)


def test_documentation_routes_follow_the_configured_setting():
    """The schema lists the whole admin API, so its exposure stays deliberate.

    Guards against the documentation being switched back on unconditionally,
    which would publish a map of the admin API on a live deployment.
    """
    from app.config import API_DOCS_ENABLED

    doc_paths = {"/docs", "/redoc", "/openapi.json"}
    registered = {getattr(route, "path", "") for route in app.routes}
    exposed = doc_paths & registered

    if API_DOCS_ENABLED:
        assert exposed == doc_paths, f"Expected documentation routes, found {exposed}"
    else:
        assert not exposed, f"Documentation should be withheld, found {exposed}"
