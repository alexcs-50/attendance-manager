import csv
import hmac
import io
import os
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import psycopg
from flask import Flask, Response, jsonify, request, send_file
from psycopg.rows import dict_row

app = Flask(__name__, static_folder=None)
app.config["MAX_CONTENT_LENGTH"] = 2_000_000
ROOT = Path(__file__).resolve().parent


@app.before_request
def authorize():
    password = os.environ.get("ADMIN_PASSWORD")
    if not password or not os.environ.get("DATABASE_URL"):
        return jsonify(error="Set ADMIN_PASSWORD and DATABASE_URL in Vercel, then redeploy."), 503
    user = request.authorization
    if not (user and user.type == "basic" and user.username == "teacher"
            and hmac.compare_digest((user.password or "").encode(), password.encode())):
        return Response("Teacher sign-in required.", 401,
                        {"WWW-Authenticate": 'Basic realm="Attendance Manager", charset="UTF-8"'})


@app.after_request
def prevent_caching(response):
    response.headers["Cache-Control"] = "private, no-store"
    return response


@app.errorhandler(ValueError)
def invalid(error):
    return jsonify(error=str(error)), 400


@app.errorhandler(psycopg.Error)
def database_error(error):
    app.logger.error("Database failure: %s", type(error).__name__)
    return jsonify(error="Database unavailable. Check DATABASE_URL and run schema.sql in Neon."), 503


def connect():
    return psycopg.connect(os.environ["DATABASE_URL"], row_factory=dict_row, connect_timeout=10)


def today():
    return datetime.now(ZoneInfo("Asia/Kolkata")).date()


def checked(value):
    if not isinstance(value, str):
        raise ValueError("Choose a date.")
    day = date.fromisoformat(value)
    if day.isoformat() != value or day > today():
        raise ValueError("Choose a valid date on or before today.")
    return day


def roster(db, day):
    return db.execute("""SELECT s.id,s.name,s.roll,a.status FROM students s
        LEFT JOIN attendance a ON a.student_id=s.id AND a.day=%s
        ORDER BY lower(s.roll)""", (day,)).fetchall()


@app.get("/")
def index():
    return send_file(ROOT / "register.html")


@app.post("/api/students")
def add_student():
    body = request.get_json()
    if not isinstance(body, dict):
        raise ValueError("Enter a roll number and name.")
    values = []
    for key, limit in (("roll", 30), ("name", 100)):
        value = body.get(key)
        if not isinstance(value, str) or not 1 <= len(value.strip()) <= limit:
            raise ValueError(f"Enter a valid {key} (up to {limit} characters).")
        values.append(value.strip())
    try:
        with connect() as db:
            db.execute("SELECT pg_advisory_xact_lock(44021)")
            db.execute("INSERT INTO students(roll,name) VALUES (%s,%s)", values)
    except psycopg.errors.UniqueViolation:
        return jsonify(error="That roll number already exists."), 409
    return jsonify(saved=True)


@app.route("/api/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        day = checked(request.args.get("day", today().isoformat()))
        with connect() as db:
            return jsonify(day=day.isoformat(), students=roster(db, day))
    body = request.get_json()
    if not isinstance(body, dict):
        raise ValueError("Invalid register.")
    day = checked(body.get("day"))
    marks = body.get("marks")
    with connect() as db:
        db.execute("SELECT pg_advisory_xact_lock(44021)")
        original = {str(s["id"]): s["status"] for s in roster(db, day)}
        if body.get("original") != original:
            return jsonify(error="The register changed. Reload the day."), 409
        if (not original or not isinstance(marks, dict) or marks.keys() != original.keys()
                or any(v not in ("Present", "Absent") for v in marks.values())):
            raise ValueError("Select a status for every student.")
        with db.cursor() as cur:
            cur.executemany("""INSERT INTO attendance(day,student_id,status) VALUES (%s,%s,%s)
                ON CONFLICT(day,student_id) DO UPDATE SET status=excluded.status""",
                [(day, int(student), status) for student, status in marks.items()])
    return jsonify(saved=True)


@app.get("/api/report")
@app.get("/summary.csv")
def report():
    start, end = (checked(request.args.get(key)) for key in ("start", "end"))
    if start > end:
        raise ValueError("Start date must come before or equal the end date.")
    with connect() as db:
        rows = db.execute("""SELECT s.roll,s.name,count(a.status) AS marked,
            count(*) FILTER(WHERE a.status='Present') AS present,
            count(*) FILTER(WHERE a.status='Absent') AS absent
            FROM students s LEFT JOIN attendance a ON a.student_id=s.id AND a.day BETWEEN %s AND %s
            GROUP BY s.id ORDER BY lower(s.roll)""", (start, end)).fetchall()
    for r in rows:
        r["percent"] = round(100*r["present"]/r["marked"], 1) if r["marked"] else None
    if request.path == "/api/report":
        return jsonify(rows)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Roll","Student","Marked days","Present","Absent","Attendance (%)"])
    for r in rows:
        values = [r[k] for k in ("roll","name","marked","present","absent","percent")]
        writer.writerow(["'" + v if isinstance(v, str) and v.lstrip().startswith(("=", "+", "-", "@")) else v for v in values])
    return Response(output.getvalue().encode("utf-8-sig"), mimetype="text/csv",
                    headers={"Content-Disposition": 'attachment; filename="attendance-summary.csv"'})
