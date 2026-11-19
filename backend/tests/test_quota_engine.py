
from quota_engine import allocate_campaign_views


def make_devices(count):
    return [
        {
            "device_id": f"id-{i}",
            "device_code": f"OWM-AUTO-{i:06d}",
        }
        for i in range(1, count + 1)
    ]


def test_50_views_distributed_across_4_devices():
    result = allocate_campaign_views(50, make_devices(4))

    assert result["purchased_views"] == 50
    assert result["total_allocated"] == 50
    assert result["unallocated"] == 0
    assert result["fully_distributed"] is True

    quotas = [
        item["allocated_views"]
        for item in result["allocations"]
    ]

    assert quotas == [13, 13, 12, 12]
    assert all(q <= 25 for q in quotas)


def test_one_device_cannot_receive_more_than_25():
    result = allocate_campaign_views(50, make_devices(1))

    assert result["total_allocated"] == 25
    assert result["unallocated"] == 25
    assert result["fully_distributed"] is False


def test_no_eligible_devices():
    result = allocate_campaign_views(50, [])

    assert result["total_allocated"] == 0
    assert result["unallocated"] == 50
    assert result["fully_distributed"] is False


def test_no_views_to_allocate():
    result = allocate_campaign_views(0, make_devices(4))

    assert result["total_allocated"] == 0
    assert result["unallocated"] == 0
    assert result["fully_distributed"] is True
    assert result["allocations"] == []


def test_duplicate_device_ids_are_not_allocated_twice():
    devices = make_devices(2)
    devices.append(devices[0].copy())

    result = allocate_campaign_views(50, devices)

    assert len(result["allocations"]) == 2
    assert result["total_allocated"] == 50
    assert result["unallocated"] == 0


def test_three_devices_capacity_is_75():
    result = allocate_campaign_views(100, make_devices(3))

    assert result["total_allocated"] == 75
    assert result["unallocated"] == 25
    assert all(
        item["allocated_views"] <= 25
        for item in result["allocations"]
    )


def test_invalid_negative_quantity_is_rejected():
    try:
        allocate_campaign_views(-1, make_devices(2))
    except ValueError:
        return

    assert False, "Negative view quantity should raise ValueError"


def test_boolean_quantity_is_rejected():
    try:
        allocate_campaign_views(True, make_devices(2))
    except ValueError:
        return

    assert False, "Boolean quantity should raise ValueError"
