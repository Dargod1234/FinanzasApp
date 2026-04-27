import os

# --- ESTO DEBE IR ANTES QUE CUALQUIER OTRO IMPORT ---
os.environ["FLAGS_enable_pir_api"] = "0"
os.environ["FLAGS_enable_new_ir_api"] = "0"
os.environ["FLAGS_use_mkldnn"] = "0"
os.environ["FLAGS_eager_delete_scope"] = "True"
# Fuerza a que no intente usar optimizaciones de hardware que fallan en Docker
os.environ["FLAGS_adaptive_deterministic"] = "True" 
os.environ["PRECISION"] = "fp32"

import logging
import io
import gc
import numpy as np
from PIL import Image
from fastapi import FastAPI, File, UploadFile, HTTPException
import uvicorn

import paddle  # noqa: F401
from paddleocr import PaddleOCR

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ocr-zero-knowledge")

app = FastAPI(title="PaddleOCR Stable & Ephemeral API")

# Inicializacion del motor (singleton)
try:
    logger.info("Initializing Stable OCR Engine...")
    ocr = PaddleOCR(
        lang="es",
        use_gpu=False,
        enable_mkldnn=False,
        ocr_version='PP-OCRv4',
        show_log=False
    )
    logger.info("OCR Engine ready.")
except Exception as e:
    logger.error(f"Initialization failed: {e}")
    ocr = None


@app.post("/process")
async def process_image(file: UploadFile = File(...)):
    if ocr is None:
        raise HTTPException(status_code=503, detail="OCR engine offline")

    contents = await file.read()
    img_io = io.BytesIO(contents)

    image = None
    img_array = None

    try:
        image = Image.open(img_io).convert("RGB")
        img_array = np.array(image)

        result = ocr.ocr(img_array)
        extracted_text = [line[1][0] for line in result[0]] if result and result[0] else []

        logger.info(
            f"Ephemeral Process: Success. {len(extracted_text)} lines found and purged from RAM."
        )
        return {
            "text": "\n".join(extracted_text),
            "status": "success",
        }
    except Exception as e:
        logger.error(f"Inference error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        try:
            img_io.close()
        except Exception:
            pass
        del image
        del img_array
        del contents
        gc.collect()


@app.get("/health")
async def health_check():
    if ocr is None:
        return {"status": "unhealthy", "engine": "offline"}
    return {"status": "healthy", "engine": "PaddleOCR Stable"}


@app.get("/")
async def root():
    return {"status": "ok", "service": "ocr-engine"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
