"""Database models with multi-account isolation."""
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    accounts = db.relationship("Account", backref="user", lazy=True, cascade="all, delete-orphan")
    jobs = db.relationship("Job", backref="user", lazy=True, cascade="all, delete-orphan")
    posts = db.relationship("Post", backref="user", lazy=True, cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "account_count": len(self.accounts),
        }


class Account(db.Model):
    __tablename__ = "accounts"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)
    fb_page_access_token = db.Column(db.Text, nullable=False)
    fb_page_id = db.Column(db.String(50), nullable=False)
    fb_api_version = db.Column(db.String(10), default="v20.0")
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    jobs = db.relationship("Job", backref="account", lazy=True, cascade="all, delete-orphan")
    posts = db.relationship("Post", backref="account", lazy=True, cascade="all, delete-orphan")

    def to_dict(self, include_token=False):
        d = {
            "id": self.id,
            "user_id": self.user_id,
            "name": self.name,
            "fb_page_id": self.fb_page_id,
            "fb_api_version": self.fb_api_version,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "job_count": len(self.jobs),
        }
        if include_token:
            d["fb_page_access_token"] = self.fb_page_access_token[:10] + "..."
        return d


class Job(db.Model):
    __tablename__ = "jobs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    account_id = db.Column(db.Integer, db.ForeignKey("accounts.id"), nullable=False, index=True)
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(20), default="pending")
    interval_minutes = db.Column(db.Integer, default=60)
    total_posts = db.Column(db.Integer, default=0)
    completed_posts = db.Column(db.Integer, default=0)
    failed_posts = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    started_at = db.Column(db.DateTime, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)
    csv_deleted = db.Column(db.Boolean, default=False)
    csv_deleted_at = db.Column(db.DateTime, nullable=True)
    error_message = db.Column(db.Text, nullable=True)

    posts = db.relationship("Post", backref="job", lazy=True, cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "account_id": self.account_id,
            "account_name": self.account.name if self.account else None,
            "original_filename": self.original_filename,
            "status": self.status,
            "interval_minutes": self.interval_minutes,
            "total_posts": self.total_posts,
            "completed_posts": self.completed_posts,
            "failed_posts": self.failed_posts,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "csv_deleted": self.csv_deleted,
            "error_message": self.error_message,
        }


class Post(db.Model):
    __tablename__ = "posts"

    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey("jobs.id"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    account_id = db.Column(db.Integer, db.ForeignKey("accounts.id"), nullable=False, index=True)
    caption = db.Column(db.Text, nullable=False)
    media_url = db.Column(db.String(500), nullable=False)
    post_type = db.Column(db.String(10), default="image")
    comment = db.Column(db.Text, nullable=True)
    comment_posted = db.Column(db.Boolean, default=False)
    comment_error = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default="pending")
    scheduled_at = db.Column(db.DateTime, nullable=True)
    posted_at = db.Column(db.DateTime, nullable=True)
    fb_post_id = db.Column(db.String(100), nullable=True)
    error_message = db.Column(db.Text, nullable=True)
    retry_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "job_id": self.job_id,
            "account_id": self.account_id,
            "caption": self.caption[:120] + "..." if len(self.caption) > 120 else self.caption,
            "full_caption": self.caption,
            "media_url": self.media_url,
            "post_type": self.post_type,
            "comment": self.comment,
            "comment_posted": self.comment_posted,
            "comment_error": self.comment_error,
            "status": self.status,
            "scheduled_at": self.scheduled_at.isoformat() if self.scheduled_at else None,
            "posted_at": self.posted_at.isoformat() if self.posted_at else None,
            "fb_post_id": self.fb_post_id,
            "error_message": self.error_message,
            "retry_count": self.retry_count,
        }
