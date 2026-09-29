# Sentinel API

A thin FastAPI wrapper around upstream [Roblox/sentinel](https://github.com/Roblox/sentinel), exposing it as
an HTTP service (`/score`, `/health`, `/banks/*`) instead of a Python library you import directly.

Sentinel is a contrastive-learning system for detecting rare text patterns (e.g. grooming, hate speech) by
comparing text against positive (rare/harmful) and negative (common/normal) example banks. This repo doesn't
change any of that logic — it just puts a small, reviewable HTTP layer in front of it so any service in any
language can call it.

## Why this exists

Roblox's own [`Dockerfile`](https://github.com/Roblox/sentinel/blob/main/Dockerfile) /
[`Dockerfile.cpu`](https://github.com/Roblox/sentinel/blob/main/Dockerfile.cpu) package the `sentinel`
_library_ and run example scripts — there's no HTTP service upstream. This repo's `Dockerfile` installs the
**unmodified upstream Roblox library** at a pinned commit as a normal Python dependency, and `app/` is a
small FastAPI application that imports it, the same way any other consumer of the `sentinel` package would.

```text
Dockerfile              # installs Roblox/sentinel (pinned) + FastAPI deps, copies app/ in
app/                     # FastAPI app — plain source, reviewable/editable like any other file
  main.py                  # app factory, lifespan (auto-loads banks on startup), /health route
  config.py                 # env-driven settings (SENTINEL_* prefix)
  dependencies.py            # IndexManager: loads/holds a SentinelLocalIndex, wraps sentinel.* calls
  schemas.py                  # request/response models
  routes/
    scoring.py                 # POST /score
    banks.py                    # /banks/{status,load,create,unload}
tests/                   # pytest suite covering app/ (see Tests below)
```

`app/` is the only thing in this repo that isn't Roblox's own code; everything it depends on (`fastapi`,
`uvicorn`, `pydantic-settings`, and the `sentinel` package itself) is installed normally in the `Dockerfile`.

`app/` originated as an API layer built by [UMass-Rescue's fork](https://github.com/UMass-Rescue/Sentinel),
which vendored it directly into a full clone of the library. Here, its files were adapted to import the
**installed** `sentinel` package (`from sentinel.sentinel_local_index import ...`, etc.) instead of relative
imports into a sibling source tree. They keep the original Apache-2.0 license header from Roblox's own files.
`app/dependencies.py` and `app/routes/scoring.py` are the files that actually reach into `sentinel`'s
internals (`sentinel.sentinel_local_index`, `sentinel.embeddings.sbert`, `sentinel.score_formulae`,
`sentinel.io.index_io`) — if Roblox renames or moves any of those, those two files need matching updates.

## Running it

```bash
docker build -t sentinel-api .
docker run --rm -p 8000:8000 sentinel-api
curl http://localhost:8000/health
```

See `app/config.py` for the full list of `SENTINEL_*` environment variables it reads (bank paths, model
name, etc.).

## Upgrading the pinned commit

Roblox has not cut a version tag yet, so `SENTINEL_COMMIT` in the `Dockerfile` pins a commit SHA rather than
a tag or `main`. To bump it:

1. Pick a new commit from [Roblox/sentinel](https://github.com/Roblox/sentinel/commits/main).
2. Update `ARG SENTINEL_COMMIT=...` in `Dockerfile`.
3. Rebuild: `docker build -t sentinel-api .`. If it fails on import errors from `app/`, `sentinel`'s internal
   module layout has moved — update the imports in `app/dependencies.py` and/or `app/routes/scoring.py` to
   match (see the previous section for exactly which modules they touch).
4. Smoke test: `docker run --rm -p 8000:8000 sentinel-api`, then `curl http://localhost:8000/health`.

## Editing the API layer

`app/` is normal Python source, versioned directly in this repo. No patch generation or regeneration step is
needed — changes show up as an ordinary diff in review.

## Tests

`tests/` covers `app/` with `pytest` — routes are tested through `fastapi.testclient.TestClient` with
`get_loaded_index`/`get_index_manager` overridden to avoid needing a real bank or model download;
`app/dependencies.py`'s `IndexManager` is tested directly, mocking only the `sentinel` calls that would
otherwise hit real model weights (`SentinelLocalIndex`, `get_sentence_transformer_and_scaling_fn`).

`pytest` and `httpx` (required by `TestClient`) are dev-only — they're in `requirements-dev.txt`, not the
`Dockerfile`, so they never ship in the runtime image. Running them locally still needs the same production
dependencies as the image itself (`torch`, `sentinel[sbert]`, `fastapi`, `uvicorn`, `pydantic-settings`), so
the easiest way to run them is against the `builder` stage, which already has all of that installed:

```bash
docker build --target builder -t sentinel-api-builder .
docker run --rm -v "$(pwd)":/workspace -w /workspace sentinel-api-builder \
  bash -c "pip install -q -r requirements-dev.txt && python -m pytest tests/ -v"
```

## Using this with Coop

[UMass-Rescue/coop-public](https://github.com/UMass-Rescue/coop-public) is the reference consumer: its
`server/services/sentinelService` is a typed HTTP client for this API, and its Sentinel integration lets an
org point `SENTINEL_API_URL` at wherever this service is deployed. See that repo's
`docs/testing/sentinel-manual-test-plan.md` for an end-to-end example of running this alongside Coop locally.

There's nothing Coop-specific about this repo itself, though — any service that can make an HTTP call can
use it.
