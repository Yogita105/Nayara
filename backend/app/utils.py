import re
from datetime import datetime


def serialize_doc(doc: dict) -> dict:
    if not doc:
        return doc
    doc.pop("_id", None)
    for key, value in list(doc.items()):
        if isinstance(value, datetime):
            doc[key] = value.isoformat()
    return doc


def public_user(user: dict) -> dict:
    result = {}
    for key in ("user_id", "mobile", "email", "name", "picture", "is_admin", "created_at"):
        value = user.get(key)
        result[key] = value.isoformat() if isinstance(value, datetime) else value
    return result


def normalize_indian_mobile(value: str) -> str:
    compact = re.sub(r"[\s()-]", "", value.strip())
    if compact.startswith("+91"):
        digits = compact[3:]
    elif compact.startswith("91") and len(compact) == 12:
        digits = compact[2:]
    elif compact.startswith("0") and len(compact) == 11:
        digits = compact[1:]
    else:
        digits = compact
    if len(digits) != 10 or not digits.isdigit() or digits[0] not in "6789":
        raise ValueError("Enter a valid 10-digit Indian mobile number")
    return f"+91{digits}"
