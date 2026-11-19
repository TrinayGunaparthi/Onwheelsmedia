
"""
OnWheelsMedia quota storage foundation.

Provides:
- MongoDB indexes for campaign/device allocations
- Idempotency indexes for impression events
- Device eligibility filtering

This file does not publish campaigns or authorize playback yet.
"""

from typing import Any, Dict, List, Optional


def _normalise(value: Any) -> str:
    return str(value or "").strip().lower()


def get_eligible_devices(
    devices: List[Dict[str, Any]],
    vehicles_by_id: Dict[str, Dict[str, Any]],
    drivers_by_id: Dict[str, Dict[str, Any]],
    target_locations: Optional[List[str]] = None,
    target_devices: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """
    Return only devices whose device, vehicle and driver are approved.

    Target locations are matched against vehicle operating_area.
    Target devices can match the Mongo device ID or permanent device code.

    This function is a pure filter. It does not query the database.
    """

    location_targets = {
        _normalise(item)
        for item in (target_locations or [])
        if _normalise(item)
    }

    device_targets = {
        str(item).strip()
        for item in (target_devices or [])
        if str(item).strip()
    }

    eligible = []
    seen_ids = set()

    for device in devices:
        device_id = str(
            device.get("_id") or device.get("id") or ""
        ).strip()

        device_code = str(
            device.get("device_code") or ""
        ).strip()

        if not device_id or not device_code:
            continue

        if device_id in seen_ids:
            continue

        if _normalise(device.get("status")) != "approved":
            continue

        vehicle_id = str(
            device.get("vehicle_id") or ""
        ).strip()

        driver_id = str(
            device.get("driver_id") or ""
        ).strip()

        vehicle = vehicles_by_id.get(vehicle_id)
        driver = drivers_by_id.get(driver_id)

        if not vehicle or not driver:
            continue

        if _normalise(vehicle.get("status")) != "approved":
            continue

        if _normalise(driver.get("status")) != "approved":
            continue

        if location_targets:
            operating_area = _normalise(
                vehicle.get("operating_area")
            )

            if operating_area not in location_targets:
                continue

        if device_targets:
            if (
                device_id not in device_targets
                and device_code not in device_targets
            ):
                continue

        seen_ids.add(device_id)

        eligible.append({
            "device_id": device_id,
            "device_code": device_code,
            "vehicle_id": vehicle_id,
            "driver_id": driver_id,
            "operating_area": vehicle.get("operating_area", ""),
        })

    return sorted(
        eligible,
        key=lambda item: item["device_code"],
    )


async def ensure_quota_indexes(db):
    """
    Create indexes required for quota allocation and event idempotency.

    Run this during backend startup only after reviewing deployment
    compatibility and existing duplicate data.
    """

    await db.quota_allocations.create_index(
        [
            ("campaign_id", 1),
            ("device_id", 1),
        ],
        unique=True,
        name="unique_campaign_device_allocation",
    )

    await db.quota_allocations.create_index(
        [
            ("campaign_id", 1),
            ("device_code", 1),
        ],
        name="campaign_device_code_lookup",
    )

    await db.quota_impressions.create_index(
        [
            ("event_id", 1),
        ],
        unique=True,
        name="unique_impression_event_id",
    )

    await db.quota_impressions.create_index(
        [
            ("campaign_id", 1),
            ("device_id", 1),
        ],
        name="campaign_device_impression_lookup",
    )

    await db.quota_reservations.create_index(
        [
            ("reservation_id", 1),
        ],
        unique=True,
        name="unique_quota_reservation_id",
    )

    await db.quota_reservations.create_index(
        [
            ("campaign_id", 1),
            ("device_id", 1),
        ],
        name="campaign_device_reservation_lookup",
    )

"""
OnWheelsMedia quota storage foundation.

Provides:
- MongoDB indexes for campaign/device allocations
- Idempotency indexes for impression events
- Device eligibility filtering
- Unique payment-session entitlement storage index

This file does not publish campaigns or authorize playback yet.
"""

from typing import Any, Dict, List, Optional


def _normalise(value: Any) -> str:
    return str(value or "").strip().lower()


def get_eligible_devices(
    devices: List[Dict[str, Any]],
    vehicles_by_id: Dict[str, Dict[str, Any]],
    drivers_by_id: Dict[str, Dict[str, Any]],
    target_locations: Optional[List[str]] = None,
    target_devices: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """Return devices whose device, vehicle and driver are approved."""
    location_targets = {
        _normalise(item)
        for item in (target_locations or [])
        if _normalise(item)
    }
    device_targets = {
        str(item).strip()
        for item in (target_devices or [])
        if str(item).strip()
    }

    eligible = []
    seen_ids = set()

    for device in devices:
        device_id = str(device.get("_id") or device.get("id") or "").strip()
        device_code = str(device.get("device_code") or "").strip()
        if not device_id or not device_code or device_id in seen_ids:
            continue
        if _normalise(device.get("status")) != "approved":
            continue

        vehicle_id = str(device.get("vehicle_id") or "").strip()
        driver_id = str(device.get("driver_id") or "").strip()
        vehicle = vehicles_by_id.get(vehicle_id)
        driver = drivers_by_id.get(driver_id)
        if not vehicle or not driver:
            continue
        if _normalise(vehicle.get("status")) != "approved":
            continue
        if _normalise(driver.get("status")) != "approved":
            continue

        if location_targets and _normalise(vehicle.get("operating_area")) not in location_targets:
            continue
        if device_targets and device_id not in device_targets and device_code not in device_targets:
            continue

        seen_ids.add(device_id)
        eligible.append({
            "device_id": device_id,
            "device_code": device_code,
            "vehicle_id": vehicle_id,
            "driver_id": driver_id,
            "operating_area": vehicle.get("operating_area", ""),
        })

    return sorted(eligible, key=lambda item: item["device_code"])


async def ensure_quota_indexes(db):
    """Create quota indexes; check existing duplicate data before startup activation."""
    await db.quota_entitlements.create_index(
        [("session_id", 1)],
        unique=True,
        name="unique_paid_session_entitlement",
    )
    await db.quota_entitlements.create_index(
        [("campaign_id", 1), ("advertiser_id", 1)],
        name="campaign_entitlement_lookup",
    )

    await db.quota_allocations.create_index(
        [("campaign_id", 1), ("device_id", 1)],
        unique=True,
        name="unique_campaign_device_allocation",
    )
    await db.quota_allocations.create_index(
        [("campaign_id", 1), ("device_code", 1)],
        name="campaign_device_code_lookup",
    )
    await db.quota_impressions.create_index(
        [("event_id", 1)],
        unique=True,
        name="unique_impression_event_id",
    )
    await db.quota_impressions.create_index(
        [("campaign_id", 1), ("device_id", 1)],
        name="campaign_device_impression_lookup",
    )
    await db.quota_reservations.create_index(
        [("reservation_id", 1)],
        unique=True,
        name="unique_quota_reservation_id",
    )
    await db.quota_reservations.create_index(
        [("campaign_id", 1), ("device_id", 1)],
        name="campaign_device_reservation_lookup",
    )
