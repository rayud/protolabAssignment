# ProtoLabs 3D Package Packing API

A small Python/FastAPI service that estimates how many shipping boxes are required for a list of rectangular packages. It uses a practical 3D bin-packing heuristic and the fixed box catalogue from the take-home assignment.

## Features

- `POST /pack` accepts a JSON array of packages.
- Uses the supplied A, B and C shipping-box catalogue.
- Sorts packages by descending volume (First Fit Decreasing ordering).
- Tries all unique axis-aligned orientations (up to six per package).
- Tracks 3D `(x, y, z)` placement coordinates.
- Uses a Maximal Empty Spaces (EMS) approach to track candidate free regions.
- Chooses a best-fit placement among available candidates.
- Checks the total weight against each box's capacity.
- Reports packages that cannot fit any catalogue box.
- Validates request fields and rejects invalid input with HTTP 422.
- Includes unit and API tests.

## Requirements

- Python 3.10 or newer
- pip

## Run locally

### 1. Create and activate a virtual environment

Linux/macOS:

```bash
python -m venv .venv
source .venv/bin/activate
```

Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Start the API

```bash
uvicorn app.main:app --reload
```

The API is available at `http://127.0.0.1:8000`.

Interactive API documentation: `http://127.0.0.1:8000/docs`.

Health check: `GET http://127.0.0.1:8000/health`.

## API contract

### `POST /pack`

The request body is a JSON array. Each package must contain:

| Field | Type | Rule |
|---|---|---|
| `id` | integer | Package identifier |
| `width` | number | Must be greater than zero |
| `height` | number | Must be greater than zero |
| `length` | number | Must be greater than zero |
| `weight` | number | Must be zero or greater |

Example request:

```json
[
  {"id": 123, "width": 10, "height": 10, "length": 10, "weight": 5},
  {"id": 125, "width": 5, "height": 5, "length": 10, "weight": 10}
]
```

Example response shape:

```json
{
  "total_boxes": 1,
  "boxes": [
    {
      "box_type": "B",
      "dimensions": {"width": 100, "height": 200, "length": 100},
      "max_weight": 1000,
      "current_weight": 15,
      "package_count": 2,
      "volume_utilization": 0.000625,
      "packages": [
        {
          "id": 123,
          "x": 0,
          "y": 0,
          "z": 0,
          "width": 10,
          "height": 10,
          "length": 10,
          "weight": 5
        },
        {
          "id": 125,
          "x": 10,
          "y": 0,
          "z": 0,
          "width": 10,
          "height": 5,
          "length": 5,
          "weight": 10
        }
      ]
    }
  ],
  "unpackable": []
}
```

The example illustrates the response structure; actual placements and selected box types are determined by the algorithm.

If the input array is empty, the API returns `total_boxes: 0`, an empty `boxes` list and an empty `unpackable` list.

If one or more packages cannot fit any available box (by dimensions and/or weight), those package IDs and reasons are returned in `unpackable`. Other packages are still packed. Invalid package data is rejected with HTTP 422.

## Algorithm overview

1. Validate dimensions and weights.
2. Sort packages by descending volume. Larger packages are generally harder to place, so they are considered first.
3. For each package, examine the already-open boxes.
4. For each box, examine its current maximal empty-space candidates and all unique package orientations.
5. A candidate is valid only if all three oriented dimensions fit inside the candidate free space and the box has enough remaining weight capacity.
6. Score valid candidates by leftover volume, then largest leftover side, then total leftover side lengths. Select the lowest score.
7. Place the package at the selected free-space origin and subtract its occupied cuboid from the free-space candidates.
8. Remove duplicate and fully contained free-space candidates.
9. If no open box can accept the package, open the smallest catalogue box that can accommodate it.
10. Return the boxes, package coordinates and unpackable packages.

### Why maximal empty spaces?

A placed package can leave useful empty regions to its left, right, above, below, in front and behind. The EMS approach generates candidate empty cuboids around the placed package and removes duplicate or contained candidates. Candidate free spaces can overlap one another; that is intentional. Each candidate is maintained so that it does not contain any already-placed package. When another package is placed, every candidate that intersects it is split again.



## Run tests

```bash
pytest
```

The tests cover empty input, multiple packages sharing a box, rotation, unpackable dimensions, weight limits, free-space pruning, API behavior and geometry checks for returned placements.


## Git workflow


```bash
git init
git add .
git commit -m "chore: initialize FastAPI packing service"
git add app/boxes.py app/models.py app/main.py
git commit -m "feat: add package packing API and box catalogue"
git add app/packing.py
git commit -m "feat: implement 3D maximal empty space packing heuristic"
git add tests/
git commit -m "test: cover packing logic and API edge cases"
git add README.md Dockerfile requirements.txt pyproject.toml .gitignore
git commit -m "docs: add setup instructions and algorithm assumptions"
```



```bash
git branch -M main
git remote add origin https://github.com/rayud/protolabAssignment.git
git push -u origin main
```
