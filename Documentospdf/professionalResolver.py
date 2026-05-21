# Documentospdf/professionalResolver.py
import os
from db.supabase_client import _get_conn


def getProfessionalData(professionalId: str):
    try:
        with _get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT * FROM profesionales WHERE id = %s AND active = TRUE",
                    (professionalId,)
                )
                row = cur.fetchone()
                if not row:
                    return None

                medico = dict(row)
                medico["firma"]  = f"firma_{professionalId}.png"
                medico["timbre"] = f"timbre_{professionalId}.png"
                return medico

    except Exception as e:
        print("ERROR professionalResolver:", e)
        return None
