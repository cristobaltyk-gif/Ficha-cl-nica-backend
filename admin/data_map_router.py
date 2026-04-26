from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from fastapi import APIRouter

router = APIRouter(prefix="/admin", tags=["Admin"])
DATA_DIR = Path("/data")


def _sizeof_fmt(num_bytes: int) -> str:
    for unit in ["B", "KB", "MB", "GB"]:
        if num_bytes < 1024:
            return f"{num_bytes:.1f} {unit}"
        num_bytes /= 1024
    return f"{num_bytes:.1f} TB"


def _sample_keys(obj: Any, max_depth: int = 2) -> Any:
    if max_depth == 0:
        return "..."
    if isinstance(obj, dict):
        return {k: _sample_keys(v, max_depth - 1) for k, v in list(obj.items())[:5]}
    if isinstance(obj, list):
        if not obj:
            return []
        return [_sample_keys(obj[0], max_depth - 1), f"... ({len(obj)} items)"]
    return type(obj).__name__


def _analyze_json(path: Path) -> Dict[str, Any]:
    try:
        size = path.stat().st_size
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return {"size": _sizeof_fmt(size), "type": "object", "count": len(data), "structure": _sample_keys(data)}
        if isinstance(data, list):
            return {"size": _sizeof_fmt(size), "type": "array", "count": len(data), "structure": _sample_keys(data)}
        return {"size": _sizeof_fmt(size), "type": "scalar", "count": 1}
    except Exception as e:
        return {"size": "?", "type": "error", "count": 0, "error": str(e)}


def _map_directory(directory: Path) -> Dict[str, Any]:
    result = {}
    if not directory.exists():
        return {"error": f"{directory} no existe"}
    for item in sorted(directory.iterdir()):
        if item.is_file() and item.suffix == ".json":
            result[item.name] = _analyze_json(item)
        elif item.is_dir():
            subdirs = [x for x in item.iterdir() if x.is_dir()]
            files   = [x for x in item.iterdir() if x.is_file()]
            if len(subdirs) > 5:
                sample = subdirs[0]
                result[item.name] = {
                    "type": "directory_records",
                    "total_records": len(subdirs),
                    "direct_files": [f.name for f in files],
                    "sample_record": sample.name,
                    "sample_structure": {
                        f.name: _analyze_json(f)
                        for f in sorted(sample.iterdir())[:5]
                        if f.suffix == ".json"
                    },
                }
            else:
                result[item.name] = _map_directory(item)
    return result


@router.get("/data-map")
def get_data_map():
    mapped = _map_directory(DATA_DIR)
    return {"data_dir": str(DATA_DIR), "structure": mapped}


@router.get("/data-map/files")
def list_all_json_files():
    files = []
    total = 0
    for f in sorted(DATA_DIR.rglob("*.json")):
        size = f.stat().st_size
        total += size
        files.append({"path": str(f.relative_to(DATA_DIR)), "size": _sizeof_fmt(size)})
    return {"total_files": len(files), "total_size": _sizeof_fmt(total), "files": files}


@router.post("/migrate")
def migrate_all():
    """
    Migra usuarios, profesionales y pacientes desde /data a PostgreSQL.
    Ejecutar una sola vez.
    """
    from db.supabase_client import _get_conn, save_user, save_profesional, create_paciente, create_evento, get_paciente

    results = {
        "usuarios": 0,
        "profesionales": 0,
        "pacientes": 0,
        "eventos": 0,
        "errores": []
    }

    # Arreglar columna password para permitir vacío
    try:
        with _get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("ALTER TABLE usuarios ALTER COLUMN password DROP NOT NULL")
                cur.execute("ALTER TABLE usuarios ALTER COLUMN password SET DEFAULT ''")
                conn.commit()
    except Exception:
        pass  # Ya fue alterada antes

    # Migrar usuarios
    users_file = DATA_DIR / "users.json"
    if users_file.exists():
        users = json.loads(users_file.read_text(encoding="utf-8"))
        for uid, data in users.items():
            try:
                save_user(uid, data)
                results["usuarios"] += 1
            except Exception as e:
                results["errores"].append(f"usuario {uid}: {str(e)}")

    # Migrar profesionales
    profs_file = DATA_DIR / "professionals.json"
    if profs_file.exists():
        profs = json.loads(profs_file.read_text(encoding="utf-8"))
        for pid, data in profs.items():
            try:
                save_profesional(pid, data)
                results["profesionales"] += 1
            except Exception as e:
                results["errores"].append(f"profesional {pid}: {str(e)}")

    # Migrar pacientes y eventos
    pacientes_dir = DATA_DIR / "pacientes"
    if pacientes_dir.exists():
        for pdir in sorted(pacientes_dir.iterdir()):
            if not pdir.is_dir():
                continue
            rut = pdir.name

            # Migrar admin.json
            admin_file = pdir / "admin.json"
            if admin_file.exists():
                try:
                    data = json.loads(admin_file.read_text(encoding="utf-8"))
                    if not get_paciente(rut):
                        create_paciente(data)
                    results["pacientes"] += 1
                except Exception as e:
                    results["errores"].append(f"paciente {rut}: {str(e)}")
                    continue

            # Migrar eventos
            eventos_dir = pdir / "eventos"
            if eventos_dir.exists():
                for ev_file in sorted(eventos_dir.glob("*.json")):
                    try:
                        evento = json.loads(ev_file.read_text(encoding="utf-8"))
                        create_evento(rut, evento)
                        results["eventos"] += 1
                    except ValueError:
                        pass  # Duplicado, ignorar
                    except Exception as e:
                        results["errores"].append(f"evento {rut}/{ev_file.name}: {str(e)}")

    return results
