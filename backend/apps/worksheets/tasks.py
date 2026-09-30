import io
import logging

import pypdfium2 as pdfium
from celery import shared_task
from PIL import Image

from apps.common import storage
from apps.worksheets.models import Worksheet, WorksheetPage

logger = logging.getLogger(__name__)

_RENDER_SCALE = 2.0  # ~144 dpi — readable for students, small enough to ship


@shared_task
def rasterize_pdf(worksheet_id: int, pdf_key: str) -> int:
    """
    Turn an uploaded PDF object into one PNG WorksheetPage per PDF page.

    Returns the number of pages created.
    """
    worksheet = Worksheet.objects.get(id=worksheet_id)
    pdf_bytes = storage.get_bytes(pdf_key)
    pdf = pdfium.PdfDocument(pdf_bytes)

    existing = WorksheetPage.objects.filter(worksheet=worksheet)
    last_page = existing.last()
    next_order = (last_page.order + 1) if last_page else 0
    created = 0
    for i, page in enumerate(pdf):
        bitmap = page.render(scale=_RENDER_SCALE)
        pil_image: Image.Image = bitmap.to_pil()

        buf = io.BytesIO()
        pil_image.save(buf, format="PNG", optimize=True)

        key = f"worksheets/{worksheet_id}/pages/{next_order + i:03d}.png"
        storage.put_bytes(key, buf.getvalue(), "image/png")

        WorksheetPage.objects.create(
            worksheet=worksheet,
            order=next_order + i,
            image_key=key,
            width=pil_image.width,
            height=pil_image.height,
        )
        created += 1

    logger.info("rasterize_pdf: worksheet %s → %d pages", worksheet_id, created)
    return created
