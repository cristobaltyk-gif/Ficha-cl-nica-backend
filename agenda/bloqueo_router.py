/**
 * components/agenda/BloqueoAgendaModal.jsx
 */
import { useState } from "react";

const API_URL = import.meta.env.VITE_API_URL;

export default function BloqueoAgendaModal({ open, professional, onClose, onSuccess, internalUser }) {
  const [fecha,     setFecha]     = useState("");
  const [motivo,    setMotivo]    = useState("El profesional no estará disponible este día");
  const [saving,    setSaving]    = useState(false);
  const [error,     setError]     = useState("");
  const [resultado, setResultado] = useState(null);

  if (!open) return null;

  function handleClose() {
    setFecha(""); setError(""); setResultado(null);
    setMotivo("El profesional no estará disponible este día");
    onClose();
  }

  async function desbloquearDia() {
    if (!fecha) { setError("Selecciona una fecha"); return; }
    setSaving(true); setError("");
    try {
      const res = await fetch(`${API_URL}/agenda/bloquear-dia/${professional}/${fecha}`, {
        method: "DELETE",
        headers: { "X-Internal-User": internalUser || "" },
      });
      if (!res.ok) throw new Error((await res.json()).detail || "Error al desbloquear");
      setResultado({ desbloqueado: true });
      onSuccess?.();
    } catch (e) { setError(e.message); }
    finally { setSaving(false); }
  }

  async function bloquearDia() {
    if (!fecha) { setError("Selecciona una fecha"); return; }
    setSaving(true); setError("");
    try {
      const res = await fetch(`${API_URL}/agenda/bloquear-dia`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-Internal-User": internalUser || "" },
        body: JSON.stringify({ date: fecha, professional, motivo })
      });
      if (!res.ok) throw new Error((await res.json()).detail || "Error al bloquear");
      setResultado(await res.json());
      onSuccess?.();
    } catch (e) { setError(e.message); }
    finally { setSaving(false); }
  }

  async function desbloquearDia() {
    if (!fecha) { setError("Selecciona una fecha"); return; }
    setSaving(true); setError("");
    try {
      const res = await fetch(`${API_URL}/agenda/bloquear-dia/${professional}/${fecha}`, {
        method: "DELETE",
        headers: { "X-Internal-User": internalUser || "" },
      });
      if (!res.ok) throw new Error((await res.json()).detail || "Error al desbloquear");
      setResultado({ ok: true, desbloqueado: true });
      onSuccess?.();
    } catch (e) { setError(e.message); }
    finally { setSaving(false); }
  }

  return (
    <div style={{
      position:"fixed", inset:0, background:"rgba(15,23,42,0.5)",
      display:"flex", alignItems:"flex-end", justifyContent:"center", zIndex:400
    }} onClick={e => e.target === e.currentTarget && handleClose()}>

      <div style={{
        background:"#fff", borderRadius:"20px 20px 0 0",
        width:"100%", maxWidth:480,
        boxShadow:"0 -8px 40px rgba(0,0,0,0.15)",
        fontFamily:"'DM Sans',system-ui,sans-serif"
      }}>

        {/* Header */}
        <div style={{
          padding:"20px 20px 16px", borderBottom:"1px solid #f1f5f9",
          display:"flex", alignItems:"center", justifyContent:"space-between"
        }}>
          <div>
            <p style={{margin:0, fontSize:16, fontWeight:700, color:"#0f172a"}}>Bloqueo de agenda</p>
            <p style={{margin:0, fontSize:12, color:"#94a3b8"}}>{professional}</p>
          </div>
          <button onClick={handleClose} style={{background:"none",border:"none",cursor:"pointer",color:"#94a3b8",padding:4}}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
            </svg>
          </button>
        </div>

        <div style={{padding:"16px 20px 32px"}}>

          {error && (
            <div style={{background:"#fef2f2",border:"1px solid #fecaca",color:"#dc2626",
              padding:"10px 12px",borderRadius:8,fontSize:13,marginBottom:12}}>{error}</div>
          )}

          {resultado && (
            <div style={{background:"#f0fdf4",border:"1px solid #86efac",color:"#166534",
              padding:"14px",borderRadius:8,fontSize:13,marginBottom:16}}>
              {resultado.desbloqueado
                ? <p style={{margin:0,fontWeight:700}}>🔓 Día desbloqueado correctamente</p>
                : <>
                    <p style={{margin:"0 0 4px",fontWeight:700}}>🔒 Día bloqueado correctamente</p>
                    <p style={{margin:0}}>{resultado.notificados} paciente{resultado.notificados !== 1 ? "s" : ""} notificado{resultado.notificados !== 1 ? "s" : ""}</p>
                  </>
              }
            </div>
          )}

          {/* Fecha */}
          <div style={{marginBottom:14}}>
            <p style={{fontSize:10,fontWeight:700,textTransform:"uppercase",
              letterSpacing:"0.12em",color:"#94a3b8",margin:"0 0 6px"}}>Fecha</p>
            <input type="date" value={fecha} onChange={e => { setFecha(e.target.value); setResultado(null); }}
              style={{width:"100%",padding:"10px 12px",border:"1px solid #e2e8f0",
                borderRadius:8,fontSize:14,fontFamily:"inherit",outline:"none",boxSizing:"border-box"}}/>
          </div>

          {/* Motivo */}
          <div style={{marginBottom:20}}>
            <p style={{fontSize:10,fontWeight:700,textTransform:"uppercase",
              letterSpacing:"0.12em",color:"#94a3b8",margin:"0 0 6px"}}>
              Motivo (se enviará a los pacientes)
            </p>
            <input value={motivo} onChange={e => setMotivo(e.target.value)}
              style={{width:"100%",padding:"10px 12px",border:"1px solid #e2e8f0",
                borderRadius:8,fontSize:13,fontFamily:"inherit",outline:"none",boxSizing:"border-box"}}/>
          </div>

          {/* Botones */}
          <div style={{display:"flex",gap:10}}>
            <button onClick={desbloquearDia} disabled={saving || !fecha} style={{
              flex:1, padding:"12px", background:"#f0fdf4", color:"#16a34a",
              border:"1px solid #86efac", borderRadius:8, fontSize:13,
              fontWeight:700, cursor: !fecha ? "not-allowed" : "pointer",
              opacity: !fecha ? 0.5 : 1
            }}>
              🔓 Desbloquear
            </button>
            <button onClick={bloquearDia} disabled={saving || !fecha} style={{
              flex:1, padding:"12px", background:"#dc2626", color:"#fff",
              border:"none", borderRadius:8, fontSize:13,
              fontWeight:700, cursor: !fecha ? "not-allowed" : "pointer",
              opacity: saving || !fecha ? 0.6 : 1
            }}>
              {saving ? "Procesando…" : "🔒 Bloquear y notificar"}
            </button>
          </div>

        </div>
      </div>
    </div>
  );
}
