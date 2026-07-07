# GlowEngine Public

[![CI](https://github.com/patlaluci-prog/glowengine-public/actions/workflows/ci.yml/badge.svg)](https://github.com/patlaluci-prog/glowengine-public/actions/workflows/ci.yml)

GlowEngine is a free, compact FastAPI engine for numeric scoring, bounded
state-vector generation and controlled learning.

This repository is the public gift version of the GlowEngine line. It is
intentionally separate from the author's commercial and private research
systems.

GlowEngine generates bounded numeric state vectors, not images.

## What It Is Useful For

- Small scoring and ranking experiments.
- Bounded synthetic numeric state generation.
- Controlled human-feedback training loops.
- FastAPI integration examples for lightweight engine services.
- Educational demos for adaptive scoring with SQLite persistence.

## Requirements

- Python 3.11
- SQLite
- Optional: Docker

## Included

- FastAPI app.
- Numeric scoring module.
- Bounded synthetic state-vector generation.
- Human-feedback training endpoint.
- SQLite initialization code.
- API key protection.
- Basic rate limiting.

## Public Package Boundaries

Runtime databases, private environment files, test media, development backups
and internal working directories are intentionally excluded.

This public edition contains only the reusable free baseline. Commercial
systems, app-specific logic, unreleased research modules and private
orchestration code are not part of this repository.

## Run Locally

```powershell
copy .env.example .env
pip install -r requirements.txt
python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

Open:

```text
http://127.0.0.1:8000/docs
```

## API Endpoints

| Method | Path | Purpose | Auth |
| --- | --- | --- | --- |
| `GET` | `/` | Engine status and version | No |
| `GET` | `/health` | Health check | No |
| `POST` | `/analyze` | Analyze an uploaded face image | No |
| `GET` | `/chaos/generate` | Generate a bounded numeric state vector | No |
| `POST` | `/chaos/train` | Train from human feedback | `X-API-Key` |

## Quick API Example

Generate a bounded numeric state vector:

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

Train from a human correction:

```bash
curl -X POST http://127.0.0.1:8000/chaos/train \
  -H "Content-Type: application/json" \
  -H "X-API-Key: change-me-local-evaluation-key" \
  -d "{\"features_list\":[0.5,0.5,0.5,0.5,0.5,0.5],\"ai_score\":5.0,\"human_score\":7.0}"
```

Typical learning flow:

```text
generate numeric state -> score it -> send human correction -> update model stats
```

## Docker

```bash
docker build -t glowengine-public .
docker run --env-file .env -p 8000:8000 glowengine-public
```

## License

MIT. See `LICENSE`.

## Author Signature

Created by Patla / patlaluci-prog. Packaged with Codex assistance.
