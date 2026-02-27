from pydantic import BaseModel, Field
from typing import Optional


class FichaEventoCreate(BaseModel):
    rut: str = Field(..., description="RUT del paciente")
    fecha: str = Field(..., description="Fecha de la atención YYYY-MM-DD")
    hora: str = Field(..., description="Hora de la atención HH:MM")

    atencion: Optional[str] = Field("", description="Motivo / relato clínico")
    diagnostico: Optional[str] = Field("", description="Diagnóstico")
    receta: Optional[str] = Field("", description="Plan / receta médica")
    examenes: Optional[str] = Field("", description="Órdenes de exámenes")
    indicaciones: Optional[str] = Field("", description="Indicaciones generales")
    orden_kinesiologia: Optional[str] = Field("", description="Orden de kinesiología")
    indicacion_quirurgica: Optional[str] = Field("", description="Indicación quirúrgica")
