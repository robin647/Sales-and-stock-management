import { createWorker, OEM, PSM } from "tesseract.js";
import workerPath from "tesseract.js/dist/worker.min.js?url";
import corePath from "tesseract.js-core/tesseract-core-lstm.wasm.js?url";
import englishModel from "@tesseract.js-data/eng/4.0.0_best_int/eng.traineddata.gz?url";
import { parseCourierLabel } from "./courierLabel";

export default async function readCourierImage(file, onProgress) {
  let worker;
  let rejectInitialization;
  const initializationError = new Promise((_, reject) => { rejectInitialization = reject; });
  try {
    worker = await Promise.race([
      createWorker("eng", OEM.LSTM_ONLY, {
        workerPath,
        workerBlobURL: false,
        corePath: new URL(corePath, window.location.origin).href,
        langPath: new URL(".", new URL(englishModel, window.location.origin)).href,
        errorHandler: rejectInitialization,
        logger: ({ status, progress }) => {
          if (status === "recognizing text") onProgress(Math.round(progress * 100));
        },
      }),
      initializationError,
    ]);
    await worker.setParameters({ tessedit_pageseg_mode: PSM.AUTO });
    const { data: { text } } = await worker.recognize(file);
    const fields = parseCourierLabel(text);
    if (fields.invoice && fields.cod_amount && fields.weight_kg) return fields;

    await worker.setParameters({ tessedit_pageseg_mode: PSM.SPARSE_TEXT });
    const { data: { text: sparseText } } = await worker.recognize(file);
    const fallback = parseCourierLabel(sparseText);
    return Object.fromEntries(Object.entries(fields).map(([key, value]) => [key, value || fallback[key]]));
  } finally {
    await worker?.terminate();
  }
}
