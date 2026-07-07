# GlowEngine API

Default local server:

```text
http://127.0.0.1:8000
```

GlowEngine is a compact scoring and controlled-learning demo engine. It
generates bounded numeric state vectors, not images.

## Endpoints

| Method | Path | Purpose | Auth |
| --- | --- | --- | --- |
| `GET` | `/` | Engine status and version | No |
| `GET` | `/health` | Health check | No |
| `POST` | `/analyze` | Analyze an uploaded image | No |
| `GET` | `/chaos/generate` | Generate a bounded numeric state vector | No |
| `POST` | `/chaos/train` | Train from human feedback | `X-API-Key` |

## Generate

```bash
curl http://127.0.0.1:8000/chaos/generate
```

Example response:

```json
{
  "status": "success",
  "features": [0.5, 0.5, 0.5, 0.5, 0.5, 0.5],
  "score": 5.0,
  "population_mean": 5.0
}
```

## Train

```bash
curl -X POST http://127.0.0.1:8000/chaos/train \
  -H "Content-Type: application/json" \
  -H "X-API-Key: change-me-local-evaluation-key" \
  -d "{\"features_list\":[0.5,0.5,0.5,0.5,0.5,0.5],\"ai_score\":5.0,\"human_score\":7.0}"
```

Example response:

```json
{
  "status": "success",
  "message": "Vote processed and model updated",
  "telemetry": {
    "target_score": 7.0,
    "population_mean": 5.1,
    "score_count": 2
  }
}
```

## Analyze

```bash
curl -X POST http://127.0.0.1:8000/analyze \
  -F "file=@sample.jpg"
```

The image endpoint accepts `.jpg`, `.jpeg`, `.png` and `.webp` files within the
configured upload and pixel limits.

## Flow

```text
GET /chaos/generate
  -> inspect returned features and score
  -> POST /chaos/train with human_score
  -> model statistics and adaptive weights are updated
```

## Public Boundary

This API is the free public GlowEngine baseline. Commercial systems,
app-specific logic and private research orchestration are intentionally outside
this repository.
