"""FastAPI application entry point."""

from fastapi import FastAPI

from app.models import PackageRequest, PackingResponse
from app.packing import Package, pack_packages

app = FastAPI(
    title="ProtoLabs Package Packing API",
    description=(
        "A small service that estimates the number of shipping boxes required "
        "using a practical 3D bin-packing heuristic."
    ),
    version="1.0.0",
)


@app.get("/health", tags=["health"])
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/pack", response_model=PackingResponse, tags=["packing"])
def pack(packages: list[PackageRequest]) -> PackingResponse:
    """Pack the supplied packages and return box placements and exceptions."""
    domain_packages = [
        Package(
            id=item.id,
            width=item.width,
            height=item.height,
            length=item.length,
            weight=item.weight,
        )
        for item in packages
    ]
    result = pack_packages(domain_packages)
    return PackingResponse.model_validate(result)
