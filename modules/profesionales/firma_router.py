"""
modules/profesionales/firma_router.py
Sube y procesa firma de profesional — elimina fondo y guarda en BD.
Genera timbre automático con Pillow.
"""
from __future__ import annotations
from fastapi import APIRouter, HTTPException, UploadFile, File, Depends
from auth.internal_auth import require_internal_auth
from db.supabase_client import _get_conn

router = APIRouter(prefix="/api/profesionales", tags=["Profesionales"])


@router.post("/{professional_id}/firma")
async def subir_firma(
    professional_id: str,
    file: UploadFile = File(...),
    user=Depends(require_internal_auth)
):
    try:
        contenido = await file.read()

        try:
            from rembg import remove
            contenido_sin_fondo = remove(contenido)
        except Exception as e:
            print(f"[FIRMA] rembg falló, guardando original: {e}")
            contenido_sin_fondo = contenido

        with _get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE profesionales SET firma_data = %s WHERE id = %s",
                    (contenido_sin_fondo, professional_id)
                )
                if cur.rowcount == 0:
                    raise HTTPException(404, "Profesional no encontrado")
                conn.commit()

        print(f"[FIRMA] ✅ Firma guardada para {professional_id}")
        return {"ok": True}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))


@router.post("/{professional_id}/generar-timbre")
async def generar_timbre_endpoint(
    professional_id: str,
    user=Depends(require_internal_auth)
):
    try:
        from modules.profesionales.timbre_generator import generar_timbre
        timbre_bytes = generar_timbre(professional_id)

        with _get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE profesionales SET timbre_data = %s WHERE id = %s",
                    (timbre_bytes, professional_id)
                )
                if cur.rowcount == 0:
                    raise HTTPException(404, "Profesional no encontrado")
                conn.commit()

        print(f"[TIMBRE] ✅ Timbre generado para {professional_id}")
        return {"ok": True}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))
