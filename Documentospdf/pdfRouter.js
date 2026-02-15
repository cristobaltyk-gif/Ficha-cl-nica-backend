import express from "express";
import PDFDocument from "pdfkit";

import { generarRecetaMedica } from "./recetaMedica.js";
import { generarOrdenKinesiologia } from "./ordenKinesiologia.js";
import { generarOrdenQuirurgica } from "./ordenQuirurgica.js";
import { generarInformeMedico } from "./informeMedico.js";

const router = express.Router();

/* =========================================
   Helper: crear PDF seguro
========================================= */

function crearPDF(res, nombreArchivo, generar, datos) {
  const doc = new PDFDocument({ size: "A4", margin: 50 });

  res.setHeader("Content-Type", "application/pdf");
  res.setHeader(
    "Content-Disposition",
    `inline; filename=${nombreArchivo}.pdf`
  );

  doc.pipe(res);
  generar(doc, datos);
  doc.end();
}

/* =========================================
   RECETA MÉDICA
========================================= */

router.post("/receta", (req, res) => {
  try {
    const professional = req.headers["x-internal-user"];

    if (!professional)
      return res.status(401).json({ error: "Profesional no autorizado" });

    crearPDF(
      res,
      "receta_medica",
      generarRecetaMedica,
      { ...req.body, professional }
    );

  } catch (err) {
    console.error("❌ PDF RECETA ERROR:", err);
    res.status(500).json({ error: "Error generando receta" });
  }
});

/* =========================================
   INFORME MÉDICO
========================================= */

router.post("/informe", (req, res) => {
  try {
    const professional = req.headers["x-internal-user"];

    if (!professional)
      return res.status(401).json({ error: "Profesional no autorizado" });

    crearPDF(
      res,
      "informe_medico",
      generarInformeMedico,
      { ...req.body, professional }
    );

  } catch (err) {
    console.error("❌ PDF INFORME ERROR:", err);
    res.status(500).json({ error: "Error generando informe" });
  }
});

/* =========================================
   ORDEN KINESIOLOGÍA
========================================= */

router.post("/kinesiologia", (req, res) => {
  try {
    const professional = req.headers["x-internal-user"];

    if (!professional)
      return res.status(401).json({ error: "Profesional no autorizado" });

    crearPDF(
      res,
      "orden_kinesiologia",
      generarOrdenKinesiologia,
      { ...req.body, professional }
    );

  } catch (err) {
    console.error("❌ PDF KINESIO ERROR:", err);
    res.status(500).json({ error: "Error generando orden kinésica" });
  }
});

/* =========================================
   ORDEN QUIRÚRGICA
========================================= */

router.post("/quirurgica", (req, res) => {
  try {
    const professional = req.headers["x-internal-user"];

    if (!professional)
      return res.status(401).json({ error: "Profesional no autorizado" });

    crearPDF(
      res,
      "orden_quirurgica",
      generarOrdenQuirurgica,
      { ...req.body, professional }
    );

  } catch (err) {
    console.error("❌ PDF QUIRÚRGICA ERROR:", err);
    res.status(500).json({ error: "Error generando orden quirúrgica" });
  }
});

export default router;
