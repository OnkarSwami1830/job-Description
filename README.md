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
$env:MONGODB_URI = "mongodb://127.0.0.1:27017"
$env:MONGODB_DATABASE = "talentlens"
python -m uvicorn backend.app:app --reload --port 8000
```

MongoDB is required for login, registration, and saved jobs. Set `MONGODB_URI` to a MongoDB Atlas connection string when using a hosted database. The frontend opens on a login screen; create an account, then analyze and save jobs in the authenticated workspace.

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
2. Create a MongoDB Atlas database and add its connection string to Render as `MONGODB_URI`. Set `MONGODB_DATABASE` to `talentlens` and provide a strong `TOKEN_SECRET`.
3. The Blueprint also defines the frontend as a Render static site. It uses `frontend` as its root directory, runs `npm install && npm run build`, and publishes `dist`. The repository root also includes a compatibility `package.json` and build script for existing Render services still configured at the repository root. Set `VITE_API_URL` to the backend service URL.
4. Set Render `CORS_ORIGINS` to the frontend URL. Multiple origins may be comma-separated. Alternatively, deploy `frontend` on Vercel with Root Directory `frontend` and the same `VITE_API_URL` setting.

The `/jobs` endpoints persist authenticated jobs in MongoDB. Do not commit `.env` files or API keys.

## Test

```powershell
python -m unittest discover -s tests -v
```

## Project layout

- `backend/app.py`: FastAPI API, MongoDB auth/jobs, and Gemini integrations
- `src/extractors.py`: role, skill, experience, and education extraction
- `frontend/src/main.jsx`: React dashboard and authentication UI
- `data/skill_taxonomy.json`: editable skill categories and terms
