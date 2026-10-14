# Sentinel API

A thin FastAPI wrapper around [Roblox/sentinel](https://github.com/Roblox/sentinel), exposing it over HTTP
(`/score`, `/health`, `/banks/*`) instead of as a Python library you import directly.

Sentinel detects rare text patterns (e.g. grooming, hate speech) via contrastive learning — comparing text
against positive (rare/harmful) and negative (common/normal) example banks. This repository places the
Sentinel library behind a lightweight HTTP layer.

## Why this exists

Roblox's own [`Dockerfile`](https://github.com/Roblox/sentinel/blob/main/Dockerfile) packages the `sentinel`
library and runs example scripts — there's no HTTP service upstream. This repository installs the
**unmodified upstream library** at a pinned commit as a normal dependency, and `app/` is a small FastAPI app
that imports it, same as any other consumer of the `sentinel` package would.

`app/dependencies.py` and `app/routes/scoring.py` are the files that actually reach into `sentinel`'s
internals (`sentinel_local_index`, `embeddings.sbert`, `score_formulae`, `io.index_io`) — if Roblox renames
or moves any of those modules, these two files need matching updates.

## Running it

```bash
docker build -t sentinel-api .
docker run --rm -p 8000:8000 sentinel-api
curl http://localhost:8000/health
```

## Configuration

Runtime settings are read from environment variables with the `SENTINEL_` prefix (see `app/config.py`).
They are defined by this API, not by the upstream Sentinel library. Set them on the process (for Docker,
pass `-e` / `--env-file` to `docker run`).

| Variable | Default | Meaning |
| --- | --- | --- |
| `SENTINEL_AUTO_LOAD_BANKS_PATH` | unset | Directory of a saved bank (`embeddings.safetensors` + config JSON). If set, banks are loaded at startup. |
| `SENTINEL_DEFAULT_TOP_K` | `5` | How many nearest neighbors in each bank to use when scoring a message. Overridable per request via `top_k` on `POST /score`. |
| `SENTINEL_DEFAULT_MIN_SCORE` | `0.1` | Per-message scores below this are treated as 0. Overridable per request via `min_score_to_consider` on `POST /score`. |
| `SENTINEL_DEFAULT_MIN_SIZE_OF_SCORES` | `5` | Minimum number of per-message scores needed before skewness aggregation is treated as meaningful. Passed through to Sentinel's `skewness()` as `min_size_of_scores`. Not overridable per request. |

Example:

```bash
docker run --rm -p 8000:8000 \
  -e SENTINEL_AUTO_LOAD_BANKS_PATH=/data/banks/my_model \
  -v /path/on/host/banks:/data/banks \
  sentinel-api
```

`SENTINEL_COMMIT` in the `Dockerfile` is a build argument (which upstream commit to install), not a runtime
setting.

## Upgrading the pinned commit

Roblox hasn't cut a version tag yet, so `SENTINEL_COMMIT` in the `Dockerfile` pins a commit SHA rather than
a tag or `main`. To bump it:

1. Pick a new commit from [Roblox/sentinel](https://github.com/Roblox/sentinel/commits/main).
2. Update `ARG SENTINEL_COMMIT=...` in `Dockerfile`.
3. Rebuild: `docker build -t sentinel-api .`. Import errors from `app/` mean `sentinel`'s internal module
   layout moved — update the imports in `app/dependencies.py` and/or `app/routes/scoring.py` to match.
4. Smoke test: `docker run --rm -p 8000:8000 sentinel-api`, then `curl http://localhost:8000/health`.

## Tests

```bash
docker build --target builder -t sentinel-api-builder .
docker run --rm -v "$(pwd)":/workspace -w /workspace sentinel-api-builder \
  bash -c "pip install -q -r requirements-dev.txt && python -m pytest tests/ -v"
```

Routes are tested through `fastapi.testclient.TestClient` with dependencies overridden to avoid needing a
real bank or model download; `IndexManager` is tested directly, mocking only the `sentinel` calls that would
otherwise hit real model weights.

`pytest`/`httpx` are dev-only (`requirements-dev.txt`) and never ship in the runtime image. Running them
locally still needs the same heavy deps as the image (`torch`, `sentinel[sbert]`, etc.), which is why the
`builder` stage above is the easiest way to run them.
