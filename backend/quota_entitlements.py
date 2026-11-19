"""
Phase 2.3: verified purchased-view entitlement validation.

This pure helper accepts only explicit, server-recorded quota entitlement
fields on a payment transaction. It intentionally does NOT use
estimated_impressions or other browser-supplied campaign estimates.
"""

from datetime import datetime, timezone
from typing import Any, Dict


def build_paid_view_entitlement(
    transaction: Dict[str, Any],
    campaign: Dict[str, Any],
    *,
    created_at: str = "",
) -> Dict[str, Any]:
    """Build an entitlement record from a paid transaction and its campaign.

    Raises ValueError unless the transaction is completed/paid, belongs to
    the campaign advertiser, references the same campaign, and contains an
    explicit positive integer quota_entitlement_views field.

    This function does not write to MongoDB or activate campaign publishing.
    """
    session_id = str(transaction.get("session_id") or "").strip()
    tx_campaign_id = str(transaction.get("campaign_id") or "").strip()
    campaign_id = str(campaign.get("id") or campaign.get("_id") or "").strip()
    tx_user_id = str(transaction.get("user_id") or "").strip()
    advertiser_id = str(campaign.get("advertiser_id") or "").strip()

    if not session_id:
        raise ValueError("transaction session_id is required")
    if transaction.get("payment_status") != "paid":
        raise ValueError("transaction must be paid")
    if transaction.get("status") != "completed":
        raise ValueError("transaction must be completed")
    if not campaign_id or tx_campaign_id != campaign_id:
        raise ValueError("transaction campaign does not match campaign")
    if not advertiser_id or tx_user_id != advertiser_id:
        raise ValueError("transaction advertiser does not match campaign advertiser")

    views = transaction.get("quota_entitlement_views")
    if isinstance(views, bool) or not isinstance(views, int) or views <= 0:
        raise ValueError("quota_entitlement_views must be a positive integer")

    amount = transaction.get("amount")
    if isinstance(amount, bool) or not isinstance(amount, (int, float)) or amount <= 0:
        raise ValueError("paid transaction amount must be positive")

    timestamp = created_at or datetime.now(timezone.utc).isoformat()

    return {
        "entitlement_id": session_id,
        "session_id": session_id,
        "campaign_id": campaign_id,
        "advertiser_id": advertiser_id,
        "purchased_views": views,
        "allocated_views": 0,
        "completed_views": 0,
        "reserved_views": 0,
        "remaining_views": views,
        "amount_paid": float(amount),
        "currency": str(transaction.get("currency") or "").upper(),
        "payment_status": "paid",
        "status": "active",
        "created_at": timestamp,
    }
