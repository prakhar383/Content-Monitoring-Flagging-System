# Content Monitoring & Flagging System

A Django REST Framework backend that ingests content, scores keyword
matches, and supports a human review workflow with suppression rules.

---

## Tech Stack

- Python 3.13
- Django 5.x
- Django REST Framework
- SQLite (local development)

---

## Setup Instructions

### 1. Clone the repository
git clone https://github.com/YOUR_USERNAME/content-monitor.git
cd content-monitor

### 2. Create and activate virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # Mac/Linux

### 3. Install dependencies
pip install django djangorestframework

### 4. Apply migrations
python manage.py migrate

### 5. Run the development server
python manage.py runserver

---

## API Endpoints

### Create a keyword
POST /api/keywords/
Content-Type: application/json
{"name": "django"}

### List all keywords
GET /api/keywords/

### Trigger a scan
POST /api/scan/

### List all flags
GET /api/flags/

### Filter flags by status
GET /api/flags/?status=pending
GET /api/flags/?status=relevant
GET /api/flags/?status=irrelevant

### Update flag status (reviewer workflow)
PATCH /api/flags/{id}/
Content-Type: application/json
{"status": "irrelevant"}

---

## Sample curl Commands

# Add keywords
curl -X POST http://127.0.0.1:8000/api/keywords/ -H "Content-Type: application/json" -d "{\"name\": \"python\"}"
curl -X POST http://127.0.0.1:8000/api/keywords/ -H "Content-Type: application/json" -d "{\"name\": \"django\"}"
curl -X POST http://127.0.0.1:8000/api/keywords/ -H "Content-Type: application/json" -d "{\"name\": \"automation\"}"
curl -X POST http://127.0.0.1:8000/api/keywords/ -H "Content-Type: application/json" -d "{\"name\": \"data pipeline\"}"

# Run scan
curl -X POST http://127.0.0.1:8000/api/scan/

# List flags
curl http://127.0.0.1:8000/api/flags/

# Mark as irrelevant
curl -X PATCH http://127.0.0.1:8000/api/flags/1/ -H "Content-Type: application/json" -d "{\"status\": \"irrelevant\"}"

# Scan again — suppression kicks in
curl -X POST http://127.0.0.1:8000/api/scan/

---

## Scoring Logic

| Match type                  | Score |
|-----------------------------|-------|
| Exact keyword in title      | 100   |
| Partial keyword in title    | 70    |
| Keyword only in body        | 40    |
| No match                    | 0     |

---

## Suppression Logic

If a flag is marked **irrelevant** by a reviewer, it will not
reappear on future scans UNLESS the underlying ContentItem's
`last_updated` timestamp is newer than the `reviewed_at` timestamp
on the flag. This is tracked in `services.py → should_suppress()`.

---

## Content Source

This project uses a **local mock JSON dataset** (`monitor/mock_data.json`)
as the content source. The fetch logic lives in `ScanService.fetch_content()`
inside `monitor/services.py`. Switching to a live API (NewsAPI, RSS)
requires only changing that one method.

---

## Project Structure

content_monitor/
├── core/
│   ├── settings.py       # project configuration
│   └── urls.py           # root URL dispatcher
├── monitor/
│   ├── models.py         # Keyword, ContentItem, Flag
│   ├── serializers.py    # JSON conversion + validation
│   ├── views.py          # API endpoint handlers
│   ├── services.py       # scan logic, scoring, suppression
│   ├── urls.py           # app-level URL patterns
│   └── mock_data.json    # sample content dataset
└── manage.py

---

## Assumptions & Trade-offs

- Used mock JSON instead of a live API to keep setup self-contained
  and reproducible. The service layer makes swapping this trivial.
- SQLite used for simplicity as permitted by the assignment.
- No authentication added — would use JWT in production.
- `unique_together` on Flag prevents duplicate flags per keyword+article pair.
- Suppression uses `reviewed_at` timestamp vs `last_updated` for
  a simple, deterministic, and easy-to-verify rule.
