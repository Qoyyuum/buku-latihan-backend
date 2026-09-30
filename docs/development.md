# Development & checks

## Backend (Python)

Toolchain: **uv** for env/deps, **ruff** for lint+format, **ty** for type
checking (with `django-stubs` basic support), **pytest** for tests.

```bash
cd backend
uv sync --dev

uv run ruff check .          # lint
uv run ruff format --check . # formatting (ruff format to fix)
uv run ty check              # type check
uv run pytest                # tests (config.settings.test → sqlite)
uv run python manage.py check
uv run python manage.py spectacular --file schema.yml   # OpenAPI dump
```

Rules of thumb:

- `ty` can't run the django-stubs *mypy plugin* — some ORM magic
  (reverse relations, `_id` fields) isn't visible; write explicit queries
  instead of silencing.
- Ruff `S`/`DJ`/`B` rules are on; test passwords are exempted via
  per-file ignores — see `pyproject.toml`.

## Frontend (TypeScript)

```bash
cd frontend
npx tsc --noEmit                 # strict typecheck
npx expo lint                    # eslint-config-expo + react-hooks rules
npx expo export --platform web   # full static-build smoke test
npx expo-doctor                  # dependency/config sanity
```

- Routes live only in `src/app/`; all other code in `src/{api,auth,
  components,constants,hooks,offline}`.
- Expo APIs change per SDK — check `https://docs.expo.dev/versions/v57.0.0/`
  before using an unfamiliar module; install Expo packages with
  `npx expo install`.

## Conventions

- Strokes are normalized vectors (x, y in 0–1); never store pixel coords.
- File bodies never pass through Django — always presigned PUT/GET.
- `auto_suggested` marks are AI output — only teachers return marks.
- Keep secrets in `.env` files (`deploy/.env`, `backend/.env`), never
  committed; `.env.example` files document the required variables.
