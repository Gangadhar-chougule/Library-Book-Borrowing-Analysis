# app.py
"""
Simple single-file Flask app:
- Signup / Login (passwords hashed)
- CSV upload to populate 'borrows' collection in MongoDB
- Dashboard with interactive charts (Chart.js): Top titles (bar), Department share (pie), Monthly trend (line)
- Minimal, Instagram-ish CSS styling in the HTML template
"""

import os
from datetime import datetime
from io import TextIOWrapper

from flask import (
    Flask, render_template_string, request, redirect, url_for,
    session, jsonify, flash
)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

import pandas as pd
from pymongo import MongoClient

# -----------------------------
# Configuration - Edit as needed
# -----------------------------
MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "library_insights_db")
UPLOAD_FOLDER = "/tmp"
ALLOWED_EXTENSIONS = {'csv'}
SECRET_KEY = os.environ.get("FLASK_SECRET_KEY", "super-secret-key-change-me")

# -----------------------------
# Flask app + Mongo client
# -----------------------------
app = Flask(__name__)
app.secret_key = SECRET_KEY
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

client = MongoClient(MONGO_URI)
db = client[DB_NAME]
users_col = db['users']
borrows_col = db['borrows']  # stores records with fields like Title, Department, Count, BorrowDate, Genre

# -----------------------------
# Helper functions
# -----------------------------
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def ensure_logged_in():
    return 'user_id' in session

# -----------------------------
# HTML Template (single-file)
# -----------------------------
BASE_HTML = """
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width,initial-scale=1" />
<title>Library Data Insights</title>

<!-- Chart.js CDN -->
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>

<style>
/* --- Simple Instagram-ish / modern styling --- */
:root{
  --bg:#fafafa;
  --card:#ffffff;
  --accent1: linear-gradient(135deg,#ff7eb3 0%, #ff65a3 50%, #7afcff 100%);
  --accent2: #6a11cb;
  --muted:#9198a3;
  --glass: rgba(255,255,255,0.8);
  --rounded: 14px;
}
*{box-sizing:border-box;font-family: "Segoe UI", Roboto, Arial, sans-serif}
body{margin:0;background: linear-gradient(180deg,#f8f9fb,#eef2fb); color:#222}
.header{
  background: linear-gradient(90deg,#ff8a80,#ff80ab);
  color:white;padding:18px 28px;display:flex;align-items:center;gap:16px;
  box-shadow: 0 6px 18px rgba(20,20,60,0.08);
}
.brand{font-weight:800;font-size:20px;letter-spacing:0.2px}
.container{max-width:1200px;margin:28px auto;padding:0 18px}
.card{background:var(--card);border-radius:var(--rounded);padding:18px;margin-bottom:18px;box-shadow:0 6px 18px rgba(20,20,60,0.04)}
.row{display:flex;gap:18px;flex-wrap:wrap}
.col{flex:1;min-width:260px}
.controls{display:flex;gap:12px;align-items:center;flex-wrap:wrap}
.btn{
  display:inline-block;padding:10px 14px;border-radius:10px;border:none;cursor:pointer;font-weight:600;
  box-shadow:0 3px 10px rgba(20,20,60,0.06)
}
.btn-primary{background:#5b21b6;color:#fff}
.btn-accent{background:linear-gradient(90deg,#ff7eb3,#7afcff);color:#111}
.small{font-size:13px;color:var(--muted)}
.form-row{display:flex;gap:8px;align-items:center}
.input{padding:10px 12px;border-radius:8px;border:1px solid #e6e9f2;min-width:160px}
.center{display:flex;align-items:center;justify-content:center}
.footer{padding:14px;text-align:center;color:#fff;background:#2b2a4a;border-radius:12px;margin-top:28px}
.alert{padding:10px;border-radius:8px;background:#fff3cd;color:#5b3b00;border:1px solid #ffeeba;margin-bottom:12px}
.card-title{font-weight:700;margin-bottom:8px}
.grid-2{display:grid;grid-template-columns:1fr 1fr;gap:16px}
@media(max-width:880px){.grid-2{grid-template-columns:1fr}}
.legend-pill{display:inline-block;padding:6px 10px;border-radius:999px;background:#f1f5f9;margin-right:8px;font-size:12px}
.login-box{max-width:420px;margin:36px auto}
.nav{display:flex;gap:8px;align-items:center}
.upload-area{border:2px dashed #e6e9f2;padding:12px;border-radius:10px;background:linear-gradient(180deg, rgba(255,255,255,0.9), rgba(250,250,250,0.95))}
</style>
</head>
<body>

<div class="header">
  <div class="brand">Library Data Insights</div>
  <div style="flex:1"></div>
  {% if session.user_name %}
    <div class="small">Logged in as <strong style="margin-left:6px">{{ session.user_name }}</strong></div>
    <form method="post" action="{{ url_for('logout') }}" style="margin-left:12px">
      <button class="btn" style="background:#fff;color:#444;padding:8px 10px;border-radius:10px">Logout</button>
    </form>
  {% else %}
    <a class="btn" href="{{ url_for('login') }}">Login</a>
    <a class="btn btn-accent" href="{{ url_for('signup') }}">Sign up</a>
  {% endif %}
</div>

<div class="container">
  {% with messages = get_flashed_messages() %}
    {% if messages %}
      <div class="card">
        {% for m in messages %}
          <div class="alert">{{ m }}</div>
        {% endfor %}
      </div>
    {% endif %}
  {% endwith %}

  {% block content %}{% endblock %}
</div>

</body>
</html>
"""

# -----------------------------
# Routes: Signup / Login / Logout
# -----------------------------
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not (name and email and password):
            flash("Please fill all fields.")
            return redirect(url_for("signup"))

        if users_col.find_one({"email": email}):
            flash("Email already registered. Please login.")
            return redirect(url_for("login"))

        pw_hash = generate_password_hash(password)
        users_col.insert_one({"name": name, "email": email, "password": pw_hash, "created_at": datetime.utcnow()})
        flash("Account created. Please log in.")
        return redirect(url_for("login"))

    return render_template_string(BASE_HTML + """
    {% block content %}
    <div class="card login-box">
      <div class="card-title">Create an account</div>
      <form method="post">
        <div style="display:flex;flex-direction:column;gap:10px">
          <input class="input" name="name" placeholder="Full name" />
          <input class="input" name="email" placeholder="Email" />
          <input class="input" name="password" type="password" placeholder="Password" />
          <div style="display:flex;gap:8px;justify-content:flex-end">
            <a href="{{ url_for('login') }}" class="small">Already have an account?</a>
            <button class="btn btn-primary" type="submit">Sign up</button>
          </div>
        </div>
      </form>
    </div>
    {% endblock %}
    """, session=session)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = users_col.find_one({"email": email})
        if not user or not check_password_hash(user['password'], password):
            flash("Invalid credentials.")
            return redirect(url_for("login"))
        # Successful login
        session['user_id'] = str(user['_id'])
        session['user_name'] = user.get('name', email.split('@')[0])
        flash("Welcome, " + session['user_name'])
        return redirect(url_for("dashboard"))

    return render_template_string(BASE_HTML + """
    {% block content %}
    <div class="card login-box">
      <div class="card-title">Login</div>
      <form method="post">
        <input class="input" name="email" placeholder="Email" />
        <input class="input" name="password" type="password" placeholder="Password" />
        <div style="display:flex;gap:8px;justify-content:flex-end;margin-top:10px">
          <a href="{{ url_for('signup') }}" class="small">Create an account</a>
          <button class="btn btn-primary" type="submit">Login</button>
        </div>
      </form>
    </div>
    {% endblock %}
    """, session=session)

@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    flash("You have been logged out.")
    return redirect(url_for("login"))

# -----------------------------
# Dashboard & Upload
# -----------------------------
@app.route("/", methods=["GET"])
def home():
    if ensure_logged_in():
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))

@app.route("/dashboard", methods=["GET"])
def dashboard():
    if not ensure_logged_in():
        return redirect(url_for("login"))

    # Basic counts for quick UI
    total_records = borrows_col.count_documents({})
    unique_titles = len(borrows_col.distinct("Title"))
    return render_template_string(BASE_HTML + """
    {% block content %}
    <div class="grid-2">
      <div class="card">
        <div style="display:flex;align-items:center;justify-content:space-between">
          <div>
            <div class="card-title">Welcome back, {{ session.user_name }}</div>
            <div class="small">Upload CSV data or view visualizations below.</div>
          </div>
          <div class="center">
            <div style="text-align:right">
              <div style="font-weight:800;font-size:20px">{{ total_records }}</div>
              <div class="small">records</div>
            </div>
            <div style="width:16px"></div>
            <div style="text-align:right">
              <div style="font-weight:800;font-size:20px">{{ unique_titles }}</div>
              <div class="small">unique titles</div>
            </div>
          </div>
        </div>

        <hr style="margin:14px 0">

        <form class="upload-area" method="post" action="{{ url_for('upload_csv') }}" enctype="multipart/form-data">
          <div style="display:flex;gap:12px;align-items:center">
            <input class="input" type="file" name="file" accept=".csv" />
            <button class="btn btn-accent" type="submit">Upload CSV</button>
            <div class="small">CSV must include <strong>BorrowDate</strong> and <strong>Count</strong> columns. Optional: Title, Department, Genre</div>
          </div>
        </form>

        <div style="margin-top:12px">
          <form method="get" action="{{ url_for('download_template') }}">
            <button class="btn" type="submit">Download sample CSV template</button>
          </form>
        </div>
      </div>

      <div class="card">
        <div class="card-title">Charts</div>
        <div class="small">Interactive charts update after each upload / change</div>

        <div style="margin-top:12px" class="controls">
          <button class="btn" onclick="refreshCharts()">Refresh</button>
        </div>

        <div style="margin-top:16px" class="row">
          <div style="flex:1;min-width:320px">
            <canvas id="barChart"></canvas>
          </div>
          <div style="flex:1;min-width:320px">
            <canvas id="pieChart"></canvas>
          </div>
        </div>

        <div style="margin-top:18px">
          <canvas id="lineChart"></canvas>
        </div>

      </div>
    </div>

    <div class="card">
      <div class="card-title">Dataset Table (recent 100)</div>
      <div class="small" id="table-note">Loading...</div>
      <div id="table-wrap" style="overflow:auto;margin-top:8px"></div>
    </div>

    <div class="footer">Built with Flask • Chart.js • MongoDB</div>

    <script>
    async function fetchData(){
      const res = await fetch("{{ url_for('api_data') }}");
      return await res.json();
    }

    let barChart, pieChart, lineChart;

    function makeChart(ctx, type, data, options){
      if (ctx && ctx._chart) {
        ctx._chart.destroy();
      }
      ctx._chart = new Chart(ctx, { type, data, options });
      return ctx._chart;
    }

    async function renderCharts(){
      const d = await fetchData();

      // Bar - Top Titles
      const barCtx = document.getElementById("barChart").getContext("2d");
      const barData = {
        labels: d.top_titles.labels,
        datasets: [{
          label: 'Borrow Count',
          data: d.top_titles.data,
          backgroundColor: d.top_titles.labels.map((_,i) => `hsl(${(i*50)%360} 80% 60%)`)
        }]
      };
      const barOptions = { responsive:true, plugins:{legend:{display:false}}, scales:{x:{ticks:{maxRotation:30}}} };
      makeChart(barCtx, 'bar', barData, barOptions);

      // Pie - department
      const pieCtx = document.getElementById("pieChart").getContext("2d");
      const pieData = {
        labels: d.dept.labels,
        datasets: [{ data: d.dept.data, backgroundColor: d.dept.labels.map((_,i)=>`hsl(${(i*70)%360} 70% 60%)`) }]
      };
      makeChart(pieCtx, 'pie', pieData, {responsive:true});

      // Line - monthly trend
      const lineCtx = document.getElementById("lineChart").getContext("2d");
      const lineData = {
        labels: d.month.labels,
        datasets: [{
          label: 'Monthly Borrow Count',
          data: d.month.data,
          fill: true,
          tension: 0.3,
          borderWidth: 2,
          pointRadius: 4
        }]
      };
      makeChart(lineCtx, 'line', lineData, {responsive:true, plugins:{legend:{display:false}}});

      // Table
      const tableWrap = document.getElementById('table-wrap');
      const rows = d.recent;
      if(rows.length === 0){
        document.getElementById('table-note').innerText = 'No rows in database. Upload a CSV to begin.';
        tableWrap.innerHTML = '';
      } else {
        document.getElementById('table-note').innerText = `Showing ${rows.length} recent rows`;
        let html = '<table style="width:100%;border-collapse:collapse"><thead><tr>';
        const cols = Object.keys(rows[0]);
        cols.forEach(c => html += `<th style="text-align:left;padding:8px;border-bottom:1px solid #eee">${c}</th>`);
        html += '</tr></thead><tbody>';
        rows.forEach(r => {
          html += '<tr>';
          cols.forEach(c => html += `<td style="padding:8px;border-bottom:1px solid #fafafa">${r[c] ?? ''}</td>`);
          html += '</tr>';
        });
        html += '</tbody></table>';
        tableWrap.innerHTML = html;
      }
    }

    function refreshCharts(){ renderCharts(); }

    // load on open
    renderCharts();
    </script>
    {% endblock %}
    """, session=session, total_records=total_records, unique_titles=unique_titles)

# -----------------------------
# CSV Template download (helpful)
# -----------------------------
@app.route("/download_template")
def download_template():
    sample = "Title,Department,Genre,Count,BorrowDate\nSample Book,Science,Fiction,5,2024-05-01\nAnother Book,Arts,Non-Fiction,2,2024-06-05\n"
    return (sample, 200, {
        'Content-Type': 'text/csv',
        'Content-Disposition': 'attachment; filename="sample_template.csv"'
    })

# -----------------------------
# CSV upload handler
# -----------------------------
@app.route("/upload_csv", methods=["POST"])
def upload_csv():
    if not ensure_logged_in():
        flash("Please log in to upload.")
        return redirect(url_for("login"))

    file = request.files.get("file")
    if not file or file.filename == "":
        flash("No file selected.")
        return redirect(url_for("dashboard"))
    if not allowed_file(file.filename):
        flash("Only CSV files allowed.")
        return redirect(url_for("dashboard"))

    try:
        # Read CSV into pandas from uploaded file
        # ensure text mode
        stream = TextIOWrapper(file.stream, encoding='utf-8')
        df = pd.read_csv(stream)
        required = {'BorrowDate', 'Count'}
        if not required.issubset(set(df.columns)):
            flash("CSV must contain at least 'BorrowDate' and 'Count' columns.")
            return redirect(url_for("dashboard"))

        # Normalize columns - convert BorrowDate
        df = df.copy()
        df['BorrowDate'] = pd.to_datetime(df['BorrowDate'], errors='coerce')
        if df['BorrowDate'].isna().all():
            flash("BorrowDate parsing failed. Use ISO dates like YYYY-MM-DD.")
            return redirect(url_for("dashboard"))

        # Fill missing optional columns with blank
        for col in ['Title', 'Department', 'Genre']:
            if col not in df.columns:
                df[col] = ''

        # Coerce Count to int (or numeric)
        df['Count'] = pd.to_numeric(df['Count'], errors='coerce').fillna(0).astype(int)

        # Build list of dicts to insert
        records = []
        for _, row in df.iterrows():
            rec = {
                "Title": str(row.get("Title")) if pd.notna(row.get("Title")) else "",
                "Department": str(row.get("Department")) if pd.notna(row.get("Department")) else "",
                "Genre": str(row.get("Genre")) if pd.notna(row.get("Genre")) else "",
                "Count": int(row.get("Count") or 0),
                "BorrowDate": row['BorrowDate'].to_pydatetime() if not pd.isna(row['BorrowDate']) else None,
                "uploaded_by": session.get('user_id'),
                "uploaded_at": datetime.utcnow()
            }
            # optionally skip rows without BorrowDate
            if rec["BorrowDate"] is None:
                continue
            records.append(rec)

        if records:
            borrows_col.insert_many(records)
            flash(f"Uploaded {len(records)} records successfully.")
        else:
            flash("No valid records to insert after parsing.")

        return redirect(url_for("dashboard"))
    except Exception as e:
        flash("Upload error: " + str(e))
        return redirect(url_for("dashboard"))

# -----------------------------
# API: data for charts
# -----------------------------
@app.route("/api/data")
def api_data():
    # Top Titles (top 5 by sum of Count)
    pipeline_titles = [
        {"$group": {"_id": "$Title", "total": {"$sum": "$Count"}}},
        {"$sort": {"total": -1}},
        {"$limit": 10}
    ]
    top = list(borrows_col.aggregate(pipeline_titles))
    top_labels = [t['_id'] or '(No title)' for t in top]
    top_data = [t['total'] for t in top]

    # Department distribution
    pipeline_dept = [
        {"$group": {"_id": "$Department", "total": {"$sum": "$Count"}}},
        {"$sort": {"total": -1}}
    ]
    depts = list(borrows_col.aggregate(pipeline_dept))
    dept_labels = [d['_id'] or 'Unknown' for d in depts]
    dept_data = [d['total'] for d in depts]

    # Monthly trend (YYYY-MM)
    pipeline_month = [
        {"$project": {"yearMonth": {"$dateToString": {"format": "%Y-%m", "date": "$BorrowDate"}}, "Count": 1}},
        {"$group": {"_id": "$yearMonth", "total": {"$sum": "$Count"}}},
        {"$sort": {"_id": 1}}
    ]
    months = list(borrows_col.aggregate(pipeline_month))
    month_labels = [m['_id'] for m in months]
    month_data = [m['total'] for m in months]

    # Recent rows (limit 100)
    recent_cursor = borrows_col.find({}, sort=[("uploaded_at", -1)]).limit(100)
    recent = []
    for r in recent_cursor:
        recent.append({
            "Title": r.get("Title", ""),
            "Department": r.get("Department", ""),
            "Genre": r.get("Genre", ""),
            "Count": r.get("Count", 0),
            "BorrowDate": r.get("BorrowDate").strftime("%Y-%m-%d") if r.get("BorrowDate") else ""
        })

    return jsonify({
        "top_titles": {"labels": top_labels, "data": top_data},
        "dept": {"labels": dept_labels, "data": dept_data},
        "month": {"labels": month_labels, "data": month_data},
        "recent": recent
    })

# -----------------------------
# Run the app
# -----------------------------
if __name__ == "__main__":
    app.run(debug=True, port=5000)
