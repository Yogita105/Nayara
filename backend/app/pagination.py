"""Shared paging parameters for list endpoints.

Offset paging is used because the admin screens need to jump to a known page.
Every paged query also sorts on an indexed field, otherwise skipping records
could return the same document twice or miss one entirely.
"""

from fastapi import Query

MAX_PAGE_SIZE = 500
TOTAL_COUNT_HEADER = "X-Total-Count"


def limit_query(default: int) -> Query:
    return Query(
        default,
        ge=1,
        le=MAX_PAGE_SIZE,
        description="Maximum number of records to return.",
    )


def offset_query() -> Query:
    return Query(
        0,
        ge=0,
        description="Number of records to skip before collecting results.",
    )
