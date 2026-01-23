import "../../styles/login.css";
import { useState } from "react";

export default function Login() {
  const [user, setUser] = useState("");
  const [pass, setPass] = useState("");

  const handleLogin = () => {
    console.log("login:", user, pass);
    // después conectamos backend
  };

  return (
    <div className="login-container">
      <div className="login-box">
        <h1>Ingreso Clínica</h1>

        <input
          type="text"
          placeholder="Usuario"
          value={user}
          onChange={(e) => setUser(e.target.value)}
        />

        <input
          type="password"
          placeholder="Clave"
          value={pass}
          onChange={(e) => setPass(e.target.value)}
        />

        <button onClick={handleLogin}>Ingresar</button>
      </div>
    </div>
  );
}
