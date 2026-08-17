"""Gera um PDF 'scan' de fatura (imagem, SEM camada de texto) para testar o OCR.

Um scan real é uma imagem — pypdf não encontra texto, e o pipeline deve
reencaminhar para o Azure Document Intelligence. Uso:

    python -m auditor.make_scan_test --dest audits/ocr_test/input/faturas
"""
from __future__ import annotations

import argparse
from pathlib import Path

from fpdf import FPDF
from PIL import Image, ImageDraw, ImageFont

FONT_PATH = r"C:\Windows\Fonts\arial.ttf"


def _draw_invoice() -> Image.Image:
    """Desenha uma fatura da Papelaria Central (a 150 dpi) como imagem."""
    dpi = 150
    w, h = int(210 / 25.4 * dpi), int(297 / 25.4 * dpi)  # A4
    img = Image.new("RGB", (w, h), "white")
    draw = ImageDraw.Draw(img)
    bold = ImageFont.truetype(FONT_PATH, 26)
    normal = ImageFont.truetype(FONT_PATH, 18)
    small = ImageFont.truetype(FONT_PATH, 14)

    def text(x: int, y: int, s: str, font=normal) -> int:
        draw.text((x, y), s, fill="black", font=font)
        return y + font.size + 6

    y = 40
    y = text(40, y, "Papelaria Central Lda", bold)
    y = text(40, y, "NIF: 523456789   Rua do Comércio 3, Braga   geral@papelariacentral.pt", small)
    y += 20
    y = text(40, y, "FATURA C2026-0331", bold)
    y = text(40, y, "Data: 2026-07-14", normal)
    y = text(40, y, "Cliente: Cliente Demo Lda", normal)
    y += 16
    draw.rectangle((40, y, w - 40, y + 56), outline="black")
    y += 8
    y = text(50, y, "Descricao", bold) + 8
    y = text(50, y, "Papel A4 80g caixa 500 folhas  x10  @24.90  = 249.00", normal)
    y = text(50, y, "Tinteiro preto compativel HP  x5  @8.40   = 42.00", normal)
    y += 16
    y = text(40, y, "Subtotal 291.00", normal)
    y = text(40, y, "IVA (23%) 66.93", normal)
    y = text(40, y, "TOTAL 357.93 EUR", bold)
    y += 20
    text(40, y, "Entidade: 12345  Referencia: 678901234  (pagamento por referencia multibanco)", small)
    return img


def make_scan(dest: Path) -> Path:
    """Gera o PNG + PDF-imagem (sem texto). Devolve o caminho do PDF."""
    dest.mkdir(parents=True, exist_ok=True)
    png = dest / "_scan_tmp.png"
    pdf_path = dest / "Fatura_Scan_C2026-0331_Papelaria.pdf"

    img = _draw_invoice()
    img.save(png)

    page = FPDF(unit="mm", format="A4")
    page.add_page()
    page.image(str(png), x=10, y=10, w=190)
    page.output(str(pdf_path))

    png.unlink()  # só o PDF importa
    print(f"OK: scan gerado em {pdf_path} (sem camada de texto)")
    return pdf_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dest", default="audits/ocr_test/input/faturas")
    args = parser.parse_args()
    make_scan(Path(args.dest))
