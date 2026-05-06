"""Stripe billing router — Checkout session creation + webhook handler.

Environment variables required:
  STRIPE_SECRET_KEY        — sk_live_... or sk_test_...
  STRIPE_WEBHOOK_SECRET    — whsec_... from Stripe Dashboard → Webhooks
  STRIPE_PRO_PRICE_ID      — price_... for the Pro monthly plan
  FRONTEND_URL             — e.g. https://llm-test-lab-app.vercel.app

Endpoints:
  POST /billing/checkout   — creates a Stripe Checkout Session, returns {url}
  POST /billing/webhook    — handles checkout.session.completed → sets is_pro=True
  GET  /billing/status     — returns current plan status
"""

from __future__ import annotations

import logging
import os

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .auth import get_current_user
from .db import get_db
from .models import User

logger = logging.getLogger(__name__)

router = APIRouter()

_STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY", "")
_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
_PRO_PRICE_ID = os.environ.get("STRIPE_PRO_PRICE_ID", "")
_FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:3000")

# Only import stripe if the key is configured — avoids hard crashes during
# local dev or staging when the Stripe env vars are not set.
if _STRIPE_SECRET_KEY:
    import stripe as _stripe
    _stripe.api_key = _STRIPE_SECRET_KEY
else:
    _stripe = None  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# GET /billing/status  — let the frontend poll plan status
# ---------------------------------------------------------------------------

@router.get("/status")
async def billing_status(
    current_user: User = Depends(get_current_user),
):
    """Return current billing / plan state for the authenticated user.

    Always returns a valid response regardless of whether Stripe is configured.
    """
    return {
        "is_pro": current_user.is_pro,
        "email": current_user.email,
        # Don't expose the raw Stripe customer ID to the frontend;
        # just signal whether a payment method is on file.
        "has_payment_method": bool(
            getattr(current_user, "stripe_customer_id", None)
        ),
        "stripe_enabled": bool(_STRIPE_SECRET_KEY),
    }


# ---------------------------------------------------------------------------
# POST /billing/checkout
# ---------------------------------------------------------------------------

@router.post("/checkout")
async def create_checkout_session(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a Stripe Checkout session for the Pro plan.

    Returns 503 with a friendly message when Stripe env vars are not yet set,
    so the frontend can surface a "coming soon" notice instead of crashing.
    """
    # ── Guard: Stripe not configured yet ────────────────────────────────────
    if not _STRIPE_SECRET_KEY or _stripe is None:
        raise HTTPException(
            status_code=503,
            detail=(
                "Billing is not yet live. To get early Pro access, "
                "email us at hello@llmtestlab.com or check back soon."
            ),
        )

    if not _PRO_PRICE_ID:
        raise HTTPException(
            status_code=503,
            detail="Billing is not fully configured on this server. Please contact support.",
        )

    if current_user.is_pro:
        raise HTTPException(status_code=400, detail="You are already on the Pro plan.")

    # ── Create or reuse Stripe customer ─────────────────────────────────────
    customer_id = getattr(current_user, "stripe_customer_id", None)

    if not customer_id:
        customer = _stripe.Customer.create(
            email=current_user.email,
            metadata={"user_id": current_user.id},
        )
        customer_id = customer.id
        result = await db.execute(select(User).where(User.id == current_user.id))
        user = result.scalar_one_or_none()
        if user:
            user.stripe_customer_id = customer_id
            await db.commit()

    session = _stripe.checkout.Session.create(
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
    if not _WEBHOOK_SECRET or _stripe is None:
        raise HTTPException(status_code=503, detail="Webhook secret not configured.")

    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    try:
        event = _stripe.Webhook.construct_event(payload, sig_header, _WEBHOOK_SECRET)
    except _stripe.error.SignatureVerificationError as exc:
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

        user: User | None = None
        if user_id:
            result = await db.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()

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
                logger.info(
                    "User %s downgraded to Free (subscription cancelled)", user.id
                )

    return {"received": True}
