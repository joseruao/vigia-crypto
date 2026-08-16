"""Gera faturas de exemplo + extrato CSV para demonstração do auditor.

Uso:
    python -m auditor.make_sample_invoices --dest audits/cliente_demo/input

Demo inclui: fatura duplicada, pagamento sem fatura, fornecedor alternativo
mais barato (papel A4) e vendas com margem baixa — para veres todas as regras.
"""
from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from fpdf import FPDF


class InvoicePDF(FPDF):
    def header(self) -> None:  # noqa: D102
        self.set_font("Helvetica", "B", 14)
        self.cell(0, 10, self.empresa, new_x="LMARGIN", new_y="NEXT")
        self.set_font("Helvetica", "", 9)
        self.cell(0, 5, f"NIF: {self.nif}   {self.morada}   {self.email}", new_x="LMARGIN", new_y="NEXT")
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


def make_invoice(
    path: Path,
    empresa: str,
    nif: str,
    morada: str,
    email: str,
    numero: str,
    data: str,
    cliente: str,
    linhas: list[tuple[str, float, float]],
) -> None:
    pdf = InvoicePDF()
    pdf.empresa, pdf.nif, pdf.morada, pdf.email = empresa, nif, morada, email
    pdf.add_page()
    pdf.invoice_body(numero, data, cliente, linhas)
    pdf.output(str(path))


def make_samples(dest: Path) -> None:
    if dest.exists():
        shutil.rmtree(dest)  # regenera sempre do zero (é material de demo)
    faturas = dest / "faturas"
    faturas.mkdir(parents=True, exist_ok=True)
    vendas = dest / "vendas"
    vendas.mkdir(parents=True, exist_ok=True)
    extratos = dest / "extratos"
    extratos.mkdir(parents=True, exist_ok=True)

    # --- COMPRAS (Luz & Energia tem sequência 0113, 0113(dup), 0114, 0116 → falta a 0115) ---
    # 1. Fatura normal (energia, junho)
    make_invoice(
        faturas / "Fatura_A2026-0113_Energia.pdf",
        empresa="Luz & Energia SA", nif="501234567", morada="Av. da Luz 42, Lisboa",
        email="info@luzenenergia.pt",
        numero="A2026-0113", data="2026-06-01", cliente="Cliente Demo Lda",
        linhas=[("Energia elétrica - junho 2026", 1, 820.00), ("Potência contratada", 1, 194.15)],
    )
    # 2. DUPLICADA: mesmo número, mesmo fornecedor, mesmo total
    make_invoice(
        faturas / "Fatura_A2026-0113_Duplicada.pdf",
        empresa="Luz & Energia SA", nif="501234567", morada="Av. da Luz 42, Lisboa",
        email="info@luzenenergia.pt",
        numero="A2026-0113", data="2026-06-03", cliente="Cliente Demo Lda",
        linhas=[("Energia elétrica - junho 2026", 1, 820.00), ("Potência contratada", 1, 194.15)],
    )
    # 3. Fatura normal (energia, julho — a que aparece paga no extrato)
    make_invoice(
        faturas / "Fatura_A2026-0114_Energia.pdf",
        empresa="Luz & Energia SA", nif="501234567", morada="Av. da Luz 42, Lisboa",
        email="info@luzenenergia.pt",
        numero="A2026-0114", data="2026-07-01", cliente="Cliente Demo Lda",
        linhas=[("Energia elétrica - julho 2026", 1, 850.00), ("Potência contratada", 1, 194.15)],
    )
    # 4. Fatura normal (energia, agosto) — cria o buraco 0115
    make_invoice(
        faturas / "Fatura_A2026-0116_Energia.pdf",
        empresa="Luz & Energia SA", nif="501234567", morada="Av. da Luz 42, Lisboa",
        email="info@luzenenergia.pt",
        numero="A2026-0116", data="2026-08-01", cliente="Cliente Demo Lda",
        linhas=[("Energia elétrica - agosto 2026", 1, 880.00), ("Potência contratada", 1, 194.15)],
    )
    # 3. Fatura normal de outro fornecedor
    make_invoice(
        faturas / "Fatura_B2027-0092_Manutencao.pdf",
        empresa="Manutenção Técnica Lda", nif="512345678", morada="Rua das Oficinas 7, Porto",
        email="geral@manutencaotecnica.pt",
        numero="B2027-0092", data="2026-07-10", cliente="Cliente Demo Lda",
        linhas=[("Manutenção preventiva equipamentos", 1, 764.23)],
    )
    # 4. Fornecedor CARO de papel (para o comparador achar)
    make_invoice(
        faturas / "Fatura_C2026-0331_Papelaria.pdf",
        empresa="Papelaria Central Lda", nif="523456789", morada="Rua do Comércio 3, Braga",
        email="geral@papelariacentral.pt",
        numero="C2026-0331", data="2026-07-14", cliente="Cliente Demo Lda",
        linhas=[("Papel A4 80g caixa 500 folhas", 10, 24.90), ("Tinteiro preto compatível HP", 5, 8.40)],
    )
    # 5. Fornecedor MAIS BARATO do mesmo papel (a demo encontra-o!)
    make_invoice(
        faturas / "Fatura_D2026-0187_OfficeMax.pdf",
        empresa="OfficeMax Portugal", nif="534567890", morada="Zona Industrial 12, Porto",
        email="vendas@officemax.pt",
        numero="D2026-0187", data="2026-07-15", cliente="Cliente Demo Lda",
        linhas=[("Papel A4 80g caixa 500 folhas", 5, 21.50)],
    )

    # --- VENDAS ---
    # 6. Venda com margem baixa (vende papel perto do preço do fornecedor caro)
    make_invoice(
        vendas / "Fatura_V2026-001_CafeCentral.pdf",
        empresa="Cliente Demo Lda", nif="545678901", morada="Sede Cliente Demo, Braga",
        email="compras@clientedemo.pt",
        numero="V2026-001", data="2026-07-18", cliente="Café Central Lda",
        linhas=[("Papel A4 80g caixa 500 folhas", 4, 24.00)],
    )
    # 7. Venda normal (sem correspondência de compra -> sem achado)
    make_invoice(
        vendas / "Fatura_V2026-002_CafeCentral.pdf",
        empresa="Cliente Demo Lda", nif="545678901", morada="Sede Cliente Demo, Braga",
        email="compras@clientedemo.pt",
        numero="V2026-002", data="2026-07-20", cliente="Café Central Lda",
        linhas=[("Serviço de impressão digital", 1, 180.00)],
    )

    # --- EXTRATO ---
    (extratos / "extrato_julho.csv").write_text(
        "data;descricao;montante\n"
        "2026-07-10;Pagamento fatura A2026-0114 Luz & Energia;-1284,30\n"
        "2026-07-12;Pagamento fatura B2027-0092 Manutenção;-940,00\n"
        "2026-07-15;Transferência Gabriel Lda;-3500,00\n"
        "2026-07-20;Pagamento fatura A2026-0114 Luz & Energia;-1284,30\n",
        encoding="utf-8",
    )
    print(f"OK: 6 faturas compras + 2 vendas + 1 extrato gerados em {dest}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dest", default="audits/cliente_demo/input", help="Pasta de destino (input do workspace)")
    args = parser.parse_args()
    make_samples(Path(args.dest))
