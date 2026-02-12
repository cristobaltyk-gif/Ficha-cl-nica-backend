// ordenQuirurgica.js
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";
import { getProfessionalData } from "./professionalResolver.js";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

export function generarOrdenQuirurgica(doc, datos) {
  const {
    nombre,
    rut,
    edad,
    diagnostico,
    codigoCirugia,
    tipoCirugia,
    modalidad, // "PAD", "Institucional", "Convencional", "Otros"
    equipoMedico,
    insumos,
    professional
  } = datos || {};

  const medico = getProfessionalData(professional);
  if (!medico) {
    throw new Error("Profesional no encontrado");
  }

  const fechaActual = new Date().toLocaleDateString("es-CL");

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
    .text("ORDEN MÉDICA DE INTERVENCIÓN QUIRÚRGICA", 150, undefined, {
      underline: true,
    });

  doc.moveDown(2);

  doc.font("Helvetica").fontSize(11)
    .text("IMPORTANTE:", { continued: true })
    .font("Helvetica")
    .text(" Se tomará contacto a la brevedad para confirmar o reagendar fecha de intervención desde la Unidad de Planificación Quirúrgica.");

  doc.moveDown(1.5);
  doc.text(`Fecha actual: ${fechaActual}`);

  doc.moveDown(2);

  /* ================= DATOS PACIENTE ================= */
  doc.font("Helvetica-Bold").fontSize(14).text("DATOS DEL PACIENTE");
  doc.moveDown(1);

  doc.font("Helvetica").fontSize(12);
  doc.text(`Nombre: ${nombre ?? ""}`);
  doc.text(`RUT: ${rut ?? ""}`);
  doc.text(`Edad: ${edad ?? ""}`);
  doc.text(`Diagnóstico: ${diagnostico ?? ""}`);
  doc.text(`Código Cirugía: ${codigoCirugia ?? ""}`);

  doc.moveDown(2);

  /* ================= DATOS INTERVENCIÓN ================= */
  doc.font("Helvetica-Bold").fontSize(14).text("DATOS DE LA INTERVENCIÓN");
  doc.moveDown(1);

  doc.font("Helvetica").fontSize(12);
  doc.text(`Tipo de Cirugía: ${tipoCirugia ?? ""}`);
  doc.moveDown(0.5);

  doc.text(`Modalidad: ${modalidad ?? ""}`);

  doc.moveDown(1);

  /* ================= EQUIPO / INSUMOS ================= */
  if (equipoMedico) {
    doc.font("Helvetica-Bold").text("Equipo Médico:");
    doc.moveDown(0.5);
    doc.font("Helvetica").text(equipoMedico);
    doc.moveDown(1);
  }

  if (insumos) {
    doc.font("Helvetica-Bold").text("Insumos / OTS:");
    doc.moveDown(0.5);
    doc.font("Helvetica").text(insumos);
  }

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

  doc.text("Firma Médico Tratante", marginL, baseY + 18, {
    align: "center",
    width: pageW - marginL - marginR,
  });

  // Firma
  try {
    const firmaPath = path.join(__dirname, "assets", medico.firma);
    if (fs.existsSync(firmaPath)) {
      const firmaW = 250;
      const firmaX = (pageW - firmaW) / 2;
      const firmaY = baseY - 45;
      doc.image(firmaPath, firmaX, firmaY, { width: firmaW });
    }
  } catch {}

  // Timbre
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
}
