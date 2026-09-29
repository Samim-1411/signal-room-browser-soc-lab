# Signal Room — Browser SOC Lab

A browser cybersecurity training lab backed by SQLite. It simulates SOC alert triage, example account context, event search, investigation notes, and guided analyst exercises.

## Run in GitHub Codespaces

1. Open this repository on GitHub and select **Code → Codespaces → Create codespace on main**.
2. When the Codespace opens, run `./run.sh` in its terminal.
3. Open the forwarded port **8123**. The Codespace is configured to open it automatically; if it does not, use the **Ports** tab.
4. Press Control-C in the terminal to stop the app.

The lab requires Python 3.9+. SQLite is included with Python; no packages, Docker, separate database service, or internet access are required. In Codespaces, the server listens on the forwarded interface so the browser can reach it.

## Run locally

1. Open this folder in Terminal.
2. Run `./run.sh` (or `python3 server.py`).
3. Open <http://127.0.0.1:8123> in your browser.
4. Press Control-C in Terminal to stop the app.
5. If it stops again, open the Codespace terminal and run: /home/codespace/.python/current/bin/python3 server.py

## SQLite database

The app creates and seeds `data/signal-room.sqlite3` if it is missing. It contains fictional example accounts, alerts, and events. The browser gets data through a same-origin API. Alert dispositions and investigation notes are stored in SQLite; learning progress stays in this browser's local storage.

The database is local to the workspace. Back it up before replacing or deleting it. To return alert statuses and notes to their original training state, use **Reset training data** in the alert queue. It leaves account and event seed data intact.

## Features

- Interactive overview and searchable alert queue
- Five invented example accounts connected to alerts and related event records
- Event explorer backed by parameterized SQLite search
- Triage status and analyst notes persisted to SQLite
- Three guided analyst lessons
- Responsive desktop and mobile layouts

This is a simulation, not a security product: it does not scan devices, send network traffic, or connect to real accounts. Do not put real credentials or personal data in the training records.
