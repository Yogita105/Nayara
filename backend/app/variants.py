"""Working out which form of a product is being bought.

A product is sold as one or more variants, and every line in a cart or an
order names one of them. Requests that predate variants do not, so a product
with a single variant resolves to it: that keeps older clients working without
a second code path, while a product with a real choice insists on being told.
"""

from typing import List, Optional

from .errors import FieldError


def variants_of(product: dict) -> List[dict]:
    return product.get("variants") or []


def find_variant(product: dict, variant_id: str) -> Optional[dict]:
    return next(
        (variant for variant in variants_of(product) if variant.get("variant_id") == variant_id),
        None,
    )


def resolve_variant(product: dict, variant_id: Optional[str]) -> dict:
    """The variant being bought, or a refusal explaining what is missing."""
    variants = variants_of(product)
    name = product.get("name", "This product")

    if not variants:
        # Every product is given a variant when it is created, so this means
        # a record written before that rule existed and never migrated.
        raise FieldError(409, "variant_id", f"{name} is not available to buy.")

    if variant_id:
        variant = find_variant(product, variant_id)
        if not variant:
            raise FieldError(404, "variant_id", f"That option of {name} is no longer available.")
        return variant

    if len(variants) == 1:
        return variants[0]

    option = product.get("option_name", "option").lower()
    raise FieldError(422, "variant_id", f"Choose a {option} for {name}.")


def line_key(product_id: str, variant_id: str) -> tuple:
    """What makes a cart or order line unique.

    Two sizes of the same product are two lines, not one, so the identity has
    to carry both parts.
    """
    return (product_id, variant_id)
