"""Load the S-Pankki dataset as pandas DataFrames.

    from junction26.data import load_transactions, load_customers

    tx = load_transactions()              # ~3.6M rows
    tx = load_transactions(["CUST00001"]) # filter to some customers

Each loader is cached in memory, so repeated calls are free. The
transactions CSV is slow to parse, so the parsed DataFrame is also cached on
disk in backend/data/cache (a pickle, rebuilt when the CSV changes).

Download the raw files first: `uv run python -m junction26.data.download`.
"""

from __future__ import annotations

from collections.abc import Iterable
from functools import lru_cache
from pathlib import Path

import pandas as pd

from .download import data_dir

TRANSACTIONS = "tx_junction_transactions.csv"
CUSTOMERS = "tx_customers_junction.csv"
MORTGAGE_EVENTS = "mtg_negotiation_history.csv"
MORTGAGE_OUTCOMES = "mtg_tx_customer_link_and_final_mtg_infio.csv"

# Timestamps look like 03OCT24:09:04:04 (SAS DATETIME format).
SAS_DATETIME = "%d%b%y:%H:%M:%S"


def _path(name: str) -> Path:
    path = data_dir() / name
    if not path.exists():
        raise FileNotFoundError(
            f"{path} is missing. Run `uv run python -m junction26.data.download` "
            "in the backend directory first."
        )
    return path


def _read_csv(name: str, **kwargs) -> pd.DataFrame:
    # The CSVs start with a UTF-8 BOM.
    return pd.read_csv(_path(name), encoding="utf-8-sig", **kwargs)


def _parse_sas(col: pd.Series) -> pd.Series:
    return pd.to_datetime(col, format=SAS_DATETIME)


@lru_cache(maxsize=1)
def _all_transactions() -> pd.DataFrame:
    csv = _path(TRANSACTIONS)
    cache = csv.parent.parent / "cache" / "transactions.pkl"
    if cache.exists() and cache.stat().st_mtime >= csv.stat().st_mtime:
        return pd.read_pickle(cache)

    df = _read_csv(
        TRANSACTIONS,
        dtype={
            "customer_id": "category",
            "bank_account_id": "category",
            "category": "category",
            "transaction_type": "category",
            "merchant_id": "category",
            "mcc_code": "category",
            "tx_amount_eur": "float64",
            "balance_after_eur": "float64",
        },
        parse_dates=["tx_date"],
    )
    df["tx_timestamp"] = _parse_sas(df["tx_timestamp"])

    cache.parent.mkdir(parents=True, exist_ok=True)
    df.to_pickle(cache)
    return df


def load_transactions(customer_ids: Iterable[str] | None = None) -> pd.DataFrame:
    """Bank transactions, one row per transaction.

    Columns: customer_id, bank_account_id, tx_date, tx_timestamp, category,
    tx_amount_eur (negative = money out), balance_after_eur,
    transaction_type, merchant_id, mcc_code.
    """
    df = _all_transactions()
    if customer_ids is None:
        return df
    return df[df["customer_id"].isin(list(customer_ids))].reset_index(drop=True)


@lru_cache(maxsize=1)
def load_customers() -> pd.DataFrame:
    """Customers: customer_id, customer_postal_code, customer_age."""
    # Postal codes have leading zeros, keep them as strings.
    return _read_csv(CUSTOMERS, dtype={"customer_postal_code": str})


@lru_cache(maxsize=1)
def load_mortgage_events() -> pd.DataFrame:
    """Mortgage application event history, one row per event.

    Keyed by mortgage_customer_id (C0004...), not customer_id. Join through
    load_mortgage_outcomes() to get to transactions.
    """
    df = _read_csv(MORTGAGE_EVENTS)
    df["timestamp"] = _parse_sas(df["timestamp"])
    return df.sort_values(["mortgage_customer_id", "timestamp"], ignore_index=True)


@lru_cache(maxsize=1)
def load_mortgage_outcomes() -> pd.DataFrame:
    """One row per mortgage application: link to customer_id plus final outcome.

    Columns: mortgage_customer_id, customer_id, final_decision,
    rejection_reason, final_property_price_eur, final_requested_loan_eur,
    final_equity_amount_eur, final_collateral_value_eur,
    required_monthly_income_eur, final_loan_to_value.
    """
    df = _read_csv(MORTGAGE_OUTCOMES)
    # Fix a typo in the source column name.
    return df.rename(columns={"lfinal_loan_to_value": "final_loan_to_value"})
