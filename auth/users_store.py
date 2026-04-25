"""
auth/users_store.py
-------------------
Reemplaza lectura/escritura de /data/users.json → Supabase
Mantiene la misma interfaz para compatibilidad.
"""
from db.supabase_client import load_users, save_users, save_user

# Compatibilidad con módulos que importan USERS directamente
USERS = load_users()
