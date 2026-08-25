<<<<<<< HEAD
# job-Description
=======
# JD Skill Extractor

A dependency-free Python pipeline that reads `job_title_des.csv` and extracts a normalized role, experience, education, and categorized skills for every row.

## Run

From this folder:

```powershell
python -m src.app
```

The result is written to `output/extracted_jobs.csv`. Override paths when needed:

```powershell
python -m src.app --input job_title_des.csv --output output/extracted_jobs.csv --taxonomy data/skill_taxonomy.json
```

`skills` is stored as JSON inside the output CSV, so it can be loaded directly by another Python service or API. Extend `data/skill_taxonomy.json` to add terms without changing the extractor.

## Live analyzer

Start the backend from this folder:

```powershell
python -m uvicorn backend.app:app --reload --port 8000
```

Start the React dashboard in a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open `http://127.0.0.1:5173/`. The dashboard sends pasted descriptions to `POST /analyze`, supports PDF, DOCX, and TXT uploads through `POST /upload`, improves copy through `POST /improve`, and saves jobs through the `/jobs` CRUD endpoints. The local repository is in-memory; `database/schema.sql` defines the Neon PostgreSQL tables for the next persistence adapter. OCR for scanned PDFs and semantic resume matching remain later integrations.

## Free deployment

The repository includes `render.yaml`, `frontend/vercel.json`, and environment templates. Push the project to GitHub, then:

1. In Render, create a Blueprint from the repository. The blueprint uses `pip install -r requirements.txt` and starts `uvicorn backend.app:app --host 0.0.0.0 --port $PORT`.
2. Create a Neon PostgreSQL project and run `database/schema.sql`. Add its connection string to Render as `DATABASE_URL`.
3. Deploy `frontend` as a Vercel project with Root Directory `frontend`, Framework `Vite`, and `VITE_API_URL` set to the Render service URL.
4. Set Render `CORS_ORIGINS` to the Vercel URL. Multiple origins may be comma-separated.

The current `/jobs` endpoints are intentionally in-memory until the database repository is connected, so data is lost when the free Render service restarts. Do not commit `.env` files or API keys.

## Test

```powershell
python -m unittest discover -s tests -v
```

## Project layout

>>>>>>> f59530e (Initial commit - AI JD Analyzer)
