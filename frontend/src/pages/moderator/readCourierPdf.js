import { getDocument, GlobalWorkerOptions } from "pdfjs-dist";
import worker from "pdfjs-dist/build/pdf.worker.min.mjs?url";
import { parseCourierLabel } from "./courierLabel";
import { courierPdfText } from "./courierPdfText";

GlobalWorkerOptions.workerSrc = worker;

export default async function readCourierPdf(file, onProgress) {
  const task = getDocument({ data: await file.arrayBuffer(), isEvalSupported: false });
  try {
    const pdf = await task.promise;
    if (pdf.numPages !== 1) throw new Error("Upload a single-page PDF with one courier label.");
    const page = await pdf.getPage(1);
    const content = await page.getTextContent();
    const fields = parseCourierLabel(courierPdfText(content.items));
    if (fields.invoice && fields.cod_amount && fields.weight_kg && fields.tracking_id) return fields;

    const original = page.getViewport({ scale: 1 });
    const viewport = page.getViewport({ scale: 2200 / Math.max(original.width, original.height) });
    const canvas = document.createElement("canvas");
    canvas.width = Math.ceil(viewport.width);
    canvas.height = Math.ceil(viewport.height);
    await page.render({ canvas, viewport }).promise;
    const { default: readCourierImage } = await import("./readCourierImage");
    const fallback = await readCourierImage(canvas, onProgress);
    return Object.fromEntries(Object.entries(fields).map(([key, value]) => [key, value || fallback[key]]));
  } finally {
    await task.destroy();
  }
}
