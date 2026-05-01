"""Stripe billing router — Checkout session creation + webhook handler.

Environment variables required:
  STRIPE_SECRET_KEY        — sk_live_... or sk_test_...
  STRIPE_WEBHOOK_SECRET    — whsec_... from Stripe Dashboard → Webhooks
  STRIPE_PRO_PRICE_ID      — price_... for the Pro monthly plan
  FRONTEND_URL             — e.g. https://llm-test-lab-app.vercel.app

Endpoints:
  POST /billing/checkout   — creates a Stripe Checkout Session, returns {url}
  POST /billing/webhook    — handles checkout.session.completed → sets is_pro=True
"""

from __future__ import annotations

import logging
import os

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .auth import get_current_user
from .db import get_db
from .models import User

logger = logging.getLogger(__name__)

router = APIRouter()

stripe.api_key = os.environ.get("STRIPE_SECRET_KEY", "")
_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
_PRO_PRICE_ID = os.environ.get("STRIPE_PRO_PRICE_ID", "")
_FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:3000")


# ---------------------------------------------------------------------------
# POST /billing/checkout
# ---------------------------------------------------------------------------

@router.post("/checkout")
async def create_checkout_session(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a Stripe Checkout session for the Pro plan.

    If the user already has a stripe_customer_id we reuse it so Stripe can
    pre-fill their payment details on return visits.
    """
    if not stripe.api_key:
        raise HTTPException(status_code=503, detail="Stripe is not configured on this server.")

    if current_user.is_pro:
        raise HTTPException(status_code=400, detail="You are already on the Pro plan.")

    customer_id = current_user.stripe_customer_id

    # Create or reuse Stripe customer
    if not customer_id:
        customer = stripe.Customer.create(email=current_user.email, metadata={"user_id": current_user.id})
        customer_id = customer.id
        # Persist customer_id immediately so we can reconcile the webhook
        result = await db.execute(select(User).where(User.id == current_user.id))
        user = result.scalar_one_or_none()
        if user:
            user.stripe_customer_id = customer_id
            await db.commit()

    session = stripe.checkout.Session.create(
        customer=customer_id,
        mode="subscription",
        line_items=[{"price": _PRO_PRICE_ID, "quantity": 1}],
        success_url=f"{_FRONTEND_URL}/settings?upgraded=1",
        cancel_url=f"{_FRONTEND_URL}/settings?upgraded=0",
        metadata={"user_id": current_user.id},
    )

    return {"url": session.url}


# ---------------------------------------------------------------------------
# POST /billing/webhook  (no auth — Stripe calls this directly)
# ---------------------------------------------------------------------------

@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Handle Stripe webhook events.

    Stripe signs every event with the webhook secret so we verify the
    signature before trusting the payload.
    """
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    if not _WEBHOOK_SECRET:
        raise HTTPException(status_code=503, detail="Webhook secret not configured.")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, _WEBHOOK_SECRET)
    except stripe.error.SignatureVerificationError as exc:
        logger.warning("Stripe webhook signature invalid: %s", exc)
        raise HTTPException(status_code=400, detail="Invalid Stripe signature")
    except Exception as exc:
        logger.error("Stripe webhook parse error: %s", exc)
        raise HTTPException(status_code=400, detail="Webhook parse error")

    # ── Handle checkout.session.completed ────────────────────────────────────
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        user_id: str | None = (session.get("metadata") or {}).get("user_id")
        customer_id: str | None = session.get("customer")

        # Look up by user_id in metadata (most reliable)
        user: User | None = None
        if user_id:
            result = await db.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()

        # Fallback: look up by stripe_customer_id
        if not user and customer_id:
            result = await db.execute(
                select(User).where(User.stripe_customer_id == customer_id)
            )
            user = result.scalar_one_or_none()

        if user:
            user.is_pro = True
            if customer_id and not user.stripe_customer_id:
                user.stripe_customer_id = customer_id
            await db.commit()
            logger.info("User %s upgraded to Pro (customer=%s)", user.id, customer_id)
        else:
            logger.warning(
                "checkout.session.completed: could not find user for user_id=%s customer=%s",
                user_id, customer_id,
            )

    # ── Handle customer.subscription.deleted (downgrade) ─────────────────────
    elif event["type"] == "customer.subscription.deleted":
        sub = event["data"]["object"]
        customer_id = sub.get("customer")
        if customer_id:
            result = await db.execute(
                select(User).where(User.stripe_customer_id == customer_id)
            )
            user = result.scalar_one_or_none()
            if user:
                user.is_pro = False
                await db.commit()
                logger.info("User %s downgraded to Free (subscription cancelled)", user.id)

    return {"received": True}


# ---------------------------------------------------------------------------
# GET /billing/status  — let the frontend poll plan status
# ---------------------------------------------------------------------------

@router.get("/status")
async def billing_status(
    current_user: User = Depends(get_current_user),
):
    return {
        "is_pro": current_user.is_pro,
        "email": current_user.email,
        "stripe_customer_id": current_user.stripe_customer_id,
    }
