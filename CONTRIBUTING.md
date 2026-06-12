# Contributing to LakeWatch

Thanks for helping. LakeWatch is a fork-able kit, so the most valuable
contributions keep the **core generic** and push city-specific logic into the
extension seams.

## Ground rules

- **Keep the core city-agnostic.** Anything specific to one city (lake names,
  local data sources, regulatory data) belongs in the extension seams, not in
  shared files. See the "Extension pattern" section of the README.
- **Don't break the seams.** Shared files must keep working when the extension
  files are absent (`HAS_CITY_EXTENSIONS` on the Python side; the no-op
  `api-ext.ts` / `extensions/index.tsx` on the frontend). If a shared file
  needs city data, route it through those seams.
- **No secrets, ever.** No real `DATABASE_URL`, GEE keys, Mapbox tokens, or API
  keys in commits. `.env` and key files are gitignored — keep it that way.

## Dev setup

See [`docs/SETUP.md`](docs/SETUP.md) for full environment setup. In short:

```bash
cd pipeline && uv sync && uv run pytest
cd ../backend && uv sync && uv run pytest
cd ../frontend && npm install && npm run build
```

## Style & checks

- Python: `ruff check .` and `ruff format .` (line length 100).
- TypeScript: `npm run lint` in `frontend/`.
- Add or update tests for behavior changes. Pipeline tests mock Earth Engine;
  backend tests mock the database — neither needs live credentials.

## Pull requests

- One focused change per PR. Describe what and why.
- Make sure pipeline + backend tests pass and the frontend builds.
- If you touch a shared file, confirm it still degrades gracefully without the
  extension files present.
