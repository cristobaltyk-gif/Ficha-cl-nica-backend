// informeMedico.js
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";
import { getProfessionalData } from "./professionalResolver.js";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

export function generarInformeMedico(doc, datos) {
  const {
    nombre,
    edad,
    rut,
    motivoConsulta,
    antecedentes,
    examenFisico,
    estudios,
    impresionDiagnostica,
    plan,
    professional // ← viene del login
  } = datos || {};

  const medico = getProfessionalData(professional);

  if (!medico) {
    throw new Error("Profesional no encontrado");
  }

  /* ================= ENCABEZADO ================= */
  try {
    const logoPath = path.join(__dirname, "assets", "ica.jpg");
    if (fs.existsSync(logoPath)) {
      doc.image(logoPath, 50, 40, { width: 120 });
    }
  } catch {}

  doc.moveDown(1.5);
  doc.font("Helvetica-Bold").fontSize(18)
    .text("INSTITUTO DE CIRUGÍA ARTICULAR", 180, 50);

  doc.moveDown(1.5);
  doc.fontSize(16)
    .text("INFORME MÉDICO", 180, undefined, {
      underline: true,
    });

  doc.moveDown(4);
  doc.x = doc.page.margins.left;

  /* ================= DATOS PACIENTE ================= */
  doc.font("Helvetica").fontSize(13);
  doc.text(`Nombre: ${nombre ?? ""}`);
  doc.moveDown(0.8);
  doc.text(`Edad: ${edad ?? ""}`);
  doc.moveDown(0.5);
  doc.text(`RUT: ${rut ?? ""}`);
  doc.moveDown(1.5);

  /* ================= CONTENIDO CLÍNICO ================= */

  function seccion(titulo, contenido) {
    if (contenido && contenido.trim()) {
      doc.moveDown(1);
      doc.font("Helvetica-Bold").fontSize(14).text(titulo);
      doc.moveDown(0.5);
      doc.font("Helvetica").fontSize(12).text(contenido.trim(), {
        align: "justify"
      });
    }
  }

  seccion("Motivo de Consulta", motivoConsulta);
  seccion("Antecedentes Relevantes", antecedentes);
  seccion("Examen Físico", examenFisico);
  seccion("Estudios Complementarios", estudios);
  seccion("Impresión Diagnóstica", impresionDiagnostica);
  seccion("Plan y Conducta", plan);

  /* ================= FIRMA DINÁMICA ================= */
  const pageW = doc.page.width;
  const pageH = doc.page.height;
  const marginL = doc.page.margins.left || 50;
  const marginR = doc.page.margins.right || 50;
  const baseY = pageH - 170;

  doc.font("Helvetica").fontSize(12);
  doc.text("_________________________", marginL, baseY, {
    align: "center",
    width: pageW - marginL - marginR,
  });
  doc.text("Firma y Timbre Médico", marginL, baseY + 18, {
    align: "center",
    width: pageW - marginL - marginR,
  });

  // Firma dinámica
  try {
    const firmaPath = path.join(__dirname, "assets", medico.firma);
    if (fs.existsSync(firmaPath)) {
      const firmaW = 250;
      const firmaX = (pageW - firmaW) / 2;
      const firmaY = baseY - 45;
      doc.image(firmaPath, firmaX, firmaY, { width: firmaW });
    }
  } catch {}

  // Timbre dinámico
  try {
    const timbrePath = path.join(__dirname, "assets", medico.timbre);
    if (fs.existsSync(timbrePath)) {
      const firmaW = 250;
      const firmaX = (pageW - firmaW) / 2;
      const timbreW = 110;
      const timbreX = firmaX + firmaW;
      const timbreY = baseY - 65;

      doc.save();
      doc.rotate(20, {
        origin: [timbreX + timbreW / 2, timbreY + timbreW / 2],
      });
      doc.image(timbrePath, timbreX, timbreY, { width: timbreW });
      doc.restore();
    }
  } catch {}

  /* ================= PIE DINÁMICO ================= */
  doc.font("Helvetica").fontSize(12);
  doc.text(medico.nombre, marginL, baseY + 52, {
    align: "center",
    width: pageW - marginL - marginR,
  });
  doc.text(`RUT: ${medico.rut}`, {
    align: "center",
    width: pageW - marginL - marginR,
  });
  doc.text(medico.especialidad, {
    align: "center",
    width: pageW - marginL - marginR,
  });
  doc.text("INSTITUTO DE CIRUGÍA ARTICULAR", {
    align: "center",
    width: pageW - marginL - marginR,
  });
}
