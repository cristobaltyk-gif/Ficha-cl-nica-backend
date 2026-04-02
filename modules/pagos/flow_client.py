"""
modules/pagos/flow_client.py
Cliente Flow para Python.
"""

import os
import hmac
import hashlib
import json
import httpx
from typing import Optional

FLOW_API_KEY    = os.getenv("FLOW_API_KEY", "")
FLOW_SECRET_KEY = os.getenv("FLOW_SECRET_KEY", "")
FLOW_ENV        = os.getenv("FLOW_ENV", "sandbox")

FLOW_BASE_URL = (
    "https://www.flow.cl/api"
    if FLOW_ENV == "production"
    else "https://sandbox.flow.cl/api"
)


def _assert_env():
    if not FLOW_API_KEY or not FLOW_SECRET_KEY:
        raise RuntimeError("Faltan variables FLOW_API_KEY / FLOW_SECRET_KEY")


def _make_signature(params: dict) -> str:
    ordered     = sorted(params.keys())
    query       = "&".join(f"{k}={params[k]}" for k in ordered)
    return hmac.new(
        FLOW_SECRET_KEY.encode("utf-8"),
        query.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()


def crear_pago(
    *,
    id_pago:          str,
    amount:           int,
    subject:          str,
    email:            str,
    url_confirmation: str,
    url_return:       str,
    optional_data:    Optional[dict] = None
) -> dict:
    _assert_env()

    base_params = {
        "apiKey":          FLOW_API_KEY,
        "commerceOrder":   id_pago,
        "subject":         subject,
        "currency":        "CLP",
        "amount":          str(amount),
        "email":           email,
        "urlConfirmation": url_confirmation,
        "urlReturn":       url_return,
        "optional":        json.dumps(optional_data or {}),
    }

    base_params["s"] = _make_signature(base_params)

    with httpx.Client(timeout=30) as client:
        res = client.post(
            f"{FLOW_BASE_URL}/payment/create",
            data=base_params,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept":       "application/json",
            }
        )

    data = res.json()

    if res.status_code == 200 and data.get("url"):
        return {
            "url":       data["url"],
            "token":     data.get("token"),
            "flowOrder": data.get("flowOrder"),
        }

    raise RuntimeError(data.get("message") or f"Error Flow HTTP {res.status_code}")


def obtener_estado_pago(token: str) -> dict:
    _assert_env()

    params = {
        "apiKey": FLOW_API_KEY,
        "token":  token,
    }
    params["s"] = _make_signature(params)

    with httpx.Client(timeout=30) as client:
        res = client.get(
            f"{FLOW_BASE_URL}/payment/getStatus",
            params=params
        )

    return res.json()
  
