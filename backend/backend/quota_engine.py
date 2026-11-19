
"""
OnWheelsMedia campaign impression allocation engine.

This module is intentionally independent from FastAPI and MongoDB.
It calculates fair per-device impression allocations without exceeding
the purchased quantity or the configured per-device maximum.

Database eligibility, payment verification, transactional publishing,
quota reservation and impression counting must be enforced by the
backend integration layer.
"""

from typing import Any, Dict, List


MAX_VIEWS_PER_DEVICE = 25


def allocate_campaign_views(
    purchased_views: int,
    eligible_devices: List[Dict[str, Any]],
    max_views_per_device: int = MAX_VIEWS_PER_DEVICE,
) -> Dict[str, Any]:
    """
    Distribute purchased impressions fairly across eligible devices.

    Each device is identified by its permanent device ID.
    Duplicate device IDs are ignored.
    Allocation is capped at max_views_per_device per device.

    Returns:
        {
            "purchased_views": int,
            "total_allocated": int,
            "unallocated": int,
            "fully_distributed": bool,
            "allocations": [
                {
                    "device_id": str,
                    "device_code": str,
                    "allocated_views": int
                }
            ]
        }
    """

    if isinstance(purchased_views, bool) or not isinstance(purchased_views, int):
        raise ValueError("purchased_views must be an integer")

    if purchased_views < 0:
        raise ValueError("purchased_views cannot be negative")

    if (
        isinstance(max_views_per_device, bool)
        or not isinstance(max_views_per_device, int)
        or max_views_per_device < 1
    ):
        raise ValueError("max_views_per_device must be a positive integer")

    # Deduplicate devices by their permanent ID and sort consistently.
    unique_devices = {}
    for device in eligible_devices:
        device_id = str(device.get("device_id") or device.get("id") or "").strip()
        device_code = str(device.get("device_code") or "").strip()

        if not device_id or not device_code:
            continue

        if device_id in unique_devices:
            continue

        unique_devices[device_id] = {
            "device_id": device_id,
            "device_code": device_code,
        }

    devices = sorted(
        unique_devices.values(),
        key=lambda item: item["device_code"],
    )

    allocations = [
        {
            "device_id": device["device_id"],
            "device_code": device["device_code"],
            "allocated_views": 0,
        }
        for device in devices
    ]

    remaining = purchased_views

    # Fairly distribute views in rounds. Every device receives an
    # equal share before any device receives its next share.
    while remaining > 0:
        active = [
            item
            for item in allocations
            if item["allocated_views"] < max_views_per_device
        ]

        if not active:
            break

        share = remaining // len(active)

        if share > 0:
            for item in active:
                room = max_views_per_device - item["allocated_views"]
                grant = min(share, room, remaining)

                item["allocated_views"] += grant
                remaining -= grant

                if remaining == 0:
                    break
        else:
            # Remaining views are fewer than active devices.
            # Give one view at a time in stable device order.
            for item in active:
                if remaining == 0:
                    break

                item["allocated_views"] += 1
                remaining -= 1

    total_allocated = sum(
        item["allocated_views"] for item in allocations
    )

    return {
        "purchased_views": purchased_views,
        "total_allocated": total_allocated,
        "unallocated": purchased_views - total_allocated,
        "fully_distributed": total_allocated == purchased_views,
        "max_views_per_device": max_views_per_device,
        "selected_devices": sum(
            1 for item in allocations if item["allocated_views"] > 0
        ),
        "allocations": [
            item for item in allocations if item["allocated_views"] > 0
        ],
    }
