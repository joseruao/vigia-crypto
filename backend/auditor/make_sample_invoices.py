"""Gera faturas de exemplo + extrato CSV para demonstração do auditor.

Uso:
    python -m auditor_demo_assets  (na pasta scripts/)
ou:
    python scripts/make_sample_invoices.py --dest audits/cliente_demo/input
"""
from __future__ import annotations

import argparse
from pathlib import Path

from fpdf import FPDF


class InvoicePDF(FPDF):
    def header(self) -> None:  # noqa: D102
        self.set_font("Helvetica", "B", 14)
        self.cell(0, 10, self.empresa, new_x="LMARGIN", new_y="NEXT")
        self.set_font("Helvetica", "", 9)
        self.cell(0, 5, f"NIF: {self.nif}", new_x="LMARGIN", new_y="NEXT")
        self.cell(0, 5, self.morada, new_x="LMARGIN", new_y="NEXT")
        self.ln(4)
        self.set_draw_color(120)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(4)

    def invoice_body(
        self,
        numero: str,
        data: str,
        cliente: str,
        linhas: list[tuple[str, float, float]],
        vat_rate: float = 0.23,
    ) -> None:
        self.set_font("Helvetica", "B", 12)
        self.cell(0, 8, f"FATURA {numero}", new_x="LMARGIN", new_y="NEXT")
        self.set_font("Helvetica", "", 10)
        self.cell(0, 6, f"Data: {data}", new_x="LMARGIN", new_y="NEXT")
        self.cell(0, 6, f"Cliente: {cliente}", new_x="LMARGIN", new_y="NEXT")
        self.ln(4)
        self.set_font("Helvetica", "B", 10)
        self.cell(90, 7, "Descrição", border=1)
        self.cell(25, 7, "Qt.", border=1, align="R")
        self.cell(35, 7, "Preço unit.", border=1, align="R")
        self.cell(35, 7, "Total", border=1, align="R", new_x="LMARGIN", new_y="NEXT")
        self.set_font("Helvetica", "", 10)
        subtotal = 0.0
        for desc, qty, price in linhas:
            total = qty * price
            subtotal += total
            self.cell(90, 7, desc[:60], border=1)
            self.cell(25, 7, f"{qty:g}", border=1, align="R")
            self.cell(35, 7, f"{price:.2f}", border=1, align="R")
            self.cell(35, 7, f"{total:.2f}", border=1, align="R", new_x="LMARGIN", new_y="NEXT")
        vat = subtotal * vat_rate
        self.ln(2)
        self.set_font("Helvetica", "", 10)
        self.cell(150, 7, "Subtotal", align="R")
        self.cell(35, 7, f"{subtotal:.2f}", align="R", new_x="LMARGIN", new_y="NEXT")
        self.cell(150, 7, f"IVA ({vat_rate:.0%})", align="R")
        self.cell(35, 7, f"{vat:.2f}", align="R", new_x="LMARGIN", new_y="NEXT")
        self.set_font("Helvetica", "B", 11)
        self.cell(150, 8, "TOTAL", align="R")
        self.cell(35, 8, f"{subtotal + vat:.2f} EUR", align="R", new_x="LMARGIN", new_y="NEXT")
        self.ln(4)
        self.set_font("Helvetica", "", 9)
        self.cell(0, 6, "Entidade: 12345  Referência: 678901234  (pagamento por referência multibanco)", new_x="LMARGIN", new_y="NEXT")


def make_invoice(path: Path, empresa: str, nif: str, morada: str, numero: str, data: str, cliente: str, linhas: list[tuple[str, float, float]]) -> None:
    pdf = InvoicePDF()
    pdf.empresa, pdf.nif, pdf.morada = empresa, nif, morada
    pdf.add_page()
    pdf.invoice_body(numero, data, cliente, linhas)
    pdf.output(str(path))


def make_samples(dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    faturas = dest / "faturas"
    faturas.mkdir(parents=True, exist_ok=True)

    # 1. Fatura normal
    make_invoice(
        faturas / "Fatura_A2026-0114_Energia.pdf",
        empresa="Luz & Energia SA", nif="501234567", morada="Av. da Luz 42, Lisboa",
        numero="A2026-0114", data="2026-07-01", cliente="Cliente Demo Lda",
        linhas=[("Energia elétrica - julho 2026", 1, 850.00), ("Potência contratada", 1, 194.15)],
    )
    # 2. DUPLICADA: mesmo número, mesmo fornecedor, mesmo total
    make_invoice(
        faturas / "Fatura_A2026-0114_Duplicada.pdf",
        empresa="Luz & Energia SA", nif="501234567", morada="Av. da Luz 42, Lisboa",
        numero="A2026-0114", data="2026-07-03", cliente="Cliente Demo Lda",
        linhas=[("Energia elétrica - julho 2026", 1, 850.00), ("Potência contratada", 1, 194.15)],
    )
    # 3. Fatura normal de outro fornecedor
    make_invoice(
        faturas / "Fatura_B2027-0092_Manutencao.pdf",
        empresa="Manutenção Técnica Lda", nif="512345678", morada="Rua das Oficinas 7, Porto",
        numero="B2027-0092", data="2026-07-10", cliente="Cliente Demo Lda",
        linhas=[("Manutenção preventiva equipamentos", 1, 764.23)],
    )

    # 4. Extrato bancário (CSV) — 2 pagamentos correspondem, 1 fica sem fatura
    extrato = dest / "extratos"
    extrato.mkdir(parents=True, exist_ok=True)
    (extrato / "extrato_julho.csv").write_text(
        "data;descricao;montante\n"
        "2026-07-10;Pagamento fatura A2026-0114 Luz & Energia;-1284,30\n"
        "2026-07-12;Pagamento fatura B2027-0092 Manutenção;-764,23\n"
        "2026-07-15;Transferência Gabriel Lda;-3500,00\n",
        encoding="utf-8",
    )
    print(f"OK: 3 faturas + 1 extrato gerados em {dest}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dest", default="audits/cliente_demo/input", help="Pasta de destino (input do workspace)")
    args = parser.parse_args()
    make_samples(Path(args.dest))
