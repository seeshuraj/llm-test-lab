import os
import json
import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from typing import Optional
from .auth import get_current_user
from .db import get_db
import sqlite3

router = APIRouter(prefix="/api/notifications", tags=["notifications"])

class NotificationSettings(BaseModel):
    email: str
    threshold: float = 0.7
    enabled: bool = True

class NotificationSettingsOut(BaseModel):
    email: str
    threshold: float
    enabled: bool

def _ensure_table(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS notification_settings (
            user_id TEXT PRIMARY KEY,
            email TEXT NOT NULL,
            threshold REAL NOT NULL DEFAULT 0.7,
            enabled INTEGER NOT NULL DEFAULT 1
        )
    """)
    conn.commit()

@router.get("/settings", response_model=NotificationSettingsOut)
def get_settings(user=Depends(get_current_user), db=Depends(get_db)):
    _ensure_table(db)
    row = db.execute(
        "SELECT email, threshold, enabled FROM notification_settings WHERE user_id=?",
        (user["id"],)
    ).fetchone()
    if not row:
        return NotificationSettingsOut(email=user["email"], threshold=0.7, enabled=True)
    return NotificationSettingsOut(email=row[0], threshold=row[1], enabled=bool(row[2]))

@router.post("/settings", response_model=NotificationSettingsOut)
def save_settings(body: NotificationSettings, user=Depends(get_current_user), db=Depends(get_db)):
    _ensure_table(db)
    db.execute("""
        INSERT INTO notification_settings (user_id, email, threshold, enabled)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            email=excluded.email,
            threshold=excluded.threshold,
            enabled=excluded.enabled
    """, (user["id"], body.email, body.threshold, int(body.enabled)))
    db.commit()
    return NotificationSettingsOut(email=body.email, threshold=body.threshold, enabled=body.enabled)

@router.post("/test")
def send_test_email(user=Depends(get_current_user), db=Depends(get_db)):
    _ensure_table(db)
    row = db.execute(
        "SELECT email FROM notification_settings WHERE user_id=?",
        (user["id"],)
    ).fetchone()
    email = row[0] if row else user["email"]
    result = send_alert_email(
        to=email,
        project="test-project",
        run_id="test-run-id",
        avg_score=0.45,
        threshold=0.7
    )
    if not result:
        raise HTTPException(status_code=500, detail="Failed to send email. Check RESEND_API_KEY.")
    return {"status": "sent", "to": email}

def send_alert_email(to: str, project: str, run_id: str, avg_score: float, threshold: float) -> bool:
    api_key = os.getenv("RESEND_API_KEY")
    if not api_key:
        print("[notifications] RESEND_API_KEY not set — skipping email")
        return False
    from_email = os.getenv("FROM_EMAIL", "onboarding@resend.dev")
    app_url = os.getenv("APP_URL", "https://llm-test-lab-app.vercel.app")
    try:
        resp = httpx.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "from": from_email,
                "to": [to],
                "subject": f"[LLM Test Lab] Alert: {project} score dropped to {avg_score:.2f}",
                "html": f"""
                <h2>Score Alert — LLM Test Lab</h2>
                <p>Project <strong>{project}</strong> scored <strong style='color:red'>{avg_score:.2f}</strong>, which is below your threshold of <strong>{threshold}</strong>.</p>
                <p><a href='{app_url}/runs/{run_id}'>View Run Results</a></p>
                <hr/>
                <small>You are receiving this because you set up alerts in LLM Test Lab. <a href='{app_url}/settings'>Manage settings</a></small>
                """
            },
            timeout=10
        )
        return resp.status_code == 200
    except Exception as e:
        print(f"[notifications] email error: {e}")
        return False

def check_and_notify(user_id: str, user_email: str, project: str, run_id: str, avg_score: float, db):
    """Called after every run to check if alert should fire."""
    _ensure_table(db)
    row = db.execute(
        "SELECT email, threshold, enabled FROM notification_settings WHERE user_id=?",
        (user_id,)
    ).fetchone()
    if not row:
        return
    email, threshold, enabled = row
    if not enabled:
        return
    if avg_score < threshold:
        print(f"[notifications] Score {avg_score} < threshold {threshold} — sending alert to {email}")
        send_alert_email(to=email, project=project, run_id=run_id, avg_score=avg_score, threshold=threshold)
