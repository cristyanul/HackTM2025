# public_resources_map/app.py
"""
Flask app with:
• SQLite + SQLAlchemy
• User auth (Flask-Login)
• Public map  → /
• Admin map   → /admin/
• Admin list  → /admin/list
• CRUD JSON   → /admin/api/places
• CSV import support for timis_public_resources.csv
"""
from pathlib import Path
import os, sqlite3

from flask import (Flask, render_template, jsonify, request,
                   redirect, url_for, flash)
from flask_sqlalchemy import SQLAlchemy
from flask_login import (LoginManager, UserMixin, login_user,
                         logout_user, current_user, login_required)
from werkzeug.security import generate_password_hash, check_password_hash

# ── configuration ─────────────────────────────────────────
BASE = Path(__file__).resolve().parent
DB   = BASE / "resources.db"

app = Flask(__name__, static_folder="static", template_folder="templates")
app.config.update(
    SQLALCHEMY_DATABASE_URI       = f"sqlite:///{DB}",
    SQLALCHEMY_TRACK_MODIFICATIONS= False,
    SECRET_KEY                    = os.getenv("SECRET_KEY", "change-me")
)
db = SQLAlchemy(app)

login_manager = LoginManager(app)
login_manager.login_view = "login"

# ── models ────────────────────────────────────────────────
class User(UserMixin, db.Model):
    id       = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    pw_hash  = db.Column(db.String(256), nullable=False)

class Place(db.Model):
    id       = db.Column(db.Integer, primary_key=True)
    name     = db.Column(db.String,  nullable=False)
    lat      = db.Column(db.Float,   nullable=False)
    lon      = db.Column(db.Float,   nullable=False)
    type     = db.Column(db.String,  nullable=False)  # Space / Event / …
    category = db.Column(db.String)                   # NEW: replaces capacity
    city     = db.Column(db.String)                   # NEW
    url      = db.Column(db.String)                   # NEW

    def to_dict(self):
        return dict(
            id=self.id, name=self.name, type=self.type,
            lat=self.lat, lon=self.lon, category=self.category,
            city=self.city, url=self.url
        )

# ── one-time automatic column patch (SQLite) ─────────────
def _ensure_new_columns():
    table = Place.__tablename__          # ← use the real table name ("place")
    with sqlite3.connect(DB) as con:
        cols = {row[1] for row in con.execute(f"PRAGMA table_info({table})")}
        if "city" not in cols:
            con.execute(f"ALTER TABLE {table} ADD COLUMN city TEXT;")
        if "url" not in cols:
            con.execute(f"ALTER TABLE {table} ADD COLUMN url TEXT;")
        if "category" not in cols:
            con.execute(f"ALTER TABLE {table} ADD COLUMN category TEXT;")
        # Remove capacity column if it exists (SQLite doesn't support DROP COLUMN in older versions)
        # We'll handle this by just ignoring the old capacity column

with app.app_context():
    db.create_all()
    _ensure_new_columns()

@login_manager.user_loader
def load_user(uid): return db.session.get(User, int(uid))

# ── public endpoints ─────────────────────────────────────
@app.route("/")
def index(): return render_template("map.html")

@app.route("/api/resources")
def api_resources():
    rtype = request.args.get("type")
    q = Place.query.filter_by(type=rtype) if rtype else Place.query
    return jsonify([p.to_dict() for p in q.all()])

# ── auth ─────────────────────────────────────────────────
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        u = User.query.filter_by(username=request.form["username"]).first()
        if u and check_password_hash(u.pw_hash, request.form["password"]):
            login_user(u)
            return redirect(request.args.get("next") or url_for("admin_map"))
        flash("Invalid credentials", "error")
    return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    logout_user(); return redirect(url_for("login"))

# ── admin pages ──────────────────────────────────────────
@app.route("/admin/")
@login_required
def admin_map(): return render_template("admin_map.html")

@app.route("/admin/list")
@login_required
def admin_list(): return render_template("admin_list.html")

# ── CRUD API ─────────────────────────────────────────────
@app.route("/admin/api/places", methods=["GET", "POST"])
@login_required
def admin_places():
    if request.method == "GET":
        offset = request.args.get("offset", type=int)
        limit  = request.args.get("limit",  type=int)
        q = Place.query.order_by(Place.id)
        if offset is not None: q = q.offset(offset)
        if limit  is not None: q = q.limit(limit)
        return jsonify([p.to_dict() for p in q.all()])

    data = request.get_json(silent=True) or {}
    try:
        p = Place(
            name=data["name"], type=data["type"],
            lat=float(data["lat"]), lon=float(data["lon"]),
            category=data.get("category"),
            city=data.get("city"), url=data.get("url")
        )
    except (KeyError, ValueError):
        return {"error": "Bad payload"}, 400
    db.session.add(p); db.session.commit()
    return jsonify(p.to_dict()), 201

@app.route("/admin/api/places/<int:pid>", methods=["GET", "PUT", "DELETE"])
@login_required
def admin_place(pid):
    p = Place.query.get_or_404(pid)
    if request.method == "GET":
        return jsonify(p.to_dict())
    if request.method == "PUT":
        d = request.get_json(silent=True) or {}
        for f in ("name", "type", "city", "url", "category"):
            if f in d: setattr(p, f, d[f])
        if "lat" in d: p.lat = float(d["lat"])
        if "lon" in d: p.lon = float(d["lon"])
        db.session.commit(); return jsonify(p.to_dict())
    db.session.delete(p); db.session.commit(); return "", 204

# ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    app.run(debug=True)
