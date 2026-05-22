"""
modules/profesionales/firma_router.py
Sube y procesa firma de profesional — elimina fondo y guarda en BD.
"""
from __future__ import annotations
import io
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
        # Leer imagen
        contenido = await file.read()

        # Eliminar fondo con rembg
        try:
            from rembg import remove
            contenido_sin_fondo = remove(contenido)
        except Exception as e:
            print(f"[FIRMA] rembg falló, guardando original: {e}")
            contenido_sin_fondo = contenido

        # Guardar en BD
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


@router.post("/{professional_id}/timbre")
async def subir_timbre(
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
            print(f"[TIMBRE] rembg falló, guardando original: {e}")
            contenido_sin_fondo = contenido

        with _get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE profesionales SET timbre_data = %s WHERE id = %s",
                    (contenido_sin_fondo, professional_id)
                )
                if cur.rowcount == 0:
                    raise HTTPException(404, "Profesional no encontrado")
                conn.commit()

        print(f"[TIMBRE] ✅ Timbre guardado para {professional_id}")
        return {"ok": True}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))
