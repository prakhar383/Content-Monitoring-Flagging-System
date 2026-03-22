# FlagEngine 🚩
### Content Monitoring & Flagging System

A Django REST API that scans content for keyword matches, scores them
by relevance, and manages a human review workflow with intelligent
suppression logic.

> **Content Source:** This project uses a local mock JSON dataset
> (`monitor/mock_data.json`). No external API keys are required.
> The project runs fully offline out of the box.

---

## Tech Stack

| Layer        | Technology                 |
|--------------|----------------------------|
| Language     | Python 3.13                |
| Framework    | Django 5.x                 |
| API Layer    | Django REST Framework       |
| Database     | SQLite (local development) |
| Data Source  | Mock JSON dataset           |

---

## Setup Instructions

### 1. Clone the repository
```bash
git clone https://github.com/prakhar383/Content-Monitoring-Flagging-System.git
cd Content-Monitoring-Flagging-System
```

### 2. Create and activate virtual environment
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Mac / Linux
source venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Apply migrations
```bash
python manage.py migrate
```

### 5. Run the development server
```bash
python manage.py runserver
```

Server starts at → http://127.0.0.1:8000

---

## Running Tests
```bash
python manage.py test monitor
```

Expected output:
```
Found 21 tests...
.....................
----------------------------------------------------------------------
Ran 21 tests in 0.070s

OK
```

Tests cover scoring logic, suppression rules, all API endpoints,
and the full scan integration flow.

---

## API Endpoints

| Method | Endpoint           | Description                         |
|--------|--------------------|-------------------------------------|
| POST   | /api/keywords/     | Create a new keyword                |
| GET    | /api/keywords/     | List all keywords                   |
| POST   | /api/scan/         | Trigger a full content scan         |
| GET    | /api/flags/        | List all flags (supports filtering) |
| PATCH  | /api/flags/{id}/   | Update flag status (reviewer)       |

---

## Sample curl Commands

### 1. Add keywords
```bash
curl -X POST http://127.0.0.1:8000/api/keywords/ \
  -H "Content-Type: application/json" \
  -d "{\"name\": \"python\"}"

curl -X POST http://127.0.0.1:8000/api/keywords/ \
  -H "Content-Type: application/json" \
  -d "{\"name\": \"django\"}"

curl -X POST http://127.0.0.1:8000/api/keywords/ \
  -H "Content-Type: application/json" \
  -d "{\"name\": \"automation\"}"

curl -X POST http://127.0.0.1:8000/api/keywords/ \
  -H "Content-Type: application/json" \
  -d "{\"name\": \"data pipeline\"}"
```

### 2. Trigger a scan
```bash
curl -X POST http://127.0.0.1:8000/api/scan/
```

Expected response:
```json
{
  "message": "Scan completed successfully.",
  "results": {
    "keywords_scanned": 4,
    "articles_scanned": 6,
    "flags_created": 7,
    "flags_suppressed": 0
  }
}
```

### 3. View all flags
```bash
curl http://127.0.0.1:8000/api/flags/
```

### 4. Filter flags by status
```bash
curl http://127.0.0.1:8000/api/flags/?status=pending
curl http://127.0.0.1:8000/api/flags/?status=relevant
curl http://127.0.0.1:8000/api/flags/?status=irrelevant
```

### 5. Reviewer marks a flag
```bash
# Mark as irrelevant
curl -X PATCH http://127.0.0.1:8000/api/flags/1/ \
  -H "Content-Type: application/json" \
  -d "{\"status\": \"irrelevant\"}"

# Mark as relevant
curl -X PATCH http://127.0.0.1:8000/api/flags/2/ \
  -H "Content-Type: application/json" \
  -d "{\"status\": \"relevant\"}"
```

### 6. Scan again — suppression kicks in
```bash
curl -X POST http://127.0.0.1:8000/api/scan/
```

Expected response after marking flags irrelevant:
```json
{
  "message": "Scan completed successfully.",
  "results": {
    "keywords_scanned": 4,
    "articles_scanned": 6,
    "flags_created": 0,
    "flags_suppressed": 1
  }
}
```

---

## Scoring Logic

Scores are computed in `monitor/services.py → ScanService.compute_score()`.

| Match Type                 | Score |
|----------------------------|-------|
| Exact keyword in title     | 100   |
| Partial keyword in title   | 70    |
| Keyword only in body       | 40    |
| No match                   | 0     |

Flags are returned ordered by score (highest first) so reviewers
see the most confident matches at the top.

---

## Suppression Logic

This is the core business rule of the system.

If a flag is marked **irrelevant** by a reviewer:
- The system records a `reviewed_at` timestamp on the flag
- On the next scan, if the article's `last_updated` is **older** than
  `reviewed_at` → the flag is **suppressed** (skipped silently)
- If the article was **updated after** the review → the flag
  **resurfaces** as pending for a fresh look

This logic lives in `monitor/services.py → ScanService.should_suppress()`.
```
Flag marked irrelevant?
  └── YES → article updated after review?
              └── YES → resurface as pending (content changed)
              └── NO  → suppress (same old article, skip it)
  └── NO  → never suppress (pending/relevant always show)
```

---

## Project Structure
```
FlagEngine/
│
├── core/
│   ├── settings.py          # project configuration
│   ├── urls.py              # root URL dispatcher
│   ├── wsgi.py              # WSGI entry point
│   └── asgi.py              # ASGI entry point
│
├── monitor/
│   ├── migrations/
│   │   └── 0001_initial.py  # auto-generated DB migration
│   ├── models.py            # Keyword, ContentItem, Flag
│   ├── serializers.py       # JSON conversion + validation
│   ├── views.py             # API endpoint handlers
│   ├── services.py          # scan logic, scoring, suppression
│   ├── urls.py              # app-level URL patterns
│   ├── admin.py             # models registered for admin panel
│   ├── tests.py             # 21 automated tests
│   └── mock_data.json       # sample content dataset
│
├── .gitignore
├── requirements.txt         # pip dependencies
├── manage.py                # Django CLI tool
└── README.md
```

---

## Assumptions & Trade-offs

- **Mock JSON over live API** — keeps the project self-contained and
  reproducible without API keys. Switching to NewsAPI or RSS requires
  changing only `ScanService.fetch_content()`.

- **SQLite** — used as permitted by the assignment. Production would
  use PostgreSQL.

- **No authentication** — endpoints are open for simplicity. Production
  would use JWT via `djangorestframework-simplejwt`.

- **Deduplication via `unique_together`** — the database enforces that
  a keyword+article pair can only produce one flag. No duplicate logic
  needed in application code.

- **Suppression via timestamps** — simple, deterministic, and easy to
  verify. `reviewed_at` vs `last_updated` is a clear contract with no
  ambiguity.

- **Service layer** — all business logic lives in `services.py`, not
  in views. Views are kept thin — they only handle HTTP in/out.

- **Ordered by score** — `GET /flags/` returns results ordered by score
  descending so reviewers always see the highest confidence matches first.