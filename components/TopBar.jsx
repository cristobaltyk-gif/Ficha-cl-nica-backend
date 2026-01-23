export default function TopBar({ role }) {
  return (
    <div className="topbar">
      <strong>Ficha Clínica</strong>
      <span className="role">{role}</span>
    </div>
  );
}
