import TopBar from "../components/TopBar";
import Card from "../components/Card";
import "../styles/secretaria.css";

export default function Secretaria() {
  return (
    <div className="secretaria-container">
      <TopBar role="Secretaría" />

      <div className="content">
        <Card title="Pacientes">
          <button>➕ Registrar nuevo paciente</button>
          <button>📋 Ver listado de pacientes</button>
        </Card>

        <Card title="Atenciones">
          <button>🗓️ Crear nueva atención</button>
          <button>📆 Agenda del día</button>
        </Card>

        <Card title="Documentos">
          <button>📄 Órdenes médicas</button>
          <button>🖨️ Imprimir documentos</button>
        </Card>
      </div>
    </div>
  );
}
