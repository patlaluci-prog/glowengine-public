# GlowEngine API

Default local server:

```text
http://127.0.0.1:8000
```

Endpoints:

- `GET /`
- `GET /health`
- `POST /analyze`
- `GET /chaos/generate`
- `POST /chaos/train`

Training endpoints require `X-API-Key`.

This API is a compact scoring/training demo engine. It is not the private C23
app engine and it is not C3Brain.
