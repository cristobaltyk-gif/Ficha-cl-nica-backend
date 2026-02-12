import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const professionalsPath = path.join(__dirname, "professionals.json");

export function getProfessionalData(professionalId) {
  try {
    const raw = fs.readFileSync(professionalsPath);
    const data = JSON.parse(raw);
    return data[professionalId] || null;
  } catch {
    return null;
  }
}
