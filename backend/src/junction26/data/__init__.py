"""S-Pankki challenge data. See loader.py for usage."""

from .download import data_dir, download_all
from .loader import (
    load_customers,
    load_mortgage_events,
    load_mortgage_outcomes,
    load_transactions,
)

__all__ = [
    "data_dir",
    "download_all",
    "load_customers",
    "load_mortgage_events",
    "load_mortgage_outcomes",
    "load_transactions",
]
