"""Fixed shipping-box catalogue from the take-home assignment."""

from dataclasses import dataclass


@dataclass(frozen=True)
class BoxType:
    name: str
    width: float
    height: float
    length: float
    max_weight: float

    @property
    def volume(self) -> float:
        return self.width * self.height * self.length


BOX_TYPES: tuple[BoxType, ...] = (
    BoxType("A", 150, 150, 150, 1000),
    BoxType("B", 100, 200, 100, 1000),
    BoxType("C", 300, 400, 300, 3000),
)
