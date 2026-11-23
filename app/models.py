"""Pydantic request and response models for the HTTP API."""

from pydantic import BaseModel, ConfigDict, Field


class PackageRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int
    width: float = Field(gt=0, allow_inf_nan=False)
    height: float = Field(gt=0, allow_inf_nan=False)
    length: float = Field(gt=0, allow_inf_nan=False)
    weight: float = Field(ge=0, allow_inf_nan=False)


class PackagePlacementResponse(BaseModel):
    id: int
    x: float
    y: float
    z: float
    width: float
    height: float
    length: float
    weight: float


class BoxDimensionsResponse(BaseModel):
    width: float
    height: float
    length: float


class BoxResponse(BaseModel):
    box_type: str
    dimensions: BoxDimensionsResponse
    max_weight: float
    current_weight: float
    package_count: int
    volume_utilization: float
    packages: list[PackagePlacementResponse]


class UnpackableResponse(BaseModel):
    id: int
    reason: str


class PackingResponse(BaseModel):
    total_boxes: int
    boxes: list[BoxResponse]
    unpackable: list[UnpackableResponse]
