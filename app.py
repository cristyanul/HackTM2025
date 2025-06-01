"""
Flask app with:
• SQLite + SQLAlchemy
• User auth (Flask-Login)
• Public map  → /
• Admin map   → /admin/
• Admin list  → /admin/list
• CRUD JSON   → /admin/api/resources
• AI Chat     → /chat
• CSV import support for timis_public_resources.csv
"""
from pathlib import Path
import os, sqlite3, json

from flask import (Flask, render_template, jsonify, request,
                   redirect, url_for, flash)
from flask_sqlalchemy import SQLAlchemy
from flask_login import (LoginManager, UserMixin, login_user,
                         logout_user, current_user, login_required)
from werkzeug.security import generate_password_hash, check_password_hash

try:
    from openai import OpenAI
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False

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

# Initialize local LLM client
if HAS_OPENAI:
    client = OpenAI(
        base_url="http://192.168.1.146:1234/v1",
        api_key="not-needed"  # Local LLM doesn't require API key
    )
else:
    client = None

# ── models ────────────────────────────────────────────────
class User(UserMixin, db.Model):
    id       = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    pw_hash  = db.Column(db.String(256), nullable=False)

class Resource(db.Model):
    __tablename__ = "resource"
    id          = db.Column(db.Integer, primary_key=True)
    name        = db.Column(db.String, nullable=False)
    type        = db.Column(db.String, nullable=False)  # Space | Volunteer | Partner | Logistics | Grant | Event
    city        = db.Column(db.String)
    lat         = db.Column(db.Float)
    lon         = db.Column(db.Float)
    capacity    = db.Column(db.Integer)
    description = db.Column(db.Text)
    url         = db.Column(db.String)
    contact     = db.Column(db.String)
    category    = db.Column(db.String)

    def to_dict(self):
        return dict(
            id=self.id, name=self.name, type=self.type,
            lat=self.lat, lon=self.lon, category=self.category,
            city=self.city, url=self.url, capacity=self.capacity,
            description=self.description, contact=self.contact
        )

# ── one-time automatic column patch (SQLite) ─────────────
def _ensure_new_columns():
    table = Resource.__tablename__          # ← use the real table name ("resource")
    with sqlite3.connect(DB) as con:
        # Check if we need to migrate from old "place" table
        tables = {row[0] for row in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if "place" in tables and "resource" not in tables:
            # Rename place table to resource
            con.execute("ALTER TABLE place RENAME TO resource;")

        # Ensure new columns exist
        cols = {row[1] for row in con.execute(f"PRAGMA table_info({table})")}
        if "description" not in cols:
            con.execute(f"ALTER TABLE {table} ADD COLUMN description TEXT;")
        if "contact" not in cols:
            con.execute(f"ALTER TABLE {table} ADD COLUMN contact TEXT;")
        if "capacity" not in cols:
            con.execute(f"ALTER TABLE {table} ADD COLUMN capacity INTEGER;")
        if "city" not in cols:
            con.execute(f"ALTER TABLE {table} ADD COLUMN city TEXT;")
        if "url" not in cols:
            con.execute(f"ALTER TABLE {table} ADD COLUMN url TEXT;")
        if "category" not in cols:
            con.execute(f"ALTER TABLE {table} ADD COLUMN category TEXT;")

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
    category = request.args.get("category")  # Keep for backwards compatibility
    q = Resource.query
    if rtype:
        q = q.filter_by(type=rtype)
    if category:
        q = q.filter_by(category=category)
    return jsonify([p.to_dict() for p in q.all()])

@app.route("/api/categories")
def api_categories():
    """Get all distinct categories"""
    categories = db.session.query(Resource.category).filter(Resource.category.isnot(None)).distinct().all()
    return jsonify([cat[0] for cat in categories if cat[0]])

@app.route("/api/resource-types")
def api_resource_types():
    """Get all distinct resource types"""
    types = db.session.query(Resource.type).filter(Resource.type.isnot(None)).distinct().all()
    return jsonify([t[0] for t in types if t[0]])

@app.route("/api/all-resources")
def api_all_resources():
    """Get all resources for AI analysis - limited info to avoid token limits"""
    resources = Resource.query.all()
    return jsonify([{
        'id': r.id,
        'name': r.name,
        'type': r.type,
        'category': r.category,
        'city': r.city,
        'capacity': r.capacity,
        'description': r.description
    } for r in resources])

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
@app.route("/admin/api/resources", methods=["GET", "POST"])
@login_required
def admin_resources():
    if request.method == "GET":
        offset = request.args.get("offset", type=int)
        limit  = request.args.get("limit",  type=int)
        rtype = request.args.get("type")  # Changed from category to type
        category = request.args.get("category")  # Keep for backwards compatibility
        q = Resource.query.order_by(Resource.id)
        if rtype:
            q = q.filter_by(type=rtype)
        if category:
            q = q.filter_by(category=category)
        if offset is not None: q = q.offset(offset)
        if limit  is not None: q = q.limit(limit)
        return jsonify([p.to_dict() for p in q.all()])

    data = request.get_json(silent=True) or {}
    try:
        # Handle lat/lon properly - convert None to 0.0 for non-localized resources
        lat = data.get("lat")
        lon = data.get("lon")
        lat = float(lat) if lat is not None else 0.0
        lon = float(lon) if lon is not None else 0.0

        p = Resource(
            name=data["name"], type=data["type"],
            lat=lat, lon=lon,
            category=data.get("category"),
            city=data.get("city"), url=data.get("url"),
            capacity=data.get("capacity"),
            description=data.get("description"),
            contact=data.get("contact")
        )
    except (KeyError, ValueError):
        return {"error": "Bad payload"}, 400
    db.session.add(p); db.session.commit()
    return jsonify(p.to_dict()), 201

@app.route("/admin/api/resources/<int:pid>", methods=["GET", "PUT", "DELETE"])
@login_required
def admin_resource(pid):
    p = Resource.query.get_or_404(pid)
    if request.method == "GET":
        return jsonify(p.to_dict())
    if request.method == "PUT":
        d = request.get_json(silent=True) or {}
        for f in ("name", "type", "city", "url", "category", "description", "contact"):
            if f in d: setattr(p, f, d[f])
        # Handle lat/lon properly - convert None to 0.0 for non-localized resources
        if "lat" in d: p.lat = float(d["lat"]) if d["lat"] is not None else 0.0
        if "lon" in d: p.lon = float(d["lon"]) if d["lon"] is not None else 0.0
        if "capacity" in d: p.capacity = int(d["capacity"]) if d["capacity"] else None
        db.session.commit(); return jsonify(p.to_dict())
    db.session.delete(p); db.session.commit(); return "", 204

# ── AI Chat functionality ───────────────────────────────
@app.route("/chat")
def chat_page():
    return render_template("chat.html")

@app.route("/api/chat", methods=["POST"])
def chat_api():
    if not client:
        return jsonify({"error": "AI chat not available. Please install the openai package and ensure your local LLM server is running."}), 503

    data = request.get_json(silent=True) or {}
    user_msg = data.get("message", "")
    conversation_history = data.get("history", [])  # Get conversation history

    if not user_msg:
        return jsonify({"error": "No message provided"}), 400

    try:
        # Get database overview for better AI context
        total_resources = Resource.query.count()
        resource_summary = db.session.query(
            Resource.type,
            db.func.count(Resource.id).label('count')
        ).group_by(Resource.type).all()

        # Create resource summary for AI context
        resource_breakdown = {c: count for c, count in resource_summary}

        # Get all available resource types from database dynamically
        available_types = db.session.query(Resource.type).filter(Resource.type.isnot(None)).distinct().all()
        available_types = [t[0] for t in available_types if t[0]]

        # 1. Ask LLM to extract intent with conversation context
        sys_prompt = f"""You are an assistant that extracts structured needs from users planning events in Timiș county, Romania.

Database Overview: We have {total_resources} total resources with the following breakdown:
{json.dumps(resource_breakdown, indent=2)}

Available resource types in our database: {available_types}

Analyze the user's current request considering the conversation history and output ONLY valid JSON with these exact fields:
{{
  "city": "<city-name-or-null>",
  "capacity": <integer-or-null>,
  "buckets": ["list", "of", "relevant", "types"]
}}

Resource type descriptions:
- Space: venues, halls, conference rooms, outdoor spaces, cultural centers, libraries, co-working spaces
- Volunteer: NGOs, volunteer organizations, individual volunteers, student organizations
- Grant: funding opportunities, grants, financial support, funding agencies
- Event: existing events, conferences, networking opportunities, festivals
- Participatory Program: community programs, participatory budgets, civic engagement
- Project: infrastructure projects, development initiatives, community projects
- Partner: companies, institutions for collaboration
- Logistics: catering, equipment, transportation

IMPORTANT:
- Be generous with bucket inclusion - if something might be relevant, include it
- For general queries about "what's available", "help with event", "resources", include ALL types: {available_types}
- For specific needs (e.g., "need a venue"), include the specific type plus potentially relevant others
- When in doubt, include more rather than fewer buckets
- The user can always see all available data

Return ONLY the JSON object, no additional text or explanation."""

        # Build messages with conversation history
        messages = [{"role": "system", "content": sys_prompt}]

        # Add conversation history
        for msg in conversation_history:
            if msg.get("role") in ["user", "assistant"]:
                messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })

        # Add current user message
        messages.append({"role": "user", "content": user_msg})

        analysis_response = client.chat.completions.create(
            model="qwen/qwen3-14b",
            messages=messages,
            temperature=0.1
        )

        # Parse the analysis response
        try:
            response_content = analysis_response.choices[0].message.content.strip()
            # Try to extract JSON if the response contains extra text
            if not response_content.startswith('{'):
                # Look for JSON in the response
                import re
                json_match = re.search(r'\{.*\}', response_content, re.DOTALL)
                if json_match:
                    response_content = json_match.group()
                else:
                    raise ValueError("No JSON found in response")

            analysis = json.loads(response_content)
        except (json.JSONDecodeError, ValueError) as e:
            # Fallback: create a default analysis that includes ALL available types
            print(f"Analysis parsing failed: {e}, using fallback with all types")
            analysis = {
                "city": None,
                "capacity": None,
                "buckets": available_types  # Use all available types as fallback
            }

        # 2. Run SQL filters per bucket with better filtering logic
        results = {}
        total_found = 0

        for bucket in analysis.get("buckets", []):
            q = Resource.query.filter_by(type=bucket)

            # Apply city filter if specified
            if analysis.get("city"):
                city_name = analysis["city"].lower()
                q = q.filter(Resource.city.ilike(f"%{city_name}%"))

            # Apply capacity filter only for spaces
            if analysis.get("capacity") and bucket == "Space":
                q = q.filter(Resource.capacity >= analysis["capacity"])

            # Order by relevance and limit results
            q = q.order_by(Resource.name)
            resources = q.limit(15).all()  # Increase limit to show more options
            results[bucket] = [r.to_dict() for r in resources]
            total_found += len(resources)

        # Fallback: if no buckets were selected or very few results found, show all types
        if not analysis.get("buckets") or total_found < 3:
            print(f"Fallback triggered: buckets={analysis.get('buckets')}, total_found={total_found}")
            analysis["buckets"] = available_types
            results = {}
            for bucket in available_types:
                q = Resource.query.filter_by(type=bucket)

                # Apply city filter if specified
                if analysis.get("city"):
                    city_name = analysis["city"].lower()
                    q = q.filter(Resource.city.ilike(f"%{city_name}%"))

                # Apply capacity filter only for spaces
                if analysis.get("capacity") and bucket == "Space":
                    q = q.filter(Resource.capacity >= analysis["capacity"])

                q = q.order_by(Resource.name)
                resources = q.limit(15).all()
                if resources:  # Only include buckets that have results
                    results[bucket] = [r.to_dict() for r in resources]

        # Final safety net: if still no results, get everything
        if not results or sum(len(res) for res in results.values()) == 0:
            print("Final safety net: getting all resources")
            all_resources = Resource.query.order_by(Resource.name).limit(50).all()
            # Group by type
            results = {}
            for resource in all_resources:
                rtype = resource.type or "Other"
                if rtype not in results:
                    results[rtype] = []
                results[rtype].append(resource.to_dict())
            analysis["buckets"] = list(results.keys())

        # 3. Let LLM draft friendly answer with conversation context
        answer_prompt = f"""Conversation history: {json.dumps(conversation_history, indent=2)}

Current user request: {user_msg}

Available resources found:
{json.dumps(results, indent=2)}

Compose a helpful, friendly reply that:
1. Acknowledges the conversation history and any previous context
2. Responds specifically to the user's current request
3. Presents the relevant resources in a clear, organized way
4. Includes specific details like names, locations, contacts when available
5. References previous conversation if relevant
6. Suggests next steps or follow-up questions
7. Uses a conversational, helpful tone

If no resources are found for a category, mention that and suggest they could add resources via the admin panel."""

        # Build messages for reply generation with full conversation context
        reply_messages = [
            {"role": "system", "content": "You are a helpful civic assistant for Timiș county, Romania. Help users plan events and find resources. Remember the conversation history and provide contextual responses."}
        ]

        # Add conversation history for context
        for msg in conversation_history:
            if msg.get("role") in ["user", "assistant"]:
                reply_messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })

        # Add the current context
        reply_messages.append({"role": "user", "content": answer_prompt})

        reply_response = client.chat.completions.create(
            model="qwen/qwen3-14b",
            messages=reply_messages,
            temperature=0.3
        )

        reply = reply_response.choices[0].message.content

        return jsonify({
            "reply": reply,
            "analysis": analysis,
            "resources": results
        })

    except Exception as e:
        return jsonify({"error": f"AI processing failed: {str(e)}"}), 500

# ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    app.run(debug=True)
