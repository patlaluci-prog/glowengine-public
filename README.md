# GlowEngine Public

Small free/open engine package for the GlowEngine line.

This repository is the public gift version: a compact FastAPI scoring,
synthetic-generation and training engine. It is intentionally separate from
C23, C3Cell, BrainReady C3 and C3Brain.

## What Is Included

- FastAPI app.
- Scoring, synthetic generation and training modules.
- SQLite initialization code.
- API key protection.
- Rate limiting.

## What Was Removed

- real `.env`;
- runtime `engine_data.db`;
- local test image;
- `patla/` working folder;
- v23 backup folder.

## Run Locally

```text
copy .env.example .env
pip install -r requirements.txt
python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

Open:

```text
http://127.0.0.1:8000/docs
```

## Public Boundary

This is the free/public GlowEngine base line. It is not C23, C3Cell,
BrainReady C3 or C3Brain.

## License

MIT. See `LICENSE`.

## Author Signature

Created by Patla / patlaluci-prog. Packaged with Codex assistance.
