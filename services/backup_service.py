"""
services/backup_service.py
--------------------------
Backup diario automático de /data/*.json → Cloudflare R2
Sigue el mismo patrón threading que modules/pagos/scheduler.py

Variables de entorno necesarias (ya agregadas en Render):
    R2_ACCOUNT_ID        → ID cuenta Cloudflare
    R2_ACCESS_KEY_ID     → Access Key del token R2
    R2_SECRET_ACCESS_KEY → Secret Key del token R2
    R2_BUCKET_NAME       → ica-backups
"""

from __future__ import annotations

import os
import tarfile
import logging
import tempfile
import threading
import time
from datetime import datetime, timezone, date
from pathlib import Path
from zoneinfo import ZoneInfo

import boto3
from botocore.config import Config

logger = logging.getLogger(__name__)

DATA_DIR      = Path("/data")
CHILE_TZ      = ZoneInfo("America/Santiago")
RETENTION_DAYS = 30
BACKUP_HOUR   = 3   # 03:00 hora Chile — menor actividad


# ── Cliente R2 ─────────────────────────────────────────────────────────────────

def _get_r2_client():
    account_id = os.environ["R2_ACCOUNT_ID"]
    return boto3.client(
        "s3",
        endpoint_url=f"https://{account_id}.r2.cloudflarestorage.com",
        aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
        config=Config(signature_version="s3v4"),
        region_name="auto",
    )


# ── Lógica de backup ───────────────────────────────────────────────────────────

def run_backup():
    """
    1. Comprime todos los JSON de /data en un tar.gz con timestamp
    2. Sube el archivo a R2 bajo daily/
    3. Elimina backups con más de RETENTION_DAYS días
    """
    bucket    = os.environ["R2_BUCKET_NAME"]
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename  = f"ica_backup_{timestamp}.tar.gz"

    json_files = list(DATA_DIR.rglob("*.json"))
    if not json_files:
        print(f"⚠️  [BACKUP] No se encontraron archivos JSON en {DATA_DIR}")
        return

    print(f"📦 [BACKUP] Iniciando — {len(json_files)} archivos JSON → {filename}")

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            tar_path = Path(tmpdir) / filename

            with tarfile.open(tar_path, "w:gz") as tar:
                for json_file in json_files:
                    arcname = json_file.relative_to(DATA_DIR.parent)
                    tar.add(json_file, arcname=str(arcname))

            size_mb = tar_path.stat().st_size / (1024 * 1024)
            print(f"📦 [BACKUP] Comprimido: {size_mb:.2f} MB")

            client = _get_r2_client()
            client.upload_file(
                str(tar_path),
                bucket,
                f"daily/{filename}",
                ExtraArgs={"ContentType": "application/gzip"},
            )
            print(f"✅ [BACKUP] Subido exitosamente → daily/{filename}")

        _cleanup_old_backups(client, bucket)

    except Exception as e:
        print(f"❌ [BACKUP] Error durante el backup: {e}")


def _cleanup_old_backups(client, bucket: str):
    """Elimina backups en R2 con más de RETENTION_DAYS días."""
    try:
        response = client.list_objects_v2(Bucket=bucket, Prefix="daily/")
        objects  = response.get("Contents", [])
        now      = datetime.now(timezone.utc)
        deleted  = 0

        for obj in objects:
            age_days = (now - obj["LastModified"]).days
            if age_days > RETENTION_DAYS:
                client.delete_object(Bucket=bucket, Key=obj["Key"])
                print(f"🗑️  [BACKUP] Eliminado backup antiguo: {obj['Key']} ({age_days} días)")
                deleted += 1

        print(f"🧹 [BACKUP] Limpieza: {deleted} backups eliminados")

    except Exception as e:
        print(f"⚠️  [BACKUP] Error en limpieza: {e}")


# ── Loop threading (mismo patrón que pagos/scheduler.py) ──────────────────────

def _loop():
    print("🕐 [BACKUP] Scheduler backup iniciado — corre diario a las 03:00 Chile")
    ultimo: date | None = None

    while True:
        ahora = datetime.now(CHILE_TZ)
        hoy   = ahora.date()

        if ahora.hour == BACKUP_HOUR and ahora.minute < 5 and ultimo != hoy:
            print(f"🚀 [BACKUP] Ejecutando backup diario {hoy}…")
            try:
                run_backup()
            except Exception as e:
                print(f"❌ [BACKUP] Error en loop: {e}")
            ultimo = hoy

        time.sleep(60)


def start_backup_scheduler():
    t = threading.Thread(target=_loop, daemon=True)
    t.start()
    print("🚀 [BACKUP] Scheduler backup iniciado")
    
