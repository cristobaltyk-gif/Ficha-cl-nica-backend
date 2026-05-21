"""
modules/superadmin/deprovisioning_service.py
Elimina infraestructura de externos completos y centros al borrar suscripción.
Llama a Cloudflare, Vercel y Render APIs en secuencia.
"""
from __future__ import annotations
import os
import httpx

CLOUDFLARE_TOKEN   = os.getenv("CLOUDFLARE_TOKEN")
CLOUDFLARE_ZONE_ID = os.getenv("CLOUDFLARE_ZONE_ID")
VERCEL_TOKEN       = os.getenv("VERCEL_TOKEN")
VERCEL_PROJECT_ID  = os.getenv("VERCEL_PROJECT_ID")
RENDER_API_KEY     = os.getenv("RENDER_API_KEY")
RENDER_SERVICE_ID  = os.getenv("RENDER_SERVICE_ID")

BASE_DOMAIN_EXTERNO = "reservas.icarticular.cl"
BASE_DOMAIN_CENTRO  = "icarticular.cl"


def desprovisionar_externo_completo(username: str) -> dict:
    """Elimina subdominio → username.reservas.icarticular.cl"""
    return _desprovisionar(username, BASE_DOMAIN_EXTERNO)


def desprovisionar_centro(centro_id: str) -> dict:
    """Elimina subdominio → centro_id.icarticular.cl"""
    return _desprovisionar(centro_id, BASE_DOMAIN_CENTRO)


def _desprovisionar(username: str, base_domain: str) -> dict:
    results = {}

    try:
        results["cloudflare"] = _eliminar_cname_cloudflare(username, base_domain)
    except Exception as e:
        results["cloudflare"] = {"ok": False, "error": str(e)}
        print(f"[DEPROVISIONING] ❌ Cloudflare error: {e}")

    try:
        results["vercel"] = _eliminar_dominio_vercel(username, base_domain)
    except Exception as e:
        results["vercel"] = {"ok": False, "error": str(e)}
        print(f"[DEPROVISIONING] ❌ Vercel error: {e}")

    try:
        results["render"] = _eliminar_cors_render(username, base_domain)
    except Exception as e:
        results["render"] = {"ok": False, "error": str(e)}
        print(f"[DEPROVISIONING] ❌ Render error: {e}")

    ok = all(r.get("ok") for r in results.values())
    print(f"[DEPROVISIONING] {'✅' if ok else '⚠️'} {username}.{base_domain} — {results}")
    return {"ok": ok, "details": results}


def _eliminar_cname_cloudflare(username: str, base_domain: str) -> dict:
    if not CLOUDFLARE_TOKEN or not CLOUDFLARE_ZONE_ID:
        raise ValueError("Faltan CLOUDFLARE_TOKEN o CLOUDFLARE_ZONE_ID")

    subdominio = f"{username}.{base_domain}"

    res = httpx.get(
        f"https://api.cloudflare.com/client/v4/zones/{CLOUDFLARE_ZONE_ID}/dns_records",
        headers={"Authorization": f"Bearer {CLOUDFLARE_TOKEN}"},
        params={"name": subdominio, "type": "CNAME"},
        timeout=10,
    )

    data = res.json()
    records = data.get("result", [])

    if not records:
        print(f"[DEPROVISIONING] CNAME {subdominio} no encontrado — ok")
        return {"ok": True, "note": "no existía"}

    record_id = records[0]["id"]

    res2 = httpx.delete(
        f"https://api.cloudflare.com/client/v4/zones/{CLOUDFLARE_ZONE_ID}/dns_records/{record_id}",
        headers={"Authorization": f"Bearer {CLOUDFLARE_TOKEN}"},
        timeout=10,
    )

    data2 = res2.json()
    if not data2.get("success"):
        raise ValueError(f"Cloudflare delete error: {data2.get('errors')}")

    print(f"[DEPROVISIONING] ✅ CNAME eliminado: {subdominio}")
    return {"ok": True}


def _eliminar_dominio_vercel(username: str, base_domain: str) -> dict:
    if not VERCEL_TOKEN or not VERCEL_PROJECT_ID:
        raise ValueError("Faltan VERCEL_TOKEN o VERCEL_PROJECT_ID")

    subdominio = f"{username}.{base_domain}"

    res = httpx.delete(
        f"https://api.vercel.com/v9/projects/{VERCEL_PROJECT_ID}/domains/{subdominio}",
        headers={"Authorization": f"Bearer {VERCEL_TOKEN}"},
        timeout=10,
    )

    if res.status_code == 200:
        print(f"[DEPROVISIONING] ✅ Dominio Vercel eliminado: {subdominio}")
        return {"ok": True}

    if res.status_code == 404:
        print(f"[DEPROVISIONING] Dominio Vercel {subdominio} no existía — ok")
        return {"ok": True, "note": "no existía"}

    raise ValueError(f"Vercel delete error: {res.text}")


def _eliminar_cors_render(username: str, base_domain: str) -> dict:
    if not RENDER_API_KEY or not RENDER_SERVICE_ID:
        raise ValueError("Faltan RENDER_API_KEY o RENDER_SERVICE_ID")

    origen = f"https://{username}.{base_domain}"

    res = httpx.get(
        f"https://api.render.com/v1/services/{RENDER_SERVICE_ID}/env-vars",
        headers={"Authorization": f"Bearer {RENDER_API_KEY}"},
        timeout=10,
    )

    if not res.is_success:
        raise ValueError(f"Render GET error: {res.text}")

    env_vars = res.json()

    frontend_urls_actual = ""
    for var in env_vars:
        if var.get("envVar", {}).get("key") == "FRONTEND_URLS":
            frontend_urls_actual = var.get("envVar", {}).get("value", "")
            break

    urls = [u.strip() for u in frontend_urls_actual.split(",") if u.strip()]

    if origen not in urls:
        print(f"[DEPROVISIONING] CORS {origen} no existía — ok")
        return {"ok": True, "note": "no existía"}

    urls.remove(origen)
    nuevo_valor = ",".join(urls)

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

    print(f"[DEPROVISIONING] ✅ CORS eliminado: {origen}")
    return {"ok": True, "frontend_urls": nuevo_valor}
