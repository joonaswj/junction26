"""FastAPI routes exposing the S-Pankki data. Included in main.py."""

from __future__ import annotations

import json
from datetime import date

import pandas as pd
from fastapi import APIRouter, HTTPException, Query

from .loader import (
    load_customers,
    load_mortgage_events,
    load_mortgage_outcomes,
    load_transactions,
)

router = APIRouter(tags=["data"])


def _records(df: pd.DataFrame) -> list[dict]:
    # to_json turns NaN into null and timestamps into ISO strings.
    return json.loads(df.to_json(orient="records", date_format="iso"))


@router.get("/data/summary")
def summary():
    tx = load_transactions()
    outcomes = load_mortgage_outcomes()
    return {
        "customers": len(load_customers()),
        "transactions": len(tx),
        "first_tx_date": tx["tx_date"].min().date().isoformat(),
        "last_tx_date": tx["tx_date"].max().date().isoformat(),
        "categories": sorted(tx["category"].cat.categories),
        "mortgage_applications": len(outcomes),
        "mortgage_decisions": outcomes["final_decision"].value_counts().to_dict(),
    }


@router.get("/customers")
def list_customers(
    limit: int = Query(100, ge=1, le=10_000),
    offset: int = Query(0, ge=0),
    has_mortgage: bool | None = None,
):
    df = load_customers()
    if has_mortgage is not None:
        with_mtg = df["customer_id"].isin(load_mortgage_outcomes()["customer_id"])
        df = df[with_mtg if has_mortgage else ~with_mtg]
    return {"total": len(df), "items": _records(df.iloc[offset : offset + limit])}


@router.get("/customers/{customer_id}")
def get_customer(customer_id: str):
    customers = load_customers()
    row = customers[customers["customer_id"] == customer_id]
    if row.empty:
        raise HTTPException(404, f"Customer {customer_id} not found")
    outcomes = load_mortgage_outcomes()
    mortgages = outcomes[outcomes["customer_id"] == customer_id]
    return {**_records(row)[0], "mortgages": _records(mortgages)}


@router.get("/customers/{customer_id}/transactions")
def get_customer_transactions(
    customer_id: str,
    start: date | None = None,
    end: date | None = None,
    category: str | None = None,
    limit: int = Query(1000, ge=1, le=100_000),
    offset: int = Query(0, ge=0),
):
    df = load_transactions([customer_id])
    if df.empty and not load_customers()["customer_id"].eq(customer_id).any():
        raise HTTPException(404, f"Customer {customer_id} not found")
    if start:
        df = df[df["tx_date"] >= pd.Timestamp(start)]
    if end:
        df = df[df["tx_date"] <= pd.Timestamp(end)]
    if category:
        df = df[df["category"] == category]
    return {"total": len(df), "items": _records(df.iloc[offset : offset + limit])}


@router.get("/mortgages")
def list_mortgages(decision: str | None = None):
    df = load_mortgage_outcomes()
    if decision:
        df = df[df["final_decision"] == decision]
    return {"total": len(df), "items": _records(df)}


@router.get("/mortgages/{mortgage_customer_id}/events")
def get_mortgage_events(mortgage_customer_id: str):
    events = load_mortgage_events()
    df = events[events["mortgage_customer_id"] == mortgage_customer_id]
    if df.empty:
        raise HTTPException(404, f"Mortgage application {mortgage_customer_id} not found")
    return {"total": len(df), "items": _records(df)}
