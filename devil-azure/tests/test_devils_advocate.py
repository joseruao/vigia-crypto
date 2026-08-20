"""Suíte laboral do Devil's Advocate — funções puras, sem rede.

Correr:  .venv/Scripts/python.exe -m pytest tests -q   (a partir de devil-azure/)
"""
import json

from Api.services.devils_advocate import (
    DevilsAdvocateReport,
    _all_report_points,
    _area_profile,
    _extract_legal_references,
    _format_legal_code,
    _legal_ref_key,
    _normalize_model_payload,
    _pre_filing_labor_block,
    _pre_filing_schema_hint,
    _pre_filing_user_prompt,
    _reference_links_from_points,
    _schema_hint,
    _user_prompt,
)


# ── Extração de referências legais laborais ─────────────────────────────

def test_extract_labor_legal_references():
    text = "O trabalhador foi despedido com fundamento no artigo 351.º do Código do Trabalho."
    refs = _extract_legal_references(text)
    assert any("Código do Trabalho, artigo 351.º" in r for r in refs)


def test_extract_labor_legal_references_lat_ltfp_rct():
    text = (
        "Acidente coberto pelo artigo 21.º da LAT; "
        "vínculo regido pelo artigo 45.º da LTFP; "
        "o artigo 3.º do RCT aplica-se."
    )
    refs = _extract_legal_references(text)
    joined = " | ".join(refs)
    assert "LAT, artigo 21.º" in joined
    assert "LTFP, artigo 45.º" in joined
    assert "RCT, artigo 3.º" in joined


def test_extract_labor_full_names():
    text = (
        "Caducidade nos termos do artigo 386.º do Código do Trabalho; "
        "recurso ao abrigo do artigo 98.º do Código de Processo do Trabalho."
    )
    refs = _extract_legal_references(text)
    joined = " | ".join(refs)
    assert "Código do Trabalho, artigo 386.º" in joined
    assert "Código de Processo do Trabalho, artigo 98.º" in joined


def test_format_legal_code_labor():
    assert _format_legal_code("codigo do trabalho") == "Código do Trabalho"
    assert _format_legal_code("CT") == "CT"
    assert _format_legal_code("Lei de Acidentes de Trabalho") == "LAT"
    assert _format_legal_code("lei geral do trabalho em funcoes publicas") == "LTFP"


def test_citation_key_labor_dedup():
    # O "º" e o "." são removidos: a mesma referência com/sem símbolo colapsa.
    assert _legal_ref_key("Código do Trabalho, artigo 351.º") == _legal_ref_key("Código do Trabalho, artigo 351")


def test_citation_key_cpt():
    # Símbolos (º, ., ,) removidos — variantes da mesma citação colapsam.
    assert _legal_ref_key("CPT, artigo 387.º") == _legal_ref_key("CPT, artigo 387")
    assert _legal_ref_key("Código de Processo do Trabalho, artigo 387.º") == _legal_ref_key(
        "Código de Processo do Trabalho, artigo 387"
    )
    # Sigla e nome por extenso têm chaves diferentes (comportamento atual) —
    # o colapso entre eles é feito em _format_legal_code durante a extração.


# ── Perfil por área jurídica ────────────────────────────────────────────

def test_labor_area_profile_detalhado():
    profile = _area_profile("Laboral", "pt")
    for token in ("351.º CT", "386.º", "387.º", "337.º", "LAT", "Lei 73/2017", "139.º-149.º", "261.º-262.º"):
        assert token in profile, f"falta '{token}' no perfil laboral"


def test_labor_area_profile_guides_practical_analysis():
    profile = _area_profile("Laboral", "en")
    assert "just-cause dismissal" in profile
    assert "art. 351.º CT" in profile


def test_area_profile_fiscal_unchanged():
    profile = _area_profile("Fiscal", "pt")
    assert "deduções" in profile
    assert "351.º" not in profile


def test_labor_area_profile_keyword():
    assert "cronologia" in _area_profile("Direito do Trabalho", "pt")


# ── Prompt pre_filing: FASE 13 laboral ──────────────────────────────────

def test_pre_filing_labor_block_empty_for_fiscal():
    assert _pre_filing_labor_block("Fiscal", "pt") == ""


def test_pre_filing_user_prompt_injects_labor_phase():
    prompt = _pre_filing_user_prompt(
        document_name="doc.txt",
        extracted_text="Nota de culpa.",
        jurisdiction="Portugal",
        legal_area="Laboral",
        document_type="Documento laboral",
        represented_side="Trabalhador",
        objective="Preparar impugnação",
        language="pt",
    )
    assert "FASE 13" in prompt
    assert "IMPUGNAÇÃO DO DESPEDIMENTO" in prompt


def test_pre_filing_user_prompt_skips_labor_phase_for_fiscal():
    prompt = _pre_filing_user_prompt(
        document_name="doc.txt",
        extracted_text="Fatura.",
        jurisdiction="Portugal",
        legal_area="Fiscal",
        document_type="Documento fiscal",
        represented_side="Contribuinte",
        objective="Analisar",
        language="pt",
    )
    assert "FASE 13" not in prompt


# ── Schema hints contêm os campos laborais ──────────────────────────────

def test_schema_hints_contain_labor_fields():
    labor_fields = {
        "observacoes",
        "cronologia",
        "testemunhas",
        "fundamentos_de_despedimento",
        "calculo_de_indemnizacao",
        "procedimento_disciplinar",
    }
    for hint in (_schema_hint(), _pre_filing_schema_hint()):
        parsed = json.loads(hint)
        assert labor_fields <= set(parsed.keys())


# ── Normalização do payload do modelo ───────────────────────────────────

def test_normalize_model_payload_labor_fields():
    data = _normalize_model_payload(
        {
            "cronologia": [
                {"data": "2024-03-15", "descricao": "Nota de culpa", "fonte": "p. 2"},
                "Admissão em 2020",
            ],
            "testemunhas": ["Maria Silva"],
            "fundamentos_de_despedimento": [
                {"fundamento": "Justa causa", "factos_invocados": "roubo", "provas_disponiveis": "câmaras"}
            ],
            "calculo_de_indemnizacao": [
                {"item": "Indemnização", "valor_estimado": "12 000 €", "base_de_calculo": "1 000 € × 12"}
            ],
            "procedimento_disciplinar": "nota de culpa; audiência prévia",
            "observacoes": "  contexto extra  ",
        }
    )
    assert data["cronologia"][0]["data"] == "2024-03-15"
    assert data["cronologia"][0]["descricao"] == "Nota de culpa"
    assert data["cronologia"][1]["descricao"] == "Admissão em 2020"
    assert data["testemunhas"][0]["nome"] == "Maria Silva"
    assert data["testemunhas"][0]["factos_que_confirmaria"] == []
    assert data["fundamentos_de_despedimento"][0]["factos_invocados"] == ["roubo"]
    assert data["fundamentos_de_despedimento"][0]["provas_disponiveis"] == ["câmaras"]
    assert data["calculo_de_indemnizacao"][0]["valor_estimado"] == "12 000 €"
    assert data["procedimento_disciplinar"] == ["nota de culpa", "audiência prévia"]
    assert data["observacoes"] == "contexto extra"


def test_normalize_model_payload_dict_string_fields():
    data = _normalize_model_payload(
        {
            "procedure": {"tribunal_competente": "Tribunal do Trabalho", "tipo": "Ação especial"},
            "case_qualification": "Despedimento ilícito",
            "executive_summary": None,
        }
    )
    assert isinstance(data["procedure"], str)
    assert "tribunal_competente" in data["procedure"]
    assert data["case_qualification"] == "Despedimento ilícito"
    assert data["executive_summary"] == ""


def test_normalize_model_payload_labor_tolerates_absence():
    data = _normalize_model_payload({"executive_summary": "x"})
    assert data["cronologia"] == []
    assert data["testemunhas"] == []
    assert data["fundamentos_de_despedimento"] == []
    assert data["calculo_de_indemnizacao"] == []
    assert data["procedimento_disciplinar"] == []
    assert data["observacoes"] == ""


# ── Defaults do relatório não quebram o contrato ────────────────────────

def test_report_defaults_do_not_break():
    report = DevilsAdvocateReport(
        document_name="d",
        jurisdiction="Portugal",
        legal_area="Laboral",
        document_type="Documento laboral",
        represented_side="Trabalhador",
        objective="o",
        source_note="s",
        executive_summary="e",
        confidence_note="c",
    )
    assert report.cronologia == []
    assert report.testemunhas == []
    assert report.observacoes == ""
    # Round-trip de serialização
    payload = json.loads(report.model_dump_json())
    assert payload["cronologia"] == []


# ── Links ponto↔artigo incluem os campos laborais ───────────────────────

def test_all_report_points_includes_labor_fields():
    data = {
        "testemunhas": [{"nome": "Ana", "factos_que_confirmaria": ["Justa causa — CT, artigo 351.º"]}],
        "cronologia": [{"data": "2024-03-15", "descricao": "Nota de culpa", "fonte": "p. 2"}],
    }
    points = _all_report_points(data)
    assert any("351.º" in p for p in points)
    links = _reference_links_from_points(data, ["CT, artigo 351.º"])
    assert any("351.º" in link["source"] for link in links)


# ── Prompt adversarial contém a instrução dos campos estruturados ───────

def test_user_prompt_labor_structured_fields_instruction():
    prompt = _user_prompt(
        document_name="doc.txt",
        extracted_text="Doc.",
        jurisdiction="Portugal",
        legal_area="Laboral",
        document_type="Documento laboral",
        represented_side="Trabalhador",
        objective="Analisar",
        language="en",
    )
    assert "cronologia" in prompt
    assert "testemunhas" in prompt
