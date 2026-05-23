"""
modules/superadmin/provisioning_service.py
Automatiza la creación de infraestructura para externos completos y centros.
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


def provisionar_externo_completo(username: str) -> dict:
    return _provisionar(username, BASE_DOMAIN_EXTERNO)


def provisionar_centro(centro_id: str) -> dict:
    return _provisionar(centro_id, BASE_DOMAIN_CENTRO)


def _provisionar(username: str, base_domain: str) -> dict:
    results = {}

    # ── 1. VERCEL primero — para obtener CNAME y TXT correctos ──
    try:
        vercel_result = _agregar_dominio_vercel(username, base_domain)
        results["vercel"] = vercel_result
    except Exception as e:
        results["vercel"] = {"ok": False, "error": str(e)}
        print(f"[PROVISIONING] ❌ Vercel error: {e}")
        vercel_result = {}

    # ── 2. CLOUDFLARE — con datos dinámicos de Vercel ──
    try:
        cname_target = vercel_result.get("cname", "cname.vercel-dns.com")
        txt_name     = vercel_result.get("txt_name")
        txt_value    = vercel_result.get("txt_value")
        results["cloudflare"] = _crear_registros_cloudflare(
            username, base_domain, cname_target, txt_name, txt_value
        )
    except Exception as e:
        results["cloudflare"] = {"ok": False, "error": str(e)}
        print(f"[PROVISIONING] ❌ Cloudflare error: {e}")

    # ── 3. RENDER — solo agrega la nueva URL, no toca nada más ──
    try:
        results["render"] = _actualizar_cors_render(username, base_domain)
    except Exception as e:
        results["render"] = {"ok": False, "error": str(e)}
        print(f"[PROVISIONING] ❌ Render error: {e}")

    ok = all(r.get("ok") for r in results.values())
    print(f"[PROVISIONING] {'✅' if ok else '⚠️'} {username}.{base_domain} — {results}")
    return {"ok": ok, "details": results}


def _agregar_dominio_vercel(username: str, base_domain: str) -> dict:
    if not VERCEL_TOKEN or not VERCEL_PROJECT_ID:
        raise ValueError("Faltan VERCEL_TOKEN o VERCEL_PROJECT_ID")

    subdominio = f"{username}.{base_domain}"

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
    already_exists = res.status_code not in (200, 201) and "already" in str(data).lower()

    if res.status_code not in (200, 201) and not already_exists:
        raise ValueError(f"Vercel error: {data}")

    if already_exists:
        print(f"[PROVISIONING] Dominio Vercel {subdominio} ya existe — consultando detalles")

    # Consultar detalles para obtener CNAME y TXT dinámicos
    res2 = httpx.get(
        f"https://api.vercel.com/v9/projects/{VERCEL_PROJECT_ID}/domains/{subdominio}",
        headers={"Authorization": f"Bearer {VERCEL_TOKEN}"},
        timeout=10,
    )

    details = res2.json()
    print(f"[PROVISIONING] Vercel domain details: {details}")

    # Extraer CNAME target dinámico
    cname_target = details.get("cname") or "cname.vercel-dns.com"

    # Extraer TXT de verificación
    txt_name  = None
    txt_value = None
    for v in (details.get("verification") or []):
        if v.get("type") == "TXT":
            txt_name  = v.get("domain")
            txt_value = v.get("value")
            break

    print(f"[PROVISIONING] ✅ Vercel: cname={cname_target} txt_name={txt_name}")
    return {
        "ok":        True,
        "cname":     cname_target,
        "txt_name":  txt_name,
        "txt_value": txt_value,
    }


def _crear_registros_cloudflare(
    username: str, base_domain: str,
    cname_target: str,
    txt_name: str | None,
    txt_value: str | None,
) -> dict:
    if not CLOUDFLARE_TOKEN or not CLOUDFLARE_ZONE_ID:
        raise ValueError("Faltan CLOUDFLARE_TOKEN o CLOUDFLARE_ZONE_ID")

    subdominio = f"{username}.{base_domain}"
    headers    = {
        "Authorization": f"Bearer {CLOUDFLARE_TOKEN}",
        "Content-Type":  "application/json",
    }

    # ── CNAME ──
    res_cname = httpx.post(
        f"https://api.cloudflare.com/client/v4/zones/{CLOUDFLARE_ZONE_ID}/dns_records",
        headers=headers,
        json={
            "type":    "CNAME",
            "name":    subdominio,
            "content": cname_target,
            "ttl":     1,
            "proxied": False,
        },
        timeout=10,
    )
    data_cname = res_cname.json()
    if not data_cname.get("success"):
        errors = data_cname.get("errors", [])
        if not any("already exists" in str(e).lower() for e in errors):
            raise ValueError(f"Cloudflare CNAME error: {errors}")
        print(f"[PROVISIONING] CNAME {subdominio} ya existía — ok")
    else:
        print(f"[PROVISIONING] ✅ CNAME creado: {subdominio} → {cname_target}")

    # ── TXT verificación ──
    if txt_name and txt_value:
        res_txt = httpx.post(
            f"https://api.cloudflare.com/client/v4/zones/{CLOUDFLARE_ZONE_ID}/dns_records",
            headers=headers,
            json={
                "type":    "TXT",
                "name":    txt_name,
                "content": txt_value,
                "ttl":     1,
            },
            timeout=10,
        )
        data_txt = res_txt.json()
        if not data_txt.get("success"):
            errors = data_txt.get("errors", [])
            if not any("already exists" in str(e).lower() for e in errors):
                print(f"[PROVISIONING] ⚠️ TXT warning: {errors}")
            else:
                print(f"[PROVISIONING] TXT ya existía — ok")
        else:
            print(f"[PROVISIONING] ✅ TXT verificación creado: {txt_name}")

    return {"ok": True}


def _actualizar_cors_render(username: str, base_domain: str) -> dict:
    if not RENDER_API_KEY or not RENDER_SERVICE_ID:
        raise ValueError("Faltan RENDER_API_KEY o RENDER_SERVICE_ID")

    nuevo_origen = f"https://{username}.{base_domain}"

    # ── Leer TODAS las variables actuales ──
    res = httpx.get(
        f"https://api.render.com/v1/services/{RENDER_SERVICE_ID}/env-vars",
        headers={"Authorization": f"Bearer {RENDER_API_KEY}"},
        timeout=10,
    )
    if not res.is_success:
        raise ValueError(f"Render GET error: {res.text}")

    env_vars = res.json()

    # Buscar FRONTEND_URLS y actualizar solo esa
    frontend_urls_actual = ""
    for var in env_vars:
        if var.get("envVar", {}).get("key") == "FRONTEND_URLS":
            frontend_urls_actual = var.get("envVar", {}).get("value", "")
            break

    urls = [u.strip() for u in frontend_urls_actual.split(",") if u.strip()]
    if nuevo_origen in urls:
        print(f"[PROVISIONING] CORS {nuevo_origen} ya existe — ok")
        return {"ok": True, "note": "ya existía"}

    urls.append(nuevo_origen)
    nuevo_valor = ",".join(urls)

    # ── Construir lista completa con TODAS las vars + FRONTEND_URLS actualizado ──
    todas_las_vars = []
    frontend_incluido = False
    for var in env_vars:
        key = var.get("envVar", {}).get("key")
        val = var.get("envVar", {}).get("value", "")
        if key == "FRONTEND_URLS":
            todas_las_vars.append({"key": key, "value": nuevo_valor})
            frontend_incluido = True
        elif key:
            todas_las_vars.append({"key": key, "value": val})

    if not frontend_incluido:
        todas_las_vars.append({"key": "FRONTEND_URLS", "value": nuevo_valor})

    # ── PUT con TODAS las variables — no se pierde ninguna ──
    res2 = httpx.put(
        f"https://api.render.com/v1/services/{RENDER_SERVICE_ID}/env-vars",
        headers={
            "Authorization": f"Bearer {RENDER_API_KEY}",
            "Content-Type":  "application/json",
        },
        json=todas_las_vars,
        timeout=10,
    )

    if not res2.is_success:
        raise ValueError(f"Render PUT error: {res2.text}")

    print(f"[PROVISIONING] ✅ CORS actualizado: {nuevo_origen}")
    return {"ok": True, "frontend_urls": nuevo_valor}
