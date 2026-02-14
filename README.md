# Medical Lab Reports MVP

## Run locally

1. Copy env:
   - `cp env.template .env`
2. Install deps:
   - `pip install -r requirements.txt`
3. Apply migrations:
   - `alembic upgrade head`
4. Start backend:
   - `uvicorn backend.main:app --reload`
5. Start frontend:
   - `streamlit run frontend/app.py`

### Conda setup (recommended)

- `conda create --solver=classic -y -n medlab-e2e python=3.11`
- `conda run -n medlab-e2e pip install -r requirements.txt`
- `conda run -n medlab-e2e alembic upgrade head`
- Backend:
  - `conda run -n medlab-e2e env PYTHONPATH=. uvicorn backend.main:app --host 127.0.0.1 --port 8000`
- Frontend:
  - `API_BASE_URL=http://127.0.0.1:8000 conda run -n medlab-e2e streamlit run frontend/app.py --server.port=8501 --server.address=127.0.0.1`

## Migrations (Alembic)

- Create / apply migrations:
  - `alembic revision --autogenerate -m "your message"`
  - `alembic upgrade head`
- Initial migration scaffold is available in `alembic/versions/0001_initial_schema.py`.

## Tests

- Run API smoke tests:
  - `pytest -q`

## Notes

- Keep API keys in `.env`, never hardcode.
- Upload endpoint parses PDFs using LlamaParse and structures tests via OpenAI.
- Test results are mapped to canonical biomarkers using fuzzy alias matching, then optional LLM fallback for unmatched tests.
- Classifier tuning:
  - `CLASSIFIER_FUZZY_THRESHOLD` (default `85`)
  - `CLASSIFIER_ENABLE_LLM_FALLBACK` (default `true`)

## Dependency policy

- Dependencies use recent stable compatibility ranges for security and patch updates.
- `llama-index` and `llama-parse` are intentionally in narrower ranges because their APIs change frequently.
- Before release, verify resolved versions with:
  - `pip list --outdated`
  - `pip check`
