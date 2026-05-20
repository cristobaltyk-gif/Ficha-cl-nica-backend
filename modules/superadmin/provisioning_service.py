"""
modules/superadmin/provisioning_service.py
Automatiza la creación de infraestructura para externos completos.
Llama a Cloudflare, Vercel y Render APIs en secuencia.
"""
from __future__ import annotations
import os
import httpx

CLOUDFLARE_TOKEN  = os.getenv("CLOUDFLARE_TOKEN")
CLOUDFLARE_ZONE_ID = os.getenv("CLOUDFLARE_ZONE_ID")
VERCEL_TOKEN      = os.getenv("VERCEL_TOKEN")
VERCEL_PROJECT_ID = os.getenv("VERCEL_PROJECT_ID")
RENDER_API_KEY    = os.getenv("RENDER_API_KEY")
RENDER_SERVICE_ID = os.getenv("RENDER_SERVICE_ID")
FRONTEND_URLS     = os.getenv("FRONTEND_URLS", "")

BASE_DOMAIN = "reservas.icarticular.cl"


def provisionar_externo_completo(username: str) -> dict:
    """
    Crea subdominio completo para un externo_completo.
    Pasos:
    1. Cloudflare → CNAME username.reservas.icarticular.cl
    2. Vercel     → agrega dominio al proyecto
    3. Render     → actualiza FRONTEND_URLS
    """
    results = {}

    # ── 1. CLOUDFLARE ──────────────────────────────────────────
    try:
        results["cloudflare"] = _crear_cname_cloudflare(username)
    except Exception as e:
        results["cloudflare"] = {"ok": False, "error": str(e)}
        print(f"[PROVISIONING] ❌ Cloudflare error: {e}")

    # ── 2. VERCEL ──────────────────────────────────────────────
    try:
        results["vercel"] = _agregar_dominio_vercel(username)
    except Exception as e:
        results["vercel"] = {"ok": False, "error": str(e)}
        print(f"[PROVISIONING] ❌ Vercel error: {e}")

    # ── 3. RENDER ──────────────────────────────────────────────
    try:
        results["render"] = _actualizar_cors_render(username)
    except Exception as e:
        results["render"] = {"ok": False, "error": str(e)}
        print(f"[PROVISIONING] ❌ Render error: {e}")

    ok = all(r.get("ok") for r in results.values())
    print(f"[PROVISIONING] {'✅' if ok else '⚠️'} {username} — {results}")
    return {"ok": ok, "details": results}


def _crear_cname_cloudflare(username: str) -> dict:
    if not CLOUDFLARE_TOKEN or not CLOUDFLARE_ZONE_ID:
        raise ValueError("Faltan CLOUDFLARE_TOKEN o CLOUDFLARE_ZONE_ID")

    subdominio = f"{username}.{BASE_DOMAIN}"

    res = httpx.post(
        f"https://api.cloudflare.com/client/v4/zones/{CLOUDFLARE_ZONE_ID}/dns_records",
        headers={
            "Authorization": f"Bearer {CLOUDFLARE_TOKEN}",
            "Content-Type":  "application/json",
        },
        json={
            "type":    "CNAME",
            "name":    subdominio,
            "content": "cname.vercel-dns.com",
            "ttl":     1,
            "proxied": False,
        },
        timeout=10,
    )

    data = res.json()
    if not data.get("success"):
        # Si ya existe el registro no es un error crítico
        errors = data.get("errors", [])
        if any("already exists" in str(e).lower() for e in errors):
            print(f"[PROVISIONING] CNAME {subdominio} ya existe — ok")
            return {"ok": True, "note": "ya existía"}
        raise ValueError(f"Cloudflare error: {errors}")

    print(f"[PROVISIONING] ✅ CNAME creado: {subdominio}")
    return {"ok": True, "record": data.get("result", {}).get("id")}


def _agregar_dominio_vercel(username: str) -> dict:
    if not VERCEL_TOKEN or not VERCEL_PROJECT_ID:
        raise ValueError("Faltan VERCEL_TOKEN o VERCEL_PROJECT_ID")

    subdominio = f"{username}.{BASE_DOMAIN}"

    res = httpx.post(
        f"https://api.vercel.com/v10/projects/{VERCEL_PROJECT_ID}/domains",
        headers={
            "Authorization": f"Bearer {VERCEL_TOKEN}",
            "Content-Type":  "application/json",
        },
        json={"name": subdominio},
        timeout=10,
    )

    data = res.json()

    if res.status_code in (200, 201):
        print(f"[PROVISIONING] ✅ Dominio Vercel agregado: {subdominio}")
        return {"ok": True}

    # Si ya existe tampoco es error crítico
    if "already" in str(data).lower():
        print(f"[PROVISIONING] Dominio Vercel {subdominio} ya existe — ok")
        return {"ok": True, "note": "ya existía"}

    raise ValueError(f"Vercel error: {data}")


def _actualizar_cors_render(username: str) -> dict:
    if not RENDER_API_KEY or not RENDER_SERVICE_ID:
        raise ValueError("Faltan RENDER_API_KEY o RENDER_SERVICE_ID")

    nuevo_origen = f"https://{username}.{BASE_DOMAIN}"

    # Obtener env vars actuales
    res = httpx.get(
        f"https://api.render.com/v1/services/{RENDER_SERVICE_ID}/env-vars",
        headers={"Authorization": f"Bearer {RENDER_API_KEY}"},
        timeout=10,
    )

    if not res.is_success:
        raise ValueError(f"Render GET error: {res.text}")

    env_vars = res.json()

    # Buscar FRONTEND_URLS actual
    frontend_urls_actual = ""
    for var in env_vars:
        if var.get("envVar", {}).get("key") == "FRONTEND_URLS":
            frontend_urls_actual = var.get("envVar", {}).get("value", "")
            break

    # Agregar nuevo origen si no existe
    urls = [u.strip() for u in frontend_urls_actual.split(",") if u.strip()]
    if nuevo_origen in urls:
        print(f"[PROVISIONING] CORS {nuevo_origen} ya existe — ok")
        return {"ok": True, "note": "ya existía"}

    urls.append(nuevo_origen)
    nuevo_valor = ",".join(urls)

    # Actualizar
    res2 = httpx.put(
        f"https://api.render.com/v1/services/{RENDER_SERVICE_ID}/env-vars",
        headers={
            "Authorization": f"Bearer {RENDER_API_KEY}",
            "Content-Type":  "application/json",
        },
        json=[{"key": "FRONTEND_URLS", "value": nuevo_valor}],
        timeout=10,
    )

    if not res2.is_success:
        raise ValueError(f"Render PUT error: {res2.text}")

    print(f"[PROVISIONING] ✅ CORS actualizado: {nuevo_origen}")
    return {"ok": True, "frontend_urls": nuevo_valor}
