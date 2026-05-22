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

                # Escribir firma y timbre en assets/ para compatibilidad con PDFs
                base_dir     = os.path.dirname(os.path.abspath(__file__))
                project_root = os.path.dirname(base_dir)
                assets_dir   = os.path.join(project_root, "assets")
                os.makedirs(assets_dir, exist_ok=True)

                firma_nombre  = f"firma_{professionalId}.png"
                timbre_nombre = f"timbre_{professionalId}.png"

                if medico.get("firma_data"):
                    with open(os.path.join(assets_dir, firma_nombre), "wb") as f:
                        f.write(bytes(medico["firma_data"]))

                if medico.get("timbre_data"):
                    with open(os.path.join(assets_dir, timbre_nombre), "wb") as f:
                        f.write(bytes(medico["timbre_data"]))

                medico["firma"]  = firma_nombre
                medico["timbre"] = timbre_nombre
                return medico

    except Exception as e:
        print("ERROR professionalResolver:", e)
        return None
