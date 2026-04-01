import { useEffect, useState, useCallback } from "react";
import Agenda from "./Agenda";
import { useAuth } from "../../auth/AuthContext";

const API_URL = import.meta.env.VITE_API_URL;

export default function AgendaDayController({
  professional,
  date,
  role,
  onAttend,
  onNoShow,
  onCancelFinal,
  onVerPagos,
}) {
  const { session } = useAuth();
  const internalUser = session?.usuario;

  const [loading, setLoading] = useState(false);
  const [agendaData, setAgendaData] = useState(null);
  const [professionalsMap, setProfessionalsMap] = useState({});
  const [patientsCache, setPatientsCache] = useState({});

  useEffect(() => {
    async function loadProfessionals() {
      try {
        const res = await fetch(`${API_URL}/professionals`);
        if (!res.ok) return;
        const data = await res.json();
        const map = {};
        data.forEach((p) => { map[p.id] = p; });
        setProfessionalsMap(map);
      } catch {}
    }
    loadProfessionals();
  }, []);

  function getWeekdayKey(dateStr) {
    const [y, m, d] = dateStr.split("-").map(Number);
    const dt = new Date(y, m - 1, d);
    return dt.toLocaleDateString("en-US", { weekday: "long" }).toLowerCase();
  }

  function buildSlotsFromSchedule(schedule, weekdayKey) {
    const slots = {};
    if (!schedule?.days?.[weekdayKey]) return slots;
    const interval = schedule.slotMinutes;
    schedule.days[weekdayKey].forEach(({ start, end }) => {
      let minutes =
        Number(start.split(":")[0]) * 60 + Number(start.split(":")[1]);
      const endMinutes =
        Number(end.split(":")[0]) * 60 + Number(end.split(":")[1]);
      while (minutes < endMinutes) {
        const hh = String(Math.floor(minutes / 60)).padStart(2, "0");
        const mm = String(minutes % 60).padStart(2, "0");
        slots[`${hh}:${mm}`] = { status: "available" };
        minutes += interval;
      }
    });
    return slots;
  }

  async function resolvePatients(slots) {
    if (!internalUser) return;
    const ruts = Object.values(slots)
      .filter(s => (s.status === "reserved" || s.status === "confirmed") && s.rut)
      .map(s => s.rut);
    const uniqueRuts = [...new Set(ruts)];
    const missing = uniqueRuts.filter(rut => !patientsCache[rut]);
    if (missing.length === 0) return;
    try {
      const results = await Promise.all(
        missing.map(rut =>
          fetch(`${API_URL}/api/fichas/admin/${rut}`, {
            headers: { "X-Internal-User": internalUser }
          })
            .then(r => r.ok ? r.json() : null)
            .catch(() => null)
        )
      );
      setPatientsCache(prev => {
        const copy = { ...prev };
        results.forEach(p => { if (p?.rut) copy[p.rut] = p; });
        return copy;
      });
    } catch {}
  }

  const loadAgenda = useCallback(async () => {
    if (!professional || !date) return;
    const prof = professionalsMap[professional];
    if (!prof) return;

    setLoading(true);

    try {
      const [agendaRes, cajaRes] = await Promise.all([
        fetch(`${API_URL}/agenda?date=${encodeURIComponent(date)}`),
        fetch(`${API_URL}/api/caja/day?date=${encodeURIComponent(date)}&professional=${encodeURIComponent(professional)}`)
          .catch(() => null)
      ]);

      if (!agendaRes.ok) throw new Error("agenda");

      const agendaJson = await agendaRes.json();

      let cajaMap = {};
      if (cajaRes?.ok) {
        const cajaJson = await cajaRes.json();
        (cajaJson.slots || []).forEach(s => {
          cajaMap[s.time] = s;
        });
      }

      const weekdayKey   = getWeekdayKey(date);
      const baseSlots    = buildSlotsFromSchedule(prof.schedule, weekdayKey);
      const backendSlots = agendaJson.calendar?.[professional]?.slots || {};

      await resolvePatients(backendSlots);

      Object.entries(backendSlots).forEach(([time, slot]) => {
        if (role === "PUBLIC" && slot.status !== "available") {
          delete baseSlots[time];
          return;
        }

        const cajaSlot = cajaMap[time] || null;

        baseSlots[time] = {
          time,
          status:              slot.status,
          rut:                 slot.rut || null,
          patient:             slot.rut ? patientsCache[slot.rut] || null : null,
          professional,
          professionalName:    professionalsMap[professional]?.name || professional,
          cajaStatus:          cajaSlot?.arrival_status    ?? null,
          tipoCaja:            cajaSlot?.tipo_atencion     ?? null,
          pagado:              cajaSlot?.pagado            ?? false,
          monto:               cajaSlot?.monto             ?? null,
          // 🔥 campos gratuito desde agenda
          gratuito:            slot.gratuito              ?? false,
          gratuito_confirmado: slot.gratuito_confirmado   ?? false,
          gratuito_aceptado:   slot.gratuito_aceptado     ?? false,
          date,
        };
      });

      setAgendaData({
        calendar: {
          [professional]: { slots: baseSlots }
        }
      });
    } catch {
      setAgendaData(null);
    } finally {
      setLoading(false);
    }
  }, [professional, date, professionalsMap, patientsCache, internalUser]);

  useEffect(() => { loadAgenda(); }, [loadAgenda]);

  useEffect(() => {
    if (!agendaData) return;
    setAgendaData(prev => {
      if (!prev) return prev;
      const calendar = { ...prev.calendar };
      const day = calendar[professional];
      if (!day) return prev;
      const slots = { ...day.slots };
      Object.entries(slots).forEach(([time, slot]) => {
        if (
          (slot.status === "reserved" || slot.status === "confirmed") &&
          slot.rut &&
          patientsCache[slot.rut]
        ) {
          slots[time] = { ...slot, patient: patientsCache[slot.rut] };
        }
      });
      return {
        ...prev,
        calendar: { ...calendar, [professional]: { ...day, slots } }
      };
    });
  }, [patientsCache, professional]);

  function handleSelectSlot(slot) {
    if (role === "MEDICO" && slot.status === "available") return;
    onAttend?.({ ...slot, professional, date });
  }

  if (!professional || !date) {
    return <div className="agenda-placeholder">Selecciona un profesional y un día</div>;
  }

  return (
    <Agenda
      loading={loading}
      date={date}
      professionals={[{
        id:   professional,
        name: professionalsMap[professional]?.name || professional
      }]}
      agendaData={agendaData}
      onSelectSlot={handleSelectSlot}
      onVerPagos={onVerPagos}
    />
  );
}
