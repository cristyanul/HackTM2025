# public_resources_map/app.py
"""
Flask app with login:
• /login   – form
• /logout  – end session
• /admin/* – protected by @login_required
"""
from pathlib import Path
import os

from flask import (Flask, render_template, jsonify, request,
                   redirect, url_for, flash)
from flask_sqlalchemy import SQLAlchemy
from flask_login import (LoginManager, UserMixin, login_user,
                         logout_user, current_user, login_required)
from werkzeug.security import generate_password_hash, check_password_hash

# ── core config ────────────────────────────────────────────
BASE = Path(__file__).resolve().parent
DB   = BASE / "resources.db"

app = Flask(__name__, static_folder="static", template_folder="templates")
app.config.update(
    SQLALCHEMY_DATABASE_URI       = f"sqlite:///{DB}",
    SQLALCHEMY_TRACK_MODIFICATIONS= False,
    SECRET_KEY                    = os.getenv("SECRET_KEY","change-me")
)
db = SQLAlchemy(app)

# ── login manager ─────────────────────────────────────────
login_manager = LoginManager(app)
login_manager.login_view = "login"      # redirects here if not logged in

# ── ORM models ────────────────────────────────────────────
class User(UserMixin, db.Model):
    id       = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    pw_hash  = db.Column(db.String(256), nullable=False)

class Place(db.Model):
    id       = db.Column(db.Integer, primary_key=True)
    name     = db.Column(db.String,  nullable=False)
    lat      = db.Column(db.Float,   nullable=False)
    lon      = db.Column(db.Float,   nullable=False)
    type     = db.Column(db.String,  nullable=False)
    capacity = db.Column(db.Integer, default=0)

    def to_dict(self):
        return dict(id=self.id, name=self.name, lat=self.lat,
                    lon=self.lon, type=self.type, capacity=self.capacity)

with app.app_context(): db.create_all()

@login_manager.user_loader
def load_user(uid): return db.session.get(User, int(uid))

# ── PUBLIC ROUTES ─────────────────────────────────────────
@app.route("/")
def index(): return render_template("map.html")

@app.route("/api/resources")
def api_resources():
    rtype = request.args.get("type")
    q = Place.query.filter_by(type=rtype) if rtype else Place.query
    return jsonify([p.to_dict() for p in q.all()])

# ── AUTH ROUTES ───────────────────────────────────────────
@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        u = User.query.filter_by(username=request.form["username"]).first()
        if u and check_password_hash(u.pw_hash, request.form["password"]):
            login_user(u)
            flash("Logged in.", "success")
            return redirect(request.args.get("next") or url_for("admin_map"))
        flash("Invalid credentials.", "error")
    return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))

# ── ADMIN PAGES (HTML) ────────────────────────────────────
@app.route("/admin/")
@login_required
def admin_map(): return render_template("admin_map.html")

@app.route("/admin/list")
@login_required
def admin_list(): return render_template("admin_list.html")

# ── ADMIN JSON API (CRUD) ─────────────────────────────────
@app.route("/admin/api/places", methods=["GET","POST"])
@login_required
def admin_places():
    if request.method == "GET":
        offset = request.args.get("offset", type=int)
        limit  = request.args.get("limit",  type=int)
        q = Place.query.order_by(Place.id)
        if offset is not None: q=q.offset(offset)
        if limit  is not None: q=q.limit(limit)
        return jsonify([p.to_dict() for p in q.all()])

    data=request.get_json(silent=True) or {}
    try:
        p=Place(name=data["name"],lat=float(data["lat"]),
                lon=float(data["lon"]),type=data["type"],
                capacity=int(data.get("capacity",0)))
    except(Exception,): return {"error":"bad payload"},400
    db.session.add(p); db.session.commit()
    return jsonify(p.to_dict()),201

@app.route("/admin/api/places/<int:pid>", methods=["PUT","DELETE","GET"])
@login_required
def admin_place(pid):
    p=Place.query.get_or_404(pid)
    if request.method=="GET": return jsonify(p.to_dict())
    if request.method=="PUT":
        d=request.get_json(silent=True) or {}
        for f in ("name","type"): setattr(p,f,d.get(f,getattr(p,f)))
        if "lat" in d: p.lat=float(d["lat"])
        if "lon" in d: p.lon=float(d["lon"])
        if "capacity" in d: p.capacity=int(d["capacity"])
        db.session.commit(); return jsonify(p.to_dict())
    db.session.delete(p); db.session.commit(); return "",204

# ──────────────────────────────────────────────────────────
if __name__ == "__main__": app.run(debug=True)
