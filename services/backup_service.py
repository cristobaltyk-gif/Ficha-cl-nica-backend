"""
backup_service.py
-----------------
Backup diario automático de /data/*.json → Cloudflare R2
Se integra al APScheduler existente del backend FastAPI ICA.

Requisitos:
    pip install boto3 apscheduler

Variables de entorno necesarias (agregar en Render):
    R2_ACCOUNT_ID        → ID de tu cuenta Cloudflare
    R2_ACCESS_KEY_ID     → Access Key del token R2
    R2_SECRET_ACCESS_KEY → Secret Key del token R2
    R2_BUCKET_NAME       → Nombre del bucket (ej: ica-backups)
"""

import os
import tarfile
import logging
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import boto3
from botocore.config import Config

logger = logging.getLogger(__name__)

# ── Configuración ──────────────────────────────────────────────────────────────

DATA_DIR = Path("/data")
RETENTION_DAYS = 30  # Backups a conservar en R2 (norma exige 15 años, pero
                     # para backups diarios 30 días es suficiente — los datos
                     # originales siguen en /data y en Render)

def _get_r2_client():
    """Crea cliente boto3 apuntando a Cloudflare R2."""
    account_id = os.environ["R2_ACCOUNT_ID"]
    return boto3.client(
        "s3",
        endpoint_url=f"https://{account_id}.r2.cloudflarestorage.com",
        aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
        config=Config(signature_version="s3v4"),
        region_name="auto",
    )


# ── Lógica principal ───────────────────────────────────────────────────────────

def run_backup():
    """
    1. Comprime todos los JSON de /data en un tar.gz con timestamp
    2. Sube el archivo a R2
    3. Elimina backups con más de RETENTION_DAYS días en R2
    """
    bucket = os.environ["R2_BUCKET_NAME"]
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup_filename = f"ica_backup_{timestamp}.tar.gz"

    # Verificar que hay archivos para respaldar
    json_files = list(DATA_DIR.rglob("*.json"))
    if not json_files:
        logger.warning("[BACKUP] No se encontraron archivos JSON en %s", DATA_DIR)
        return

    logger.info("[BACKUP] Iniciando backup de %d archivos JSON → %s", len(json_files), backup_filename)

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            tar_path = Path(tmpdir) / backup_filename

            # Comprimir todos los JSON
            with tarfile.open(tar_path, "w:gz") as tar:
                for json_file in json_files:
                    # Mantener estructura relativa desde /data
                    arcname = json_file.relative_to(DATA_DIR.parent)
                    tar.add(json_file, arcname=str(arcname))

            size_mb = tar_path.stat().st_size / (1024 * 1024)
            logger.info("[BACKUP] Archivo comprimido: %.2f MB", size_mb)

            # Subir a R2
            client = _get_r2_client()
            client.upload_file(
                str(tar_path),
                bucket,
                f"daily/{backup_filename}",
                ExtraArgs={"ContentType": "application/gzip"},
            )
            logger.info("[BACKUP] ✅ Subido exitosamente a R2: daily/%s", backup_filename)

        # Limpiar backups antiguos en R2
        _cleanup_old_backups(client, bucket)

    except Exception as e:
        logger.error("[BACKUP] ❌ Error durante el backup: %s", str(e), exc_info=True)
        raise


def _cleanup_old_backups(client, bucket: str):
    """Elimina backups en R2 con más de RETENTION_DAYS días."""
    try:
        response = client.list_objects_v2(Bucket=bucket, Prefix="daily/")
        objects = response.get("Contents", [])

        now = datetime.now(timezone.utc)
        deleted = 0

        for obj in objects:
            age_days = (now - obj["LastModified"]).days
            if age_days > RETENTION_DAYS:
                client.delete_object(Bucket=bucket, Key=obj["Key"])
                logger.info("[BACKUP] 🗑️  Eliminado backup antiguo: %s (%d días)", obj["Key"], age_days)
                deleted += 1

        if deleted:
            logger.info("[BACKUP] Limpieza: %d backups eliminados", deleted)
        else:
            logger.info("[BACKUP] Sin backups antiguos que eliminar")

    except Exception as e:
        logger.warning("[BACKUP] Error en limpieza de backups antiguos: %s", str(e))


# ── Integración con APScheduler ────────────────────────────────────────────────

def register_backup_scheduler(scheduler):
    """
    Registra el job de backup en el APScheduler existente.
    
    Uso en main.py o donde inicializas el scheduler:
    
        from backup_service import register_backup_scheduler
        register_backup_scheduler(scheduler)
    
    Se ejecuta diariamente a las 03:00 hora Chile (UTC-3 / UTC-4 según DST).
    Usamos UTC 06:00 para cubrir ambos casos.
    """
    scheduler.add_job(
        run_backup,
        trigger="cron",
        hour=6,        # 06:00 UTC = 03:00 Chile (hora de menor actividad)
        minute=0,
        id="daily_backup_r2",
        name="Backup diario JSON → Cloudflare R2",
        replace_existing=True,
        misfire_grace_time=3600,  # Si el server estaba caído, ejecuta hasta 1h después
    )
    logger.info("[BACKUP] ✅ Scheduler de backup registrado — diario 03:00 Chile")


# ── Ejecución manual (para testing) ───────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logger.info("Ejecutando backup manual...")
    run_backup()
    logger.info("Backup manual completado.")
