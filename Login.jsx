import { useState } from "react";
import "../styles/login.css";

export default function Login({ onLogin }) {
  const [usuario, setUsuario] = useState("");
  const [clave, setClave] = useState("");
  const [role, setRole] = useState("MEDICO"); // 👈 default médico
  const [error, setError] = useState("");

  const handleSubmit = (e) => {
    e.preventDefault();

    if (!usuario || !clave) {
      setError("Debe ingresar usuario y contraseña");
      return;
    }

    // ✅ Login MOCK: el rol lo escogemos aquí solo por ahora
    setError("");
    onLogin({ usuario, role });
  };

  return (
    <div className="login-container">
      <form className="login-card" onSubmit={handleSubmit}>
        <h1>Ficha Clínica</h1>
        <p className="subtitle">Acceso profesionales</p>

        {error && <div className="error">{error}</div>}

        <label>Usuario</label>
        <input
          type="text"
          value={usuario}
          onChange={(e) => setUsuario(e.target.value)}
          placeholder="usuario"
        />

        <label>Contraseña</label>
        <input
          type="password"
          value={clave}
          onChange={(e) => setClave(e.target.value)}
          placeholder="••••••••"
        />

        <label>Rol (temporal)</label>
        <select value={role} onChange={(e) => setRole(e.target.value)}>
          <option value="MEDICO">Médico</option>
          <option value="SECRETARIA">Secretaría</option>
          <option value="KINESIOLOGO">Kinesiólogo</option>
          <option value="ADMIN">Administrador</option>
          <option value="AUDITOR">Auditor</option>
        </select>

        <button type="submit">Ingresar</button>

        <p className="footer">© Instituto de Cirugía Articular</p>
      </form>
    </div>
  );
}
