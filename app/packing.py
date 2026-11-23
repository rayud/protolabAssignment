"""A practical 3D bin-packing heuristic using maximal empty spaces (EMS).

This is a heuristic, not an exact optimizer. It uses axis-aligned rotations and
keeps a set of empty rectangular candidate spaces for each opened box.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from itertools import permutations
from math import isfinite
from typing import Any, Iterable, Sequence

from app.boxes import BOX_TYPES, BoxType


@dataclass(frozen=True)
class Package:
    id: int
    width: float
    height: float
    length: float
    weight: float

    @property
    def volume(self) -> float:
        return self.width * self.height * self.length


@dataclass(frozen=True)
class FreeSpace:
    x: float
    y: float
    z: float
    width: float
    height: float
    length: float

    @property
    def volume(self) -> float:
        return self.width * self.height * self.length


@dataclass(frozen=True)
class Placement:
    package_id: int
    x: float
    y: float
    z: float
    width: float
    height: float
    length: float
    weight: float

    @property
    def volume(self) -> float:
        return self.width * self.height * self.length


@dataclass
class PackedBox:
    box_type: BoxType
    free_spaces: list[FreeSpace] = field(default_factory=list)
    packages: list[Placement] = field(default_factory=list)
    current_weight: float = 0.0

    @property
    def used_volume(self) -> float:
        return sum(package.volume for package in self.packages)


@dataclass(frozen=True)
class Candidate:
    space_index: int
    orientation: tuple[float, float, float]
    score: tuple[float, float, float]


def calculate_volume(width: float, height: float, length: float) -> float:
    """Return the volume of a rectangular package or space."""
    return width * height * length


def get_orientations(package: Package) -> list[tuple[float, float, float]]:
    """Return unique axis-aligned orientations (at most six)."""
    return sorted(set(permutations((package.width, package.height, package.length))))


def _fits_in_space(
    orientation: tuple[float, float, float], space: FreeSpace
) -> bool:
    width, height, length = orientation
    return (
        width <= space.width
        and height <= space.height
        and length <= space.length
    )


def find_best_placement(
    package: Package, free_spaces: Sequence[FreeSpace]
) -> Candidate | None:
    """Choose the best fitting free-space/orientation candidate.

    The score first minimizes unused volume in the candidate free space, then
    the largest leftover side, then the sum of leftover sides.
    """
    best: Candidate | None = None

    for space_index, space in enumerate(free_spaces):
        for orientation in get_orientations(package):
            if not _fits_in_space(orientation, space):
                continue

            width, height, length = orientation
            leftovers = (
                space.width - width,
                space.height - height,
                space.length - length,
            )
            score = (
                max(0.0, space.volume - package.volume),
                max(leftovers),
                sum(leftovers),
            )
            candidate = Candidate(space_index, orientation, score)

            if best is None or candidate.score < best.score:
                best = candidate

    return best


def _intersects(a: FreeSpace, b: FreeSpace) -> bool:
    """Return True only when two cuboids overlap with positive volume."""
    return (
        a.x < b.x + b.width
        and a.x + a.width > b.x
        and a.y < b.y + b.height
        and a.y + a.height > b.y
        and a.z < b.z + b.length
        and a.z + a.length > b.z
    )


def _contains(outer: FreeSpace, inner: FreeSpace) -> bool:
    """Return True when outer fully contains inner, including equal bounds."""
    return (
        outer.x <= inner.x
        and outer.y <= inner.y
        and outer.z <= inner.z
        and outer.x + outer.width >= inner.x + inner.width
        and outer.y + outer.height >= inner.y + inner.height
        and outer.z + outer.length >= inner.z + inner.length
    )


def _positive_space(space: FreeSpace) -> bool:
    return (
        space.width > 0
        and space.height > 0
        and space.length > 0
    )


def _split_free_space(space: FreeSpace, used: FreeSpace) -> list[FreeSpace]:
    """Subtract a placed package from one free-space candidate.

    Up to six slabs are generated around the placed package. These candidate
    spaces can overlap one another; that is intentional in an EMS approach.
    Each candidate remains free of every placed package.
    """
    if not _intersects(space, used):
        return [space]

    sx1, sy1, sz1 = space.x, space.y, space.z
    sx2 = space.x + space.width
    sy2 = space.y + space.height
    sz2 = space.z + space.length

    # Clip the placed cuboid to this free-space candidate. EMS candidates may
    # overlap one another, so the new package need not be fully inside every
    # candidate that it intersects.
    ix1 = max(sx1, used.x)
    iy1 = max(sy1, used.y)
    iz1 = max(sz1, used.z)
    ix2 = min(sx2, used.x + used.width)
    iy2 = min(sy2, used.y + used.height)
    iz2 = min(sz2, used.z + used.length)

    candidates = [
        # Left and right slabs span the full Y/Z dimensions.
        FreeSpace(sx1, sy1, sz1, ix1 - sx1, space.height, space.length),
        FreeSpace(ix2, sy1, sz1, sx2 - ix2, space.height, space.length),
        # Below and above slabs span the full X/Z dimensions.
        FreeSpace(sx1, sy1, sz1, space.width, iy1 - sy1, space.length),
        FreeSpace(sx1, iy2, sz1, space.width, sy2 - iy2, space.length),
        # Front and back slabs span the full X/Y dimensions.
        FreeSpace(sx1, sy1, sz1, space.width, space.height, iz1 - sz1),
        FreeSpace(sx1, sy1, iz2, space.width, space.height, sz2 - iz2),
    ]
    return [candidate for candidate in candidates if _positive_space(candidate)]


def prune_free_spaces(spaces: Iterable[FreeSpace]) -> list[FreeSpace]:
    """Remove duplicate and fully-contained free-space candidates."""
    unique: list[FreeSpace] = []
    seen: set[tuple[float, ...]] = set()

    for space in spaces:
        if not _positive_space(space):
            continue
        key = tuple(round(value, 9) for value in (
            space.x, space.y, space.z,
            space.width, space.height, space.length,
        ))
        if key not in seen:
            seen.add(key)
            unique.append(space)

    result: list[FreeSpace] = []
    for index, candidate in enumerate(unique):
        contained = False
        for other_index, other in enumerate(unique):
            if index == other_index:
                continue
            if _contains(other, candidate):
                # Duplicates have already been removed, so this is strict containment.
                contained = True
                break
        if not contained:
            result.append(candidate)
    return result


def create_box(box_type: BoxType) -> PackedBox:
    """Create an empty box whose initial free space is the entire box."""
    return PackedBox(
        box_type=box_type,
        free_spaces=[FreeSpace(0, 0, 0, box_type.width, box_type.height, box_type.length)],
    )


def place_package(package: Package, box: PackedBox, candidate: Candidate) -> None:
    """Place a package at the selected free-space origin and update the EMS list."""
    selected_space = box.free_spaces[candidate.space_index]
    width, height, length = candidate.orientation

    placed_region = FreeSpace(
        selected_space.x,
        selected_space.y,
        selected_space.z,
        width,
        height,
        length,
    )

    placement = Placement(
        package_id=package.id,
        x=placed_region.x,
        y=placed_region.y,
        z=placed_region.z,
        width=width,
        height=height,
        length=length,
        weight=package.weight,
    )

    updated_spaces: list[FreeSpace] = []
    for free_space in box.free_spaces:
        updated_spaces.extend(_split_free_space(free_space, placed_region))

    box.free_spaces = prune_free_spaces(updated_spaces)
    box.packages.append(placement)
    box.current_weight += package.weight


def _box_types_by_size() -> list[BoxType]:
    """Return the fixed catalogue from smallest volume to largest."""
    return sorted(BOX_TYPES, key=lambda item: (item.volume, item.name))


def _unpackable_reason(package: Package) -> str:
    dimensionally_compatible = [
        box_type
        for box_type in BOX_TYPES
        if any(
            orientation[0] <= box_type.width
            and orientation[1] <= box_type.height
            and orientation[2] <= box_type.length
            for orientation in get_orientations(package)
        )
    ]

    if not dimensionally_compatible:
        return "Package dimensions do not fit any available box, even after rotation."

    if all(package.weight > box_type.max_weight for box_type in dimensionally_compatible):
        return "Package weight exceeds the capacity of every dimensionally compatible box."

    return "Package could not be placed in the available box catalogue."


def _validate_package(package: Package) -> None:
    values = (package.width, package.height, package.length, package.weight)
    if not all(isfinite(value) for value in values):
        raise ValueError(f"Package {package.id} contains a non-finite numeric value.")
    if min(package.width, package.height, package.length) <= 0:
        raise ValueError(f"Package {package.id} dimensions must be greater than zero.")
    if package.weight < 0:
        raise ValueError(f"Package {package.id} weight cannot be negative.")


def _serialize_box(box: PackedBox) -> dict[str, Any]:
    box_volume = box.box_type.volume
    utilization = (box.used_volume / box_volume) if box_volume else 0.0
    return {
        "box_type": box.box_type.name,
        "dimensions": {
            "width": box.box_type.width,
            "height": box.box_type.height,
            "length": box.box_type.length,
        },
        "max_weight": box.box_type.max_weight,
        "current_weight": round(box.current_weight, 6),
        "package_count": len(box.packages),
        "volume_utilization": round(utilization, 6),
        "packages": [
            {
                "id": item.package_id,
                "x": item.x,
                "y": item.y,
                "z": item.z,
                "width": item.width,
                "height": item.height,
                "length": item.length,
                "weight": item.weight,
            }
            for item in box.packages
        ],
    }


def pack_packages(packages: Sequence[Package]) -> dict[str, Any]:
    """Pack packages using a volume-descending EMS best-fit heuristic.

    Packages that cannot fit any catalogue box are reported in `unpackable`;
    other packages are still packed. Empty input returns zero boxes.
    """
    for package in packages:
        _validate_package(package)

    ordered_packages = sorted(
        packages,
        key=lambda item: (-item.volume, -max(item.width, item.height, item.length), item.id),
    )
    box_types = _box_types_by_size()
    packed_boxes: list[PackedBox] = []
    unpackable: list[dict[str, Any]] = []

    for package in ordered_packages:
        best_box: PackedBox | None = None
        best_candidate: Candidate | None = None
        best_score: tuple[float, float, float, int] | None = None

        # First try every already-open box and choose the best candidate.
        for box_index, box in enumerate(packed_boxes):
            if box.current_weight + package.weight > box.box_type.max_weight:
                continue

            candidate = find_best_placement(package, box.free_spaces)
            if candidate is None:
                continue

            combined_score = (*candidate.score, box_index)
            if best_score is None or combined_score < best_score:
                best_score = combined_score
                best_box = box
                best_candidate = candidate

        if best_box is not None and best_candidate is not None:
            place_package(package, best_box, best_candidate)
            continue

        # No open box can accept it: create the smallest compatible new box.
        new_box: PackedBox | None = None
        new_candidate: Candidate | None = None
        for box_type in box_types:
            if package.weight > box_type.max_weight:
                continue

            candidate_box = create_box(box_type)
            candidate = find_best_placement(package, candidate_box.free_spaces)
            if candidate is not None:
                new_box = candidate_box
                new_candidate = candidate
                break

        if new_box is None or new_candidate is None:
            unpackable.append({"id": package.id, "reason": _unpackable_reason(package)})
            continue

        place_package(package, new_box, new_candidate)
        packed_boxes.append(new_box)

    return {
        "total_boxes": len(packed_boxes),
        "boxes": [_serialize_box(box) for box in packed_boxes],
        "unpackable": unpackable,
    }


def validate_packing_geometry(result: dict[str, Any]) -> None:
    """Raise AssertionError if returned placements overlap or exceed box bounds.

    This helper is useful in tests and debugging. It does not prove that the
    heuristic found the best possible packing.
    """
    box_lookup = {item.name: item for item in BOX_TYPES}
    for box in result["boxes"]:
        dimensions = box_lookup[box["box_type"]]
        placements = box["packages"]

        for item in placements:
            assert item["x"] >= 0 and item["y"] >= 0 and item["z"] >= 0
            assert item["x"] + item["width"] <= dimensions.width
            assert item["y"] + item["height"] <= dimensions.height
            assert item["z"] + item["length"] <= dimensions.length

        for index, first in enumerate(placements):
            first_space = FreeSpace(
                first["x"], first["y"], first["z"],
                first["width"], first["height"], first["length"],
            )
            for second in placements[index + 1:]:
                second_space = FreeSpace(
                    second["x"], second["y"], second["z"],
                    second["width"], second["height"], second["length"],
                )
                assert not _intersects(first_space, second_space), (
                    f"Packages {first['id']} and {second['id']} overlap."
                )
