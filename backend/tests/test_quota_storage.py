
from quota_storage import get_eligible_devices


def make_records():
    drivers = {
        "driver-1": {"status": "Approved"},
        "driver-2": {"status": "Pending"},
    }

    vehicles = {
        "vehicle-1": {
            "status": "Approved",
            "operating_area": "Vijayawada",
        },
        "vehicle-2": {
            "status": "Approved",
            "operating_area": "Guntur",
        },
        "vehicle-3": {
            "status": "Pending",
            "operating_area": "Vijayawada",
        },
    }

    devices = [
        {
            "_id": "device-1",
            "device_code": "OWM-AUTO-000001",
            "vehicle_id": "vehicle-1",
            "driver_id": "driver-1",
            "status": "Approved",
        },
        {
            "_id": "device-2",
            "device_code": "OWM-AUTO-000002",
            "vehicle_id": "vehicle-2",
            "driver_id": "driver-1",
            "status": "Approved",
        },
        {
            "_id": "device-3",
            "device_code": "OWM-AUTO-000003",
            "vehicle_id": "vehicle-1",
            "driver_id": "driver-2",
            "status": "Approved",
        },
        {
            "_id": "device-4",
            "device_code": "OWM-AUTO-000004",
            "vehicle_id": "vehicle-3",
            "driver_id": "driver-1",
            "status": "Approved",
        },
        {
            "_id": "device-5",
            "device_code": "OWM-AUTO-000005",
            "vehicle_id": "vehicle-1",
            "driver_id": "driver-1",
            "status": "Pending",
        },
    ]

    return devices, vehicles, drivers


def test_only_fully_approved_devices_are_eligible():
    devices, vehicles, drivers = make_records()

    result = get_eligible_devices(
        devices,
        vehicles,
        drivers,
    )

    assert [
        item["device_id"] for item in result
    ] == ["device-1", "device-2"]


def test_location_targeting_filters_devices():
    devices, vehicles, drivers = make_records()

    result = get_eligible_devices(
        devices,
        vehicles,
        drivers,
        target_locations=["Vijayawada"],
    )

    assert [
        item["device_id"] for item in result
    ] == ["device-1"]


def test_device_targeting_accepts_permanent_device_code():
    devices, vehicles, drivers = make_records()

    result = get_eligible_devices(
        devices,
        vehicles,
        drivers,
        target_devices=["OWM-AUTO-000002"],
    )

    assert [
        item["device_id"] for item in result
    ] == ["device-2"]


def test_device_targeting_accepts_database_id():
    devices, vehicles, drivers = make_records()

    result = get_eligible_devices(
        devices,
        vehicles,
        drivers,
        target_devices=["device-1"],
    )

    assert [
        item["device_id"] for item in result
    ] == ["device-1"]


def test_missing_vehicle_or_driver_is_not_eligible():
    devices, vehicles, drivers = make_records()

    devices.append({
        "_id": "device-6",
        "device_code": "OWM-AUTO-000006",
        "vehicle_id": "missing-vehicle",
        "driver_id": "driver-1",
        "status": "Approved",
    })

    result = get_eligible_devices(
        devices,
        vehicles,
        drivers,
    )

    assert "device-6" not in [
        item["device_id"] for item in result
    ]


def test_duplicate_device_records_are_not_returned_twice():
    devices, vehicles, drivers = make_records()

    devices.append(devices[0].copy())

    result = get_eligible_devices(
        devices,
        vehicles,
        drivers,
    )

    ids = [item["device_id"] for item in result]

    assert len(ids) == len(set(ids))


def test_empty_location_target_means_no_location_restriction():
    devices, vehicles, drivers = make_records()

    result = get_eligible_devices(
        devices,
        vehicles,
        drivers,
        target_locations=[],
    )

    assert len(result) == 2
