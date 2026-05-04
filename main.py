import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# ==========================
# INICIALIZACIÓN DISCO
# ==========================
from init_data import init_disk_data
init_disk_data()

# ==========================
# SCHEDULER
# ==========================
from modules.pagos.scheduler import start_scheduler
start_scheduler()

# ==========================
# BACKUP DIARIO → R2
# ==========================
from services.backup_service import start_backup_scheduler
start_backup_scheduler()

# ==========================
# Routers
# ==========================
from auth.auth_service                              import login_router
from auth.change_password_router                    import router as change_password_router
from core.professionals_router                      import router as professionals_router
from agenda.router                                  import router as agenda_router
from agenda.summary_router                          import router as agenda_summary_router
from agenda.professionals_router                    import router as professionals_admin_router
from admin.users_router                             import router as users_admin_router
from modules.fichas.ficha_create                    import router as ficha_create_router
from modules.fichas.ficha_read                      import router as ficha_read_router
from modules.fichas.ficha_update                    import router as ficha_update_router
from api.gpt_clinical                               import router as gpt_clinical_router
from Documentospdf.pdfRouter                        import router as pdf_router
from modules.fichas.ficha_evento_create             import router as ficha_evento_create_router
from modules.fichas.ficha_evento_read               import router as ficha_evento_read_router
from modules.fichas.ficha_evento_update             import router as ficha_evento_update_router
from modules.fichas.ficha_evento_list               import router as ficha_evento_list_router
from modules.fichas.ficha_evento_resumen_clinico    import router as ficha_evento_resumen_clinico_router
from api.gpt_summary                                import router as gpt_summary_router
from api.claude_router                              import router as claude_clinical_router
from api.claude_kine_router                         import router as claude_kine_router
from modules.caja.caja_router                       import router as caja_router
from api.claude_summary                             import router as claude_summary_router
from modules.control.control_gratuito_router        import router as control_gratuito_router
from modules.contable.gastos_router                 import router as gastos_router
from modules.contable.contable_router               import router as contable_router
from modules.pagos.confirmacion_router              import router as confirmacion_router
from modules.rrhh.router                            import router as rrhh_router
from modules.fichas.prediagnostico_ia_router        import router as prediag_ia_router
from core.sedes_router                              import router as sedes_router
from core.geo_router                                import router as geo_router
from modules.control.control_sobrecupo_router       import router as sobrecupo_router
from modules.caja.caja_config_router                import router as caja_config_router
from admin.data_map_router                          import router as data_map_router

# ==========================
# APP CORE
# ==========================
app = FastAPI(title="Ficha Clínica – Backend", version="1.0")

# ==========================
# CORS
# ==========================
FRONTEND_URLS = os.getenv("FRONTEND_URLS")
if not FRONTEND_URLS:
    raise RuntimeError("Falta variable FRONTEND_URLS en Render")

allowed_origins = [url.strip() for url in FRONTEND_URLS.split(",") if url.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================
# ROUTERS
# ==========================
app.include_router(login_router)
app.include_router(change_password_router)
app.include_router(professionals_router)
app.include_router(agenda_router)
app.include_router(agenda_summary_router)
app.include_router(professionals_admin_router)
app.include_router(users_admin_router)
app.include_router(ficha_create_router)
app.include_router(ficha_read_router)
app.include_router(ficha_update_router)
app.include_router(ficha_evento_create_router)
app.include_router(ficha_evento_read_router)
app.include_router(ficha_evento_update_router)
app.include_router(ficha_evento_list_router)
app.include_router(ficha_evento_resumen_clinico_router)
app.include_router(gpt_clinical_router)
app.include_router(gpt_summary_router)
app.include_router(claude_clinical_router)
app.include_router(claude_kine_router)
app.include_router(claude_summary_router)
app.include_router(caja_router)
app.include_router(pdf_router)
app.include_router(control_gratuito_router)
app.include_router(gastos_router)
app.include_router(contable_router)
app.include_router(confirmacion_router)
app.include_router(rrhh_router)
app.include_router(prediag_ia_router)
app.include_router(sedes_router)
app.include_router(geo_router)
app.include_router(sobrecupo_router)
app.include_router(caja_config_router)
app.include_router(data_map_router)

# ==========================
# HEALTHCHECK
# ==========================
@app.get("/")
def root():
    return {
        "status":  "ok",
        "service": "Ficha Clínica Backend",
        "modules": ["auth", "professionals", "agenda", "caja", "contable", "pagos"]
    }
    
