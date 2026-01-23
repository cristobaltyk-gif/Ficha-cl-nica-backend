import TopBar from "../components/TopBar";
import Card from "../components/Card";
import "../styles/medico.css";

export default function Medico({ session, onLogout }) {
  return (
    <div className="medico-container">
      <TopBar role={`Médico • ${session.usuario}`} />

      <div className="medico-actions">
        <button className="logout" onClick={onLogout}>Cerrar sesión</button>
      </div>

      <div className="content">
        <Card title="Paciente">
          <button>🔎 Buscar paciente</button>
          <button>📂 Abrir ficha</button>
        </Card>

        <Card title="Atención clínica">
          <button>🩺 Nueva atención</button>
          <button>📝 Evolución / Nota</button>
        </Card>

        <Card title="Documentos">
          <button>📄 Generar receta</button>
          <button>🧾 Orden de exámenes</button>
          <button>🖨️ Imprimir / Descargar PDFs</button>
        </Card>

        <Card title="Resumen">
          <div className="hint">
            Aquí después mostraremos: diagnósticos recientes, alergias, alertas, últimos exámenes, etc.
          </div>
        </Card>
      </div>
    </div>
  );
}
