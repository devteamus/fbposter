#!/usr/bin/env python3
"""FB Auto-Poster API — Single-container: serves API + static frontend."""
import os
import re
import threading
import logging
from datetime import datetime
from urllib.parse import urlparse

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from flask_jwt_extended import JWTManager, jwt_required, get_jwt_identity
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.utils import secure_filename
import pandas as pd

from config import Config
from models import db, User, Account, Job, Post
from auth import hash_password, verify_password, create_user_token
from worker import PostingWorker

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("fb_app")

app = Flask(__name__, static_folder=None)
app.config.from_object(Config)

# CORS. A wildcard origin ("*") combined with credentialed requests is a
# real security hole — browsers are supposed to reject it, but we don't
# rely on that: explicitly disable credentials whenever the origin list is
# a wildcard, and only allow credentials for an explicit origin list (e.g.
# CORS_ORIGINS=https://fb.postgo.fun).
_cors_origins = app.config.get("CORS_ORIGINS", ["*"])
_cors_wildcard = _cors_origins in (["*"], "*")
CORS(app, origins=_cors_origins, supports_credentials=not _cors_wildcard)

# JWT
jwt = JWTManager(app)

# Rate limiting — protects /api/auth/* from brute-force / credential
# stuffing via automated requests (not stoppable from the browser UI, but
# this stops someone hammering the API directly, e.g. via devtools/curl).
limiter = Limiter(get_remote_address, app=app, storage_uri="memory://", default_limits=["300 per minute"])


@app.after_request
def set_security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    # Only meaningful once served over HTTPS (e.g. behind Cloudflare) — harmless over plain HTTP locally.
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


# Ensure upload dir
try:
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    logger.info("Upload folder ready: %s", app.config["UPLOAD_FOLDER"])
except Exception as e:
    logger.error("FATAL: cannot create upload folder: %s", e)
    raise

# Init DB
db.init_app(app)
try:
    with app.app_context():
        db.create_all()
    logger.info("Database ready: %s", app.config.get("SQLALCHEMY_DATABASE_URI"))
except Exception as e:
    logger.error("FATAL: cannot init database: %s", e)
    raise

# Log startup env
logger.info("=" * 60)
logger.info("ENVIRONMENT: PORT=%s", os.environ.get("PORT"))
logger.info("DATABASE_URL env: %r", os.environ.get("DATABASE_URL"))
logger.info("Resolved SQLALCHEMY_DATABASE_URI: %s", app.config.get("SQLALCHEMY_DATABASE_URI"))
logger.info("Resolved UPLOAD_FOLDER: %s", app.config.get("UPLOAD_FOLDER"))
logger.info("Resolved STATIC_FOLDER: %s", app.config.get("STATIC_FOLDER"))
logger.info("=" * 60)

# Background worker
worker = PostingWorker(app)


# ═══════════════════════════════════════════════════════════════════════════════
# Auth Routes
# ═══════════════════════════════════════════════════════════════════════════════

@app.route("/api/auth/register", methods=["POST"])
@limiter.limit("5 per hour")
def register():
    data = request.get_json() or {}
    username = data.get("username", "").strip().lower()
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    if not username or not email or not password:
        return jsonify({"error": "Username, email and password required"}), 400
    if len(password) < 8:
        return jsonify({"error": "Password must be at least 8 characters"}), 400
    if not re.match(r"^[a-z0-9_.-]{3,30}$", username):
        return jsonify({"error": "Username must be 3-30 chars: letters, numbers, . _ -"}), 400

    if User.query.filter((User.username == username) | (User.email == email)).first():
        return jsonify({"error": "Username or email already exists"}), 409

    user = User(
        username=username,
        email=email,
        password_hash=hash_password(password),
    )
    db.session.add(user)
    db.session.commit()
    token = create_user_token(user)
    return jsonify({"success": True, "token": token, "user": user.to_dict()})


@app.route("/api/auth/login", methods=["POST"])
@limiter.limit("10 per minute")
def login():
    data = request.get_json() or {}
    username = data.get("username", "").strip().lower()
    password = data.get("password", "")

    user = User.query.filter_by(username=username).first()
    if not user or not verify_password(password, user.password_hash):
        return jsonify({"error": "Invalid username or password"}), 401

    token = create_user_token(user)
    return jsonify({"success": True, "token": token, "user": user.to_dict()})


@app.route("/api/auth/me", methods=["GET"])
@jwt_required()
def me():
    user_id = int(get_jwt_identity())
    user = User.query.get_or_404(user_id)
    return jsonify(user.to_dict())


# ═══════════════════════════════════════════════════════════════════════════════
# Account Routes
# ═══════════════════════════════════════════════════════════════════════════════

@app.route("/api/accounts", methods=["GET"])
@jwt_required()
def list_accounts():
    user_id = int(get_jwt_identity())
    accounts = Account.query.filter_by(user_id=user_id).order_by(Account.created_at.desc()).all()
    return jsonify([a.to_dict() for a in accounts])


@app.route("/api/accounts", methods=["POST"])
@jwt_required()
def create_account():
    user_id = int(get_jwt_identity())
    data = request.get_json() or {}

    count = Account.query.filter_by(user_id=user_id).count()
    if count >= 100:
        return jsonify({"error": "Maximum 100 accounts reached"}), 400

    name = data.get("name", "").strip()
    token = data.get("fb_page_access_token", "").strip()
    page_id = data.get("fb_page_id", "").strip()
    api_ver = data.get("fb_api_version", "v20.0").strip()

    if not name or not token or not page_id:
        return jsonify({"error": "name, fb_page_access_token, fb_page_id required"}), 400
    if len(name) > 100 or len(page_id) > 50 or len(api_ver) > 10 or len(token) > 500:
        return jsonify({"error": "One or more fields exceed the maximum length"}), 400

    acc = Account(
        user_id=user_id,
        name=name,
        fb_page_access_token=token,
        fb_page_id=page_id,
        fb_api_version=api_ver,
    )
    db.session.add(acc)
    db.session.commit()
    return jsonify({"success": True, "account": acc.to_dict()})


@app.route("/api/accounts/<int:account_id>", methods=["GET"])
@jwt_required()
def get_account(account_id):
    user_id = int(get_jwt_identity())
    acc = Account.query.filter_by(id=account_id, user_id=user_id).first_or_404()
    return jsonify(acc.to_dict(include_token=True))


@app.route("/api/accounts/<int:account_id>", methods=["PUT"])
@jwt_required()
def update_account(account_id):
    user_id = int(get_jwt_identity())
    acc = Account.query.filter_by(id=account_id, user_id=user_id).first_or_404()
    data = request.get_json() or {}

    if "name" in data:
        acc.name = data["name"].strip()
    if "fb_page_access_token" in data:
        acc.fb_page_access_token = data["fb_page_access_token"].strip()
    if "fb_page_id" in data:
        acc.fb_page_id = data["fb_page_id"].strip()
    if "fb_api_version" in data:
        acc.fb_api_version = data["fb_api_version"].strip()
    if "is_active" in data:
        acc.is_active = bool(data["is_active"])

    db.session.commit()
    return jsonify({"success": True, "account": acc.to_dict()})


@app.route("/api/accounts/<int:account_id>", methods=["DELETE"])
@jwt_required()
def delete_account(account_id):
    user_id = int(get_jwt_identity())
    acc = Account.query.filter_by(id=account_id, user_id=user_id).first_or_404()
    db.session.delete(acc)
    db.session.commit()
    return jsonify({"success": True})


@app.route("/api/accounts/<int:account_id>/validate", methods=["POST"])
@jwt_required()
def validate_account(account_id):
    user_id = int(get_jwt_identity())
    acc = Account.query.filter_by(id=account_id, user_id=user_id).first_or_404()

    from worker import FacebookPoster, FacebookAPIError
    try:
        poster = FacebookPoster(acc.fb_page_access_token, acc.fb_page_id, acc.fb_api_version)
        info = poster.validate()
        return jsonify({"success": True, "page": info})
    except FacebookAPIError as e:
        # Safe to show — this is Facebook's own error message (e.g. bad
        # token), not an internal exception.
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        logger.exception("Account validation failed for account %s: %s", account_id, e)
        return jsonify({"success": False, "error": "Could not validate this account right now."}), 400


# ═══════════════════════════════════════════════════════════════════════════════
# Job Routes
# ═══════════════════════════════════════════════════════════════════════════════

@app.route("/api/jobs", methods=["GET"])
@jwt_required()
def list_jobs():
    user_id = int(get_jwt_identity())
    account_id = request.args.get("account_id", type=int)

    q = Job.query.filter_by(user_id=user_id)
    if account_id:
        q = q.filter_by(account_id=account_id)
    jobs = q.order_by(Job.created_at.desc()).all()
    return jsonify([j.to_dict() for j in jobs])


@app.route("/api/jobs/<int:job_id>", methods=["GET"])
@jwt_required()
def get_job(job_id):
    user_id = int(get_jwt_identity())
    job = Job.query.filter_by(id=job_id, user_id=user_id).first_or_404()
    return jsonify(job.to_dict())


@app.route("/api/jobs/<int:job_id>/posts", methods=["GET"])
@jwt_required()
def get_job_posts(job_id):
    user_id = int(get_jwt_identity())
    job = Job.query.filter_by(id=job_id, user_id=user_id).first_or_404()
    posts = Post.query.filter_by(job_id=job.id).order_by(Post.id.asc()).all()
    return jsonify([p.to_dict() for p in posts])


@app.route("/api/jobs/<int:job_id>/pause", methods=["POST"])
@jwt_required()
def pause_job(job_id):
    user_id = int(get_jwt_identity())
    job = Job.query.filter_by(id=job_id, user_id=user_id).first_or_404()
    if job.status == "running":
        job.status = "paused"
        db.session.commit()
    return jsonify(job.to_dict())


@app.route("/api/jobs/<int:job_id>/resume", methods=["POST"])
@jwt_required()
def resume_job(job_id):
    user_id = int(get_jwt_identity())
    job = Job.query.filter_by(id=job_id, user_id=user_id).first_or_404()
    if job.status == "paused":
        job.status = "running"
        db.session.commit()
    return jsonify(job.to_dict())


@app.route("/api/jobs/<int:job_id>", methods=["DELETE"])
@jwt_required()
def delete_job(job_id):
    user_id = int(get_jwt_identity())
    job = Job.query.filter_by(id=job_id, user_id=user_id).first_or_404()
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], job.filename)
    if os.path.exists(filepath):
        try:
            os.remove(filepath)
        except OSError:
            pass
    db.session.delete(job)
    db.session.commit()
    return jsonify({"success": True})


@app.route("/api/upload", methods=["POST"])
@jwt_required()
@limiter.limit("20 per hour")
def upload_csv():
    user_id = int(get_jwt_identity())

    if "csv" not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files["csv"]
    if file.filename == "" or not file.filename.lower().endswith(".csv"):
        return jsonify({"error": "Only .csv files allowed"}), 400

    account_id = request.form.get("account_id", type=int)
    if not account_id:
        return jsonify({"error": "account_id required"}), 400

    acc = Account.query.filter_by(id=account_id, user_id=user_id).first()
    if not acc:
        return jsonify({"error": "Account not found"}), 404

    try:
        interval_value = int(request.form.get("interval_value", 1))
    except ValueError:
        return jsonify({"error": "Invalid interval value"}), 400
    if interval_value < 1:
        return jsonify({"error": "Interval must be at least 1"}), 400

    interval_unit = request.form.get("interval_unit", "hours")
    if interval_unit == "minutes":
        interval_minutes = interval_value
    elif interval_unit == "hours":
        interval_minutes = interval_value * 60
    elif interval_unit == "days":
        interval_minutes = interval_value * 60 * 24
    else:
        interval_minutes = 60

    filepath = None
    try:
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        safe_name = secure_filename(file.filename)
        if not safe_name.lower().endswith(".csv"):
            # secure_filename can strip everything if the name was all
            # unsafe characters — refuse rather than silently renaming.
            return jsonify({"error": "Invalid file name"}), 400
        filename = f"{ts}_{safe_name}"
        filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        file.save(filepath)

        # Content sniff: reject anything that isn't plain text before we
        # ever hand it to pandas. A renamed executable/binary will contain
        # null bytes or invalid UTF-8/Latin-1 sequences; real CSVs won't.
        with open(filepath, "rb") as fh:
            head = fh.read(8192)
        if b"\x00" in head:
            os.remove(filepath)
            return jsonify({"error": "File does not look like a valid CSV"}), 400
        try:
            head.decode("utf-8")
        except UnicodeDecodeError:
            try:
                head.decode("latin-1")
            except UnicodeDecodeError:
                os.remove(filepath)
                return jsonify({"error": "File does not look like a valid CSV"}), 400

        df = pd.read_csv(filepath, dtype=str).fillna("")
        required = ["caption"]
        missing = [c for c in required if c not in df.columns]
        if missing:
            os.remove(filepath)
            return jsonify({"error": f"Missing columns: {', '.join(missing)}"}), 400

        max_rows = app.config.get("MAX_CSV_ROWS", 5000)
        if len(df) == 0:
            os.remove(filepath)
            return jsonify({"error": "CSV has no rows"}), 400
        if len(df) > max_rows:
            os.remove(filepath)
            return jsonify({"error": f"CSV has {len(df)} rows — max allowed is {max_rows}"}), 400

        VALID_TYPES = ("text", "image", "video", "reel")

        # Validate every row before importing anything, so a bad CSV never
        # creates a half-imported job. media_url is only required for
        # image/video/reel rows — text posts don't need one. Where a
        # media_url IS required, only http/https URLs are accepted — this
        # is what gets sent server-side to the Facebook Graph API, so
        # anything else (file://, javascript:, internal IPs via unusual
        # schemes, etc.) must never reach that call.
        bad_rows = []
        for idx, row in df.iterrows():
            ptype = str(row.get("post_type", "image")).lower().strip() or "image"
            if ptype not in VALID_TYPES:
                ptype = "image"
            url = str(row.get("media_url", "")).strip()
            if ptype != "text":
                parsed = urlparse(url)
                if parsed.scheme not in ("http", "https") or not parsed.netloc:
                    bad_rows.append(idx + 2)  # +2: header row + 1-indexed
            if len(url) > 2000 or len(str(row.get("caption", ""))) > 5000:
                bad_rows.append(idx + 2)
            if len(str(row.get("comment", ""))) > 2000:
                bad_rows.append(idx + 2)
            if len(bad_rows) >= 10:
                break
        if bad_rows:
            os.remove(filepath)
            preview = ", ".join(str(r) for r in bad_rows[:10])
            return jsonify({
                "error": f"Invalid row(s): {preview}{' ...' if len(bad_rows) >= 10 else ''}. "
                         f"media_url is required (full http(s) link) for image/video/reel rows, "
                         f"caption max 5000 chars, comment max 2000 chars."
            }), 400

        job = Job(
            user_id=user_id,
            account_id=account_id,
            filename=filename,
            original_filename=safe_name,
            interval_minutes=interval_minutes,
            total_posts=len(df),
            status="pending",
        )
        db.session.add(job)
        db.session.flush()

        for _, row in df.iterrows():
            ptype = str(row.get("post_type", "image")).lower().strip() or "image"
            if ptype not in VALID_TYPES:
                ptype = "image"
            # Strip control/null characters defensively before storing —
            # belt-and-braces on top of the validation above.
            caption = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", str(row.get("caption", "")))
            media_url = re.sub(r"[\x00-\x1f]", "", str(row.get("media_url", "")))
            raw_comment = str(row.get("comment", "")).strip()
            comment = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", raw_comment) if raw_comment else None
            post = Post(
                job_id=job.id,
                user_id=user_id,
                account_id=account_id,
                caption=caption,
                media_url=media_url,
                post_type=ptype,
                comment=comment,
                status="pending",
            )
            db.session.add(post)

        job.status = "running"
        job.started_at = datetime.utcnow()
        db.session.commit()

        return jsonify({"success": True, "job": job.to_dict()})

    except Exception as e:
        logger.exception("CSV upload failed for user %s: %s", user_id, e)
        if filepath and os.path.exists(filepath):
            try:
                os.remove(filepath)
            except OSError:
                pass
        return jsonify({"error": "Could not process this CSV. Please check the format and try again."}), 500


# ═══════════════════════════════════════════════════════════════════════════════
# Stats & Health
# ═══════════════════════════════════════════════════════════════════════════════

@app.route("/api/stats", methods=["GET"])
@jwt_required()
def get_stats():
    user_id = int(get_jwt_identity())
    total_jobs = Job.query.filter_by(user_id=user_id).count()
    total_posts = Post.query.filter_by(user_id=user_id).count()
    posted = Post.query.filter_by(user_id=user_id, status="posted").count()
    pending = Post.query.filter_by(user_id=user_id).filter(Post.status.in_(["pending","scheduled","posting"])).count()
    failed = Post.query.filter_by(user_id=user_id, status="failed").count()
    account_count = Account.query.filter_by(user_id=user_id).count()

    return jsonify({
        "total_jobs": total_jobs,
        "total_posts": total_posts,
        "posted": posted,
        "pending": pending,
        "failed": failed,
        "account_count": account_count,
    })


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "worker": "running" if worker.running else "stopped"})


# ═══════════════════════════════════════════════════════════════════════════════
# Static Frontend — serves Next.js static export (output: "export")
#
# Two things had to be right here, both learned the hard way:
#
# 1) static_folder=None above is intentional. Flask's built-in static
#    endpoint uses the same URL rule pattern ("/<path:filename>") as the
#    catch-all below, and it wins the routing conflict without knowing
#    about our fallback logic — causing a raw 404 on any hard-reload of
#    a nested route like /dashboard/jobs.
#
# 2) Next static export pre-renders a SEPARATE html file per route, each
#    with that route's own embedded page data (e.g. dashboard/jobs.html,
#    dashboard.html, index.html). This is NOT a single-page app with one
#    shared index.html — so blindly falling back to index.html for every
#    unmatched path (the usual SPA trick) serves the WRONG page's html.
#    The browser URL says /dashboard/jobs but the hydrated tree is the
#    login page, which looks exactly like "getting logged out on reload".
#    We must resolve <path>.html (and <path>/index.html) BEFORE ever
#    falling back to index.html, and only fall back to index.html for
#    truly unknown paths in dev — production should have a real 404.html.
# ═══════════════════════════════════════════════════════════════════════════════

@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_frontend(path):
    # If request is for API but no route matched, return 404 JSON
    if path.startswith("api/"):
        return jsonify({"error": "Not found"}), 404

    static_dir = app.config.get("STATIC_FOLDER")
    if not static_dir or not os.path.isdir(static_dir):
        # Static folder not built — show backend-only message
        return jsonify({
            "name": "FB Auto-Poster API",
            "status": "frontend not built",
            "endpoints": ["/api/health", "/api/auth/login", "/api/auth/register"],
        }), 200

    clean_path = path.strip("/")

    # Candidate files to try, in priority order, for this exact route.
    if clean_path:
        candidates = [
            clean_path,                          # exact static asset, e.g. _next/static/...
            f"{clean_path}.html",                # e.g. dashboard/jobs -> dashboard/jobs.html
            f"{clean_path}/index.html",           # fallback shape some exports use
        ]
    else:
        candidates = ["index.html"]

    for rel in candidates:
        full_path = os.path.join(static_dir, rel)
        # Guard against path traversal / escaping static_dir
        if os.path.commonpath([os.path.abspath(full_path), os.path.abspath(static_dir)]) != os.path.abspath(static_dir):
            continue
        if os.path.isfile(full_path):
            return send_from_directory(static_dir, rel)

    # Truly unknown path — serve Next's generated 404 page if present,
    # else fall back to index.html so client-side nav still works.
    not_found_path = os.path.join(static_dir, "404.html")
    if os.path.isfile(not_found_path):
        return send_from_directory(static_dir, "404.html"), 404

    index_path = os.path.join(static_dir, "index.html")
    if os.path.isfile(index_path):
        return send_from_directory(static_dir, "index.html")

    return jsonify({"error": "Frontend build missing"}), 404


# ═══════════════════════════════════════════════════════════════════════════════
# Startup
# ═══════════════════════════════════════════════════════════════════════════════

def start_worker():
    def _run():
        try:
            worker.start()
        except Exception as e:
            logger.exception("Worker thread crashed: %s", e)

    t = threading.Thread(target=_run, daemon=True, name="FBWorker")
    t.start()
    logger.info("Background worker thread started.")


if __name__ == "__main__":
    start_worker()
    port = int(os.environ.get("PORT", 5000))
    host = os.environ.get("HOST", "0.0.0.0")
    logger.info("Starting Flask on %s:%s (PID=%d)", host, port, os.getpid())
    try:
        app.run(host=host, port=port, debug=False, threaded=True, use_reloader=False)
    except OSError as e:
        logger.error("FATAL: cannot bind to %s:%s — %s", host, port, e)
        raise
    except Exception as e:
        logger.error("FATAL: Flask crashed: %s", e)
        raise
