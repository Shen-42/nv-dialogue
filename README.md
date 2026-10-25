# New Vegas Dialogue Explorer

Search Fallout: New Vegas dialogue by meaning and see which faction each line backs. React (Pip-Boy UI), FastAPI, PostgreSQL with pgvector, Docker Compose.

The project plan, with the card list and checklists, is in Claude Docs: "New Vegas Dialogue Explorer: Project Plan".

## Game text

The dialogue belongs to Bethesda. This repo holds the export script, schema and code, but never the extracted text. `data/` is in `.gitignore`. To run the app, export the data from your own copy of the game (below).

## Layout

| Folder | What it holds |
| --- | --- |
| `client/` | React app (Vite), served by nginx in Docker |
| `server/` | FastAPI app |
| `ingest/` | Scripts that check and load the exported data |
| `export/fnvedit/` | FNVEdit script that exports dialogue to CSV |
| `db/init/` | SQL that runs when the database is first created |
| `data/export/` | Your exported CSVs (ignored by git) |

## Run it with Docker

```
cp .env.example .env        # then set POSTGRES_PASSWORD
docker compose up --build
```

Open http://localhost:8080. The status screen should say ALL SYSTEMS ONLINE. The API is also on http://localhost:8000/api/health, with docs at http://localhost:8000/api/docs.

If the screen says DATABASE OFFLINE, run `docker compose logs db`.

## Run it without Docker (for development)

Start only the database in Docker:

```
docker compose up db
```

API, in a second terminal:

```
cd server
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
export DATABASE_URL=postgresql://nv:<your password>@localhost:5432/nv_dialogue
uvicorn app.main:app --reload
```

React app, in a third terminal:

```
cd client
npm install
npm run dev
```

Vite serves on http://localhost:5173 and forwards `/api` to port 8000. After the first `npm install`, commit `client/package-lock.json` so Docker builds use the same versions.

## Export the dialogue (card 2)

FNVEdit is a Windows program. Use a Windows PC, a Windows VM, or CrossOver on a Mac, plus your own copy of the game.

1. Download FNVEdit (xEdit) and copy `export/fnvedit/NVDialogueExport.pas` into its `Edit Scripts` folder.
2. Start FNVEdit and load `FalloutNV.esm` only.
3. Right-click `FalloutNV.esm` in the left pane, choose **Apply Script**, and pick `NVDialogueExport`. It takes a few minutes.
4. Copy the files from `<FNVEdit folder>\NVDialogueExport\FalloutNV.esm\` into `data/export/`.
5. Check them:

```
python ingest/check_export.py data/export --sample 20
```

The checker reports line counts, how many lines have no named speaker or quest, and prints 20 lines to compare against the game. It exits with an error if a file is missing, a header is wrong, text is empty, or a line appears twice.

Many lines have no single named speaker: generic NCR troopers, for example. For those, `speaker_conditions` holds what the game checks instead, such as `GetInFaction NCRFactionNV`.

### Exported columns

`lines.csv` has one row per response. An INFO record can hold several responses, so `(info_form_id, response_index)` is the key.

| Column | Meaning |
| --- | --- |
| `info_form_id` | Form ID of the INFO record |
| `response_index` | 1, 2, ... within the INFO |
| `topic_form_id`, `topic_editor_id`, `topic_text` | The DIAL topic the line answers |
| `quest_form_id`, `quest_editor_id` | The quest that owns the line |
| `speaker_form_id`, `speaker_editor_id`, `speaker_name` | The NPC or creature, if one is named |
| `speaker_conditions` | Other conditions on who can say it |
| `text` | The line |
| `source_file` | The plugin it came from |

`npcs.csv` lists factions as `formid:rank` pairs separated by `;`.

## Tests

```
python -m unittest discover -s ingest/tests
cd server && pytest
```
