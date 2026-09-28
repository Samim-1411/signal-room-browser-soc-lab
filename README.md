# Signal Room — Browser SOC Lab

A local browser cybersecurity training lab backed by SQLite. It simulates SOC alert triage, example account context, event search, investigation notes, and guided analyst exercises.

## Run locally

1. Open this folder in Terminal.
2. Run `./run.sh` (or `python3 server.py`).
3. Open <http://127.0.0.1:8123> in your browser.
4. Press Control-C in Terminal to stop the app.

Python 3.9+ is required. SQLite is included with Python; no packages, Docker, database service, or internet access are required.

## SQLite database

The project includes `data/signal-room.sqlite3`, seeded with fictional example accounts, alerts, and events. If the database file is missing, the app creates and seeds it on startup. The browser gets data through a small same-origin API. Alert dispositions and investigation notes are stored in SQLite; learning progress stays in this browser's local storage.

The database is local to this project. Back up the SQLite file before replacing or deleting it. To return alert statuses and notes to their original training state, use **Reset training data** in the alert queue. It leaves account and event seed data intact.

## Features

- Interactive overview and searchable alert queue
- Five invented example accounts connected to alerts and related event records
- Event explorer backed by parameterized SQLite search
- Triage status and analyst notes persisted to SQLite
- Three guided analyst lessons
- Responsive desktop and mobile layouts

The app binds its server to `127.0.0.1` only. It is a simulation, not a security product: it does not scan devices, send network traffic, or connect to real accounts. Do not put real credentials or personal data in the training records.
