"""Stage 28F Finance / Insurance taxonomy contract package."""

from .manifest import get_finance_insurance_taxonomy_manifest
from .validation import validate_finance_insurance_taxonomy_manifest

__all__ = [
    "get_finance_insurance_taxonomy_manifest",
    "validate_finance_insurance_taxonomy_manifest",
]
