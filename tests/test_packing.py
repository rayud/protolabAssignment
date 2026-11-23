from fastapi.testclient import TestClient

from app.main import app
from app.packing import (
    Package,
    create_box,
    find_best_placement,
    get_orientations,
    pack_packages,
    prune_free_spaces,
    validate_packing_geometry,
)
from app.boxes import BOX_TYPES
from app.packing import FreeSpace

client = TestClient(app)


def test_empty_package_list_returns_zero_boxes():
    result = pack_packages([])
    assert result == {"total_boxes": 0, "boxes": [], "unpackable": []}


def test_two_small_packages_share_one_box():
    packages = [
        Package(123, 10, 10, 10, 5),
        Package(125, 5, 5, 10, 10),
    ]
    result = pack_packages(packages)
    assert result["total_boxes"] == 1
    assert result["unpackable"] == []
    assert result["boxes"][0]["package_count"] == 2
    validate_packing_geometry(result)


def test_rotation_is_considered():
    package = Package(1, 200, 100, 100, 10)
    orientations = get_orientations(package)
    assert (100, 200, 100) in orientations
    result = pack_packages([package])
    assert result["total_boxes"] == 1
    assert result["unpackable"] == []
    validate_packing_geometry(result)


def test_package_too_large_is_reported_as_unpackable():
    package = Package(99, 500, 500, 500, 10)
    result = pack_packages([package])
    assert result["total_boxes"] == 0
    assert result["unpackable"][0]["id"] == 99
    assert "dimensions" in result["unpackable"][0]["reason"]


def test_weight_over_capacity_is_reported_as_unpackable():
    package = Package(77, 10, 10, 10, 5000)
    result = pack_packages([package])
    assert result["total_boxes"] == 0
    assert result["unpackable"][0]["id"] == 77
    assert "weight" in result["unpackable"][0]["reason"]


def test_packages_are_not_placed_over_box_weight_limit():
    packages = [
        Package(1, 20, 20, 20, 700),
        Package(2, 20, 20, 20, 700),
    ]
    result = pack_packages(packages)
    assert result["total_boxes"] == 2
    assert all(box["current_weight"] <= box["max_weight"] for box in result["boxes"])
    validate_packing_geometry(result)


def test_free_space_pruning_removes_contained_spaces():
    large = FreeSpace(0, 0, 0, 100, 100, 100)
    small = FreeSpace(10, 10, 10, 20, 20, 20)
    assert prune_free_spaces([large, small]) == [large]


def test_best_placement_returns_none_when_nothing_fits():
    box = create_box(BOX_TYPES[0])
    package = Package(1, 500, 500, 500, 1)
    assert find_best_placement(package, box.free_spaces) is None


def test_api_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_api_pack_endpoint_accepts_raw_package_array():
    response = client.post(
        "/pack",
        json=[
            {"id": 123, "width": 10, "height": 10, "length": 10, "weight": 5},
            {"id": 125, "width": 5, "height": 5, "length": 10, "weight": 10},
        ],
    )
    assert response.status_code == 200
    body = response.json()
    assert body["total_boxes"] == 1
    assert body["unpackable"] == []


def test_api_rejects_negative_dimensions():
    response = client.post(
        "/pack",
        json=[{"id": 1, "width": -1, "height": 10, "length": 10, "weight": 1}],
    )
    assert response.status_code == 422


def test_api_rejects_unknown_fields():
    response = client.post(
        "/pack",
        json=[{
            "id": 1, "width": 10, "height": 10, "length": 10,
            "weight": 1, "colour": "red"
        }],
    )
    assert response.status_code == 422
