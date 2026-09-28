#!/usr/bin/env python3
"""Local-only API and static server for Signal Room's SQLite training lab."""
from __future__ import annotations

import json
import mimetypes
import os
import sqlite3
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit

ROOT = Path(__file__).resolve().parent
DB_PATH = Path(os.environ.get("SOC_LAB_DB", ROOT / "data" / "signal-room.sqlite3")).expanduser().resolve()
HOST = "127.0.0.1"
PORT = int(os.environ.get("PORT", "8123"))

ACCOUNTS = [
    ("j.chen", "Jordan Chen", "Finance analyst", "Employee", "FIN-WS-08", "Unusual sign-in"),
    ("lab-demo", "Lab Demo", "Training identity", "Demo user", "LAB-LNX-02", "7 SSH failures"),
    ("m.rao", "Meera Rao", "Development engineer", "Employee", "ENG-MBP-04", "Rare domain lookup"),
    ("build-agent", "Build Agent", "CI service account", "Service account", "CI-01", "Group change"),
    ("ops-demo", "Ops Demo", "Operations trainer", "Demo user", "OPS-SIM-01", "Approved change"),
]
ALERTS = [
    ("SOC-1042", "j.chen", "Unusual sign-in location", "high", "Identity", "A successful sign-in for j.chen was followed by a second sign-in from a distant, unfamiliar location 11 minutes later. The session is still active in this simulation.", "192.0.2.55", "09:38:12 UTC", "09:38:12  auth.success  user=j.chen  source=192.0.2.55    device=unknown app=web-portal\n09:39:01  mfa.challenge  user=j.chen  result=approved", "Compare device identity, MFA context, and the user's expected travel. A location anomaly is a lead, not proof of compromise."),
    ("SOC-1039", "lab-demo", "Repeated SSH authentication failures", "medium", "Authentication", "Seven failed SSH authentication events appeared over two minutes for a fictional lab account. No successful login is present in the sample window.", "203.0.113.77", "09:31:46 UTC", "09:29:10  sshd  Failed password user=lab-demo source=203.0.113.77\n09:29:33  sshd  Failed password user=lab-demo source=203.0.113.77\n09:31:46  sshd  Failed password user=lab-demo source=203.0.113.77 count=7 window=120s", "Check for a later success, confirm whether the source is expected, and look for other affected accounts. The address is reserved for documentation."),
    ("SOC-1034", "m.rao", "Rare outbound domain observed", "medium", "Network", "A development laptop requested a domain not seen in its recent baseline. The domain is fictional and reserved for examples.", "198.51.100.42", "09:18:03 UTC", "09:18:03  dns.query  host=ENG-MBP-04  qname=updates.example.invalid\n09:18:04  process  name=browser  user=m.rao  parent=launchd", "Identify the process and destination context, then compare against approved software and recent user activity. A rare domain alone is not a verdict."),
    ("SOC-1028", "build-agent", "New admin group membership", "low", "Change", "A fictional service account was added to a local administrator group during a scheduled maintenance window.", "192.0.2.18", "08:54:29 UTC", "08:54:29  group.change  actor=ops-demo  target=build-agent  group=local-admins\n08:51:00  change.ticket  id=CHG-204  window=08:45-09:15 UTC", "Compare the change with its ticket, approved actor, and maintenance window. Document a benign disposition if all details match."),
]
EVENTS = [
    ("09:39:01.044 UTC", "IDENTITY", "j.chen", "FIN-WS-08", "192.0.2.55", "mfa.challenge user=j.chen result=approved device=unknown source=192.0.2.55"),
    ("09:38:12.611 UTC", "IDENTITY", "j.chen", "FIN-WS-08", "192.0.2.55", "auth.success user=j.chen source=192.0.2.55 device=unknown app=web-portal"),
    ("09:31:46.270 UTC", "AUTH", "lab-demo", "LAB-LNX-02", "203.0.113.77", "sshd.failure user=lab-demo source=203.0.113.77 count=7 window=120s"),
    ("09:29:10.028 UTC", "AUTH", "lab-demo", "LAB-LNX-02", "203.0.113.77", "sshd.failure user=lab-demo source=203.0.113.77 method=password"),
    ("09:27:04.195 UTC", "IDENTITY", "j.chen", "FIN-WS-08", "198.51.100.24", "auth.success user=j.chen source=198.51.100.24 device=FIN-WS-08 app=web-portal"),
    ("09:18:04.322 UTC", "PROCESS", "m.rao", "ENG-MBP-04", "", "process.start name=browser user=m.rao parent=launchd"),
    ("09:18:03.919 UTC", "NETWORK", "m.rao", "ENG-MBP-04", "", "dns.query qname=updates.example.invalid host=ENG-MBP-04 process=browser"),
    ("09:14:20.008 UTC", "NETWORK", "m.rao", "ENG-MBP-04", "", "dns.query qname=packages.example.invalid host=ENG-MBP-04 process=package-helper"),
    ("08:54:29.441 UTC", "CHANGE", "build-agent", "CI-01", "", "group.change actor=ops-demo target=build-agent group=local-admins"),
    ("08:51:00.000 UTC", "CHANGE", "ops-demo", "CI-01", "", "change.ticket id=CHG-204 window=08:45-09:15 UTC status=approved"),
    ("08:44:09.152 UTC", "AUTH", "casey-demo", "HR-WS-03", "192.0.2.88", "auth.failure user=casey-demo source=192.0.2.88 reason=invalid-password"),
    ("08:40:33.827 UTC", "NETWORK", "casey-demo", "HR-WS-03", "", "dns.query qname=portal.example.invalid host=HR-WS-03 process=browser"),
]


def connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(DB_PATH, timeout=10)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("PRAGMA foreign_keys=ON")
    return db


def init_db():
    with connect() as db:
        db.executescript("""
          CREATE TABLE IF NOT EXISTS accounts (
            account_id TEXT PRIMARY KEY, display_name TEXT NOT NULL,
            role TEXT NOT NULL, account_type TEXT NOT NULL, device TEXT NOT NULL, signal TEXT NOT NULL
          );
          CREATE TABLE IF NOT EXISTS alerts (
            alert_id TEXT PRIMARY KEY, account_id TEXT NOT NULL REFERENCES accounts(account_id),
            title TEXT NOT NULL, severity TEXT NOT NULL CHECK(severity IN ('high','medium','low')),
            kind TEXT NOT NULL, summary TEXT NOT NULL, source_ip TEXT NOT NULL,
            detected TEXT NOT NULL, evidence TEXT NOT NULL, analyst_lead TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'open' CHECK(status IN ('open','investigating','escalated','resolved')),
            notes TEXT NOT NULL DEFAULT ''
          );
          CREATE TABLE IF NOT EXISTS events (
            event_id INTEGER PRIMARY KEY, event_time TEXT NOT NULL, event_type TEXT NOT NULL,
            account_id TEXT NOT NULL, host TEXT NOT NULL, source_ip TEXT NOT NULL DEFAULT '',
            details TEXT NOT NULL
          );
        """)
        if db.execute("SELECT COUNT(*) FROM accounts").fetchone()[0] == 0:
            db.executemany("INSERT INTO accounts VALUES (?,?,?,?,?,?)", ACCOUNTS)
        if db.execute("SELECT COUNT(*) FROM alerts").fetchone()[0] == 0:
            db.executemany("INSERT INTO alerts(alert_id,account_id,title,severity,kind,summary,source_ip,detected,evidence,analyst_lead) VALUES (?,?,?,?,?,?,?,?,?,?)", ALERTS)
        if db.execute("SELECT COUNT(*) FROM events").fetchone()[0] == 0:
            db.executemany("INSERT INTO events(event_time,event_type,account_id,host,source_ip,details) VALUES (?,?,?,?,?,?)", EVENTS)


def json_bytes(value):
    return json.dumps(value, ensure_ascii=False).encode("utf-8")


class Handler(BaseHTTPRequestHandler):
    server_version = "SignalRoom/1.0"

    def log_message(self, fmt, *args):
        print("%s - %s" % (self.address_string(), fmt % args))

    def send_json(self, value, status=200):
        body = json_bytes(value)
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def read_json(self):
        length = int(self.headers.get("Content-Length", "0"))
        if length > 16384:
            raise ValueError("Request body is too large")
        value = json.loads(self.rfile.read(length) or b"{}")
        if not isinstance(value, dict):
            raise ValueError("JSON request body must be an object")
        return value

    def do_GET(self):
        parsed = urlsplit(self.path)
        if parsed.path.startswith("/api/"):
            return self.api_get(parsed.path, parse_qs(parsed.query))
        return self.serve_file(parsed.path)

    def api_get(self, path, query):
        with connect() as db:
            if path == "/api/health":
                return self.send_json({"ok": True, "database": "sqlite", "storage": str(DB_PATH.name)})
            if path == "/api/accounts":
                rows = db.execute("""
                  SELECT a.account_id AS id,a.display_name AS name,a.role,a.account_type AS type,a.device,a.signal,
                         al.alert_id AS alert,al.title AS alertTitle,al.severity
                  FROM accounts a LEFT JOIN alerts al ON al.account_id=a.account_id ORDER BY a.account_id
                """).fetchall()
                return self.send_json([dict(r) for r in rows])
            if path == "/api/alerts":
                rows = db.execute("""
                  SELECT x.alert_id AS id,x.title,x.severity,x.kind,x.summary,x.source_ip AS ip,x.detected AS time,
                         x.evidence,x.analyst_lead AS recommendation,x.status,x.notes,x.account_id AS user,
                         a.device AS host,a.account_id || ' · host: ' || a.device AS source
                  FROM alerts x JOIN accounts a ON a.account_id=x.account_id ORDER BY
                    CASE x.severity WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END,x.detected DESC
                """).fetchall()
                return self.send_json([dict(r) for r in rows])
            if path == "/api/events":
                term = (query.get("q") or [""])[0].strip()
                like = "%" + term + "%"
                rows = db.execute("""
                  SELECT e.event_time AS time,e.event_type AS type,e.account_id AS account,
                         e.host,e.source_ip,e.details
                  FROM events e
                  WHERE ? = '' OR e.event_time LIKE ? OR e.event_type LIKE ? OR e.account_id LIKE ?
                     OR e.host LIKE ? OR e.source_ip LIKE ? OR e.details LIKE ?
                  ORDER BY e.event_id LIMIT 200
                """, (term,like,like,like,like,like,like)).fetchall()
                return self.send_json([dict(r) for r in rows])
        self.send_json({"error":"Not found"},404)

    def do_PATCH(self):
        path = urlsplit(self.path).path
        prefix = "/api/alerts/"
        if not path.startswith(prefix):
            return self.send_json({"error":"Not found"},404)
        alert_id = unquote(path[len(prefix):])
        try:
            data = self.read_json()
        except (ValueError, json.JSONDecodeError) as exc:
            return self.send_json({"error":str(exc)},400)
        updates = {}
        if "status" in data:
            if data["status"] not in {"open","investigating","escalated","resolved"}:
                return self.send_json({"error":"Invalid status"},400)
            updates["status"] = data["status"]
        if "notes" in data:
            if not isinstance(data["notes"], str) or len(data["notes"]) > 4000:
                return self.send_json({"error":"Notes must be text up to 4000 characters"},400)
            updates["notes"] = data["notes"]
        if not updates:
            return self.send_json({"error":"No supported fields supplied"},400)
        with connect() as db:
            columns = list(updates)
            sql = "UPDATE alerts SET " + ",".join(k + "=?" for k in columns) + " WHERE alert_id=?"
            cur = db.execute(sql, [updates[k] for k in columns] + [alert_id])
            if cur.rowcount == 0:
                return self.send_json({"error":"Alert not found"},404)
        self.send_json({"ok":True,"id":alert_id,**updates})

    def do_POST(self):
        path = urlsplit(self.path).path
        if path != "/api/reset":
            return self.send_json({"error":"Not found"},404)
        with connect() as db:
            db.execute("UPDATE alerts SET status='open',notes='' ")
        self.send_json({"ok":True})

    def serve_file(self, path):
        rel = unquote(path).lstrip("/") or "index.html"
        target = (ROOT / rel).resolve()
        if ROOT not in target.parents and target != ROOT:
            return self.send_error(403)
        if not target.is_file():
            return self.send_error(404)
        content = target.read_bytes()
        mime = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
        self.send_response(200)
        self.send_header("Content-Type", mime + ("; charset=utf-8" if mime.startswith(("text/", "application/javascript")) else ""))
        self.send_header("Content-Length", str(len(content)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(content)

    def do_HEAD(self):
        if urlsplit(self.path).path.startswith("/api/"):
            self.send_json({"error":"Method not allowed"},405)
        else:
            self.send_error(405)


if __name__ == "__main__":
    init_db()
    print("Signal Room SQLite lab: http://%s:%d" % (HOST, PORT))
    print("SQLite file: %s" % DB_PATH)
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
