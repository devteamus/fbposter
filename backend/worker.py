"""Background worker with multi-account isolation."""
import os
import time
import logging
import requests
from datetime import datetime, timedelta
from sqlalchemy import inspect, text
from models import db, Account, Job, Post

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger("fb_worker")


class FacebookAPIError(Exception):
    pass


class FacebookPoster:
    """Low-level Facebook Graph API poster per account."""

    def __init__(self, access_token: str, page_id: str, api_version: str = "v20.0"):
        self.access_token = access_token
        self.page_id = page_id
        self.base_url = f"https://graph.facebook.com/{api_version}"
        self.session = requests.Session()

    def _request(self, method: str, endpoint: str, data: dict = None, params: dict = None, timeout: int = None):
        url = f"{self.base_url}/{endpoint}"
        req_params = {"access_token": self.access_token}
        if params:
            req_params.update(params)
        try:
            if method.upper() == "GET":
                resp = self.session.get(url, params=req_params, timeout=timeout or 30)
            else:
                resp = self.session.post(url, data=data, params=req_params, timeout=timeout or 120)
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.HTTPError as e:
            try:
                err = e.response.json() if e.response.text else {}
            except ValueError:
                err = {}
            code = err.get("error", {}).get("code", "unknown")
            msg = err.get("error", {}).get("message", str(e))
            raise FacebookAPIError(f"Graph API {code}: {msg}")
        except requests.exceptions.RequestException as e:
            raise FacebookAPIError(f"Network error: {e}")

    def post_image(self, caption: str, image_url: str):
        """Reliably publish a photo to the Page's Timeline.

        Posting straight to /{page}/photos with published=true adds the
        photo to an album and *usually* also creates a Timeline story —
        but this isn't guaranteed, and the photo can end up sitting only
        in the Photos tab, invisible on the Timeline to anyone but the
        Page admin. The reliable approach (Meta's documented pattern) is
        two steps: upload the photo *unpublished* (so it's not shown
        anywhere yet), then create an actual Timeline post via /feed that
        attaches that photo — this always generates a proper feed story.
        """
        uploaded = self._request("POST", f"{self.page_id}/photos", data={
            "url": image_url, "published": "false",
        })
        photo_id = uploaded.get("id")
        if not photo_id:
            raise FacebookAPIError("Photo upload did not return an id")
        return self._request("POST", f"{self.page_id}/feed", data={
            "message": caption,
            "attached_media[0]": f'{{"media_fbid":"{photo_id}"}}',
            "published": "true",
        })

    def post_video(self, caption: str, video_url: str):
        """Publish a video to the Page's Timeline.

        Unlike photos, Facebook's /feed endpoint with attached_media only
        accepts photo IDs — it does NOT accept video IDs.  The correct way
        to create a video Timeline story is to upload directly to
        /{page}/videos with published=true and description=<caption>,
        which automatically creates a proper feed story (visible on the
        Timeline, not just buried in the Videos tab).

        Facebook fetches the file from file_url synchronously — this call
        doesn't return until Facebook finishes downloading + validating
        the video, which for a real video file (tens/hundreds of MB) can
        take several minutes depending on how fast our hosting serves it.
        A short timeout here doesn't fail cleanly, it just times out the
        HTTP request client-side while Facebook keeps working server-side
        — so the post looks "stuck" on retry after retry.
        """
        return self._request("POST", f"{self.page_id}/videos", data={
            "file_url": video_url,
            "description": caption,
            "published": "true",
        }, timeout=480)

    def post_text(self, caption: str):
        """Plain text status update — no media at all."""
        return self._request("POST", f"{self.page_id}/feed", data={
            "message": caption, "published": "true",
        })

    def post_reel(self, caption: str, video_url: str):
        """Publish a Facebook Reel.

        This is a genuinely different API from a normal Page video — a
        regular /videos upload NEVER appears in Reels no matter what, so
        this uses Meta's dedicated Reels upload flow:
          1) start an upload session (get a video_id + upload_url)
          2) download the video from our hosting URL, then POST the
             raw binary bytes to the upload_url (rupload.facebook.com
             does NOT support file_url — it strictly requires binary
             data with offset + file_size headers)
          3) finish the session with video_state=PUBLISHED to actually
             publish it as a Reel

        Reel processing can take a little time after step 3 returns
        success — that's normal Facebook-side video processing, not a
        failure on our end.
        """
        start = self._request("POST", f"{self.page_id}/video_reels", data={"upload_phase": "start"})
        video_id = start.get("video_id")
        upload_url = start.get("upload_url")
        if not video_id or not upload_url:
            raise FacebookAPIError("Could not start Reels upload session")

        try:
            # Step 2a: Download the video from our hosting URL.
            # Reels are typically short (15-90 s) so the file is manageable
            # in memory.  For very large files you'd want chunked streaming,
            # but Meta's rupload endpoint expects the whole blob in one POST.
            logger.info("Reel #%s: downloading video from %s", video_id, video_url)
            video_resp = self.session.get(video_url, timeout=300, stream=False)
            video_resp.raise_for_status()
            video_data = video_resp.content
            file_size = len(video_data)
            logger.info("Reel #%s: downloaded %d bytes, uploading to rupload…", video_id, file_size)

            # Step 2b: Upload raw binary to Facebook's rupload endpoint.
            # Required headers: Authorization, offset, file_size.
            # Content-Type must be application/octet-stream (raw bytes).
            resp = self.session.post(
                upload_url,
                data=video_data,
                headers={
                    "Authorization": f"OAuth {self.access_token}",
                    "Content-Type": "application/octet-stream",
                    "offset": "0",
                    "file_size": str(file_size),
                },
                timeout=480,
            )
            resp.raise_for_status()
            logger.info("Reel #%s: rupload complete, finishing…", video_id)
        except requests.exceptions.RequestException as e:
            raise FacebookAPIError(f"Reel upload failed: {e}")

        finish = self._request("POST", f"{self.page_id}/video_reels", data={
            "upload_phase": "finish",
            "video_id": video_id,
            "video_state": "PUBLISHED",
            "description": caption,
        }, timeout=60)
        # The finish call doesn't reliably echo the video_id back, but we
        # already have it — normalize so callers (and post_comment) can
        # always read result["id"] the same way as the other post_* methods.
        if "id" not in finish:
            finish["id"] = video_id
        return finish

    def post_comment(self, object_id: str, message: str):
        """Comment on a just-published post/video. Kept separate from the
        main publish call so a comment failure never marks the post itself
        as failed — the post already went live successfully."""
        return self._request("POST", f"{object_id}/comments", data={"message": message})

    def validate(self):
        return self._request("GET", self.page_id, params={"fields": "id,name"})


class PostingWorker:
    """Background worker that processes jobs across all accounts."""

    def __init__(self, app):
        self.app = app
        self.running = False
        self._posters = {}

    def _get_poster(self, account: Account):
        if account.id not in self._posters:
            self._posters[account.id] = FacebookPoster(
                account.fb_page_access_token,
                account.fb_page_id,
                account.fb_api_version,
            )
        return self._posters[account.id]

    def start(self):
        self.running = True
        logger.info("Worker started — multi-account mode.")
        # In-place schema migration: add error_message column to jobs if missing
        try:
            with self.app.app_context():
                inspector = inspect(db.engine)
                if "jobs" in inspector.get_table_names():
                    cols = [c["name"] for c in inspector.get_columns("jobs")]
                    if "error_message" not in cols:
                        db.session.execute(text("ALTER TABLE jobs ADD COLUMN error_message TEXT"))
                        db.session.commit()
                        logger.info("Migration: added 'error_message' column to jobs table.")
                if "posts" in inspector.get_table_names():
                    cols = [c["name"] for c in inspector.get_columns("posts")]
                    if "comment" not in cols:
                        db.session.execute(text("ALTER TABLE posts ADD COLUMN comment TEXT"))
                        db.session.commit()
                        logger.info("Migration: added 'comment' column to posts table.")
                    if "comment_posted" not in cols:
                        db.session.execute(text(
                            "ALTER TABLE posts ADD COLUMN comment_posted BOOLEAN NOT NULL DEFAULT FALSE"
                        ))
                        db.session.commit()
                        logger.info("Migration: added 'comment_posted' column to posts table.")
                    if "comment_error" not in cols:
                        db.session.execute(text("ALTER TABLE posts ADD COLUMN comment_error TEXT"))
                        db.session.commit()
                        logger.info("Migration: added 'comment_error' column to posts table.")
        except Exception as e:
            logger.warning("Schema migration skipped: %s", e)

        while self.running:
            try:
                with self.app.app_context():
                    self._tick()
                    self._cleanup_csv()
                    self._cleanup_old_jobs()
            except Exception as e:
                logger.exception("Worker tick failed: %s", e)
            time.sleep(self.app.config.get("WORKER_TICK_SECONDS", 30))
        logger.info("Worker stopped.")

    def stop(self):
        self.running = False

    def _tick(self):
        self._resume_interrupted_jobs()
        running_jobs = Job.query.filter(Job.status.in_(["running", "paused"])).all()

        for job in running_jobs:
            if job.status == "paused":
                continue

            account = Account.query.get(job.account_id)
            if not account or not account.is_active:
                job.status = "failed"
                job.error_message = "Account deactivated"
                db.session.commit()
                continue

            next_post = (
                Post.query.filter_by(job_id=job.id)
                .filter(Post.status.in_(["pending", "scheduled"]))
                .order_by(Post.id.asc())
                .first()
            )

            if not next_post:
                job.status = "completed"
                job.completed_at = datetime.utcnow()
                db.session.commit()
                logger.info("Job #%d (account #%d) completed.", job.id, account.id)
                continue

            if next_post.status == "pending":
                if job.started_at is None:
                    job.started_at = datetime.utcnow()
                last_posted = (
                    Post.query.filter_by(job_id=job.id)
                    .filter(Post.status == "posted")
                    .order_by(Post.posted_at.desc())
                    .first()
                )
                if last_posted and last_posted.posted_at:
                    next_post.scheduled_at = last_posted.posted_at + timedelta(minutes=job.interval_minutes)
                else:
                    next_post.scheduled_at = datetime.utcnow()
                next_post.status = "scheduled"
                db.session.commit()
                continue

            if next_post.status == "scheduled" and next_post.scheduled_at <= datetime.utcnow():
                self._execute_post(job, account, next_post)

    def _execute_post(self, job: Job, account: Account, post: Post):
        post.status = "posting"
        db.session.commit()
        try:
            poster = self._get_poster(account)
            if post.post_type == "video":
                result = poster.post_video(post.caption, post.media_url)
            elif post.post_type == "reel":
                result = poster.post_reel(post.caption, post.media_url)
            elif post.post_type == "text":
                result = poster.post_text(post.caption)
            else:
                result = poster.post_image(post.caption, post.media_url)
            post.status = "posted"
            post.posted_at = datetime.utcnow()
            post.fb_post_id = result.get("id") or result.get("post_id")
            job.completed_posts += 1
            logger.info("Job #%d: Post #%d published → %s", job.id, post.id, post.fb_post_id)

            # Optional comment — only attempted after the main post succeeds.
            # A comment failure never rolls back or fails the post itself,
            # since the actual content already went live successfully.
            if post.comment and post.comment.strip() and post.fb_post_id:
                try:
                    poster.post_comment(post.fb_post_id, post.comment.strip())
                    post.comment_posted = True
                    logger.info("Job #%d: Post #%d comment added.", job.id, post.id)
                except FacebookAPIError as ce:
                    post.comment_posted = False
                    post.comment_error = str(ce)
                    logger.warning("Job #%d: Post #%d comment failed → %s", job.id, post.id, ce)
        except FacebookAPIError as e:
            post.retry_count += 1
            if post.retry_count >= self.app.config.get("MAX_RETRIES", 3):
                post.status = "failed"
                post.error_message = str(e)
                job.failed_posts += 1
                logger.error("Job #%d: Post #%d failed → %s", job.id, post.id, e)
            else:
                post.status = "scheduled"
                post.scheduled_at = datetime.utcnow() + timedelta(minutes=5)
                logger.warning("Job #%d: Post #%d retry %d → %s",
                               job.id, post.id, post.retry_count, e)
        except Exception as e:
            post.status = "failed"
            post.error_message = str(e)
            job.failed_posts += 1
            logger.exception("Job #%d: Post #%d error", job.id, post.id)
        db.session.commit()

    def _resume_interrupted_jobs(self):
        interrupted = Job.query.filter_by(status="running").all()
        for job in interrupted:
            stuck = Post.query.filter_by(job_id=job.id, status="posting").all()
            for p in stuck:
                p.status = "scheduled"
                p.scheduled_at = datetime.utcnow()
            if stuck:
                db.session.commit()
                logger.info("Job #%d: Resumed %d stuck posts.", job.id, len(stuck))

    def _cleanup_csv(self):
        cutoff = datetime.utcnow() - timedelta(
            hours=self.app.config.get("CSV_RETENTION_HOURS", 24)
        )
        jobs = Job.query.filter(
            Job.status == "completed",
            Job.csv_deleted == False,
            Job.completed_at <= cutoff,
        ).all()
        for job in jobs:
            filepath = os.path.join(self.app.config["UPLOAD_FOLDER"], job.filename)
            if os.path.exists(filepath):
                try:
                    os.remove(filepath)
                    logger.info("Deleted CSV for Job #%d", job.id)
                except OSError as e:
                    logger.warning("Could not delete CSV for Job #%d: %s", job.id, e)
            job.csv_deleted = True
            job.csv_deleted_at = datetime.utcnow()
            db.session.commit()

    def _cleanup_old_jobs(self):
        """Permanently remove finished jobs (and their post history via
        cascade) once they're older than JOB_RETENTION_DAYS, so the DB
        doesn't grow forever. The CSV file is deleted first if it somehow
        still exists (normally _cleanup_csv already removed it earlier)."""
        cutoff = datetime.utcnow() - timedelta(
            days=self.app.config.get("JOB_RETENTION_DAYS", 15)
        )
        old_jobs = Job.query.filter(
            Job.status.in_(["completed", "failed"]),
            Job.completed_at.isnot(None),
            Job.completed_at <= cutoff,
        ).all()
        for job in old_jobs:
            filepath = os.path.join(self.app.config["UPLOAD_FOLDER"], job.filename)
            if os.path.exists(filepath):
                try:
                    os.remove(filepath)
                except OSError as e:
                    logger.warning("Could not delete CSV for Job #%d: %s", job.id, e)
            job_id, post_count = job.id, len(job.posts)
            db.session.delete(job)  # cascades to Post rows (see models.py)
            db.session.commit()
            logger.info(
                "Purged Job #%d and %d post record(s) — older than %d-day retention.",
                job_id, post_count, self.app.config.get("JOB_RETENTION_DAYS", 15),
            )
