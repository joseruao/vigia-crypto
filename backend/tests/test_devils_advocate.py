from Api.services.devils_advocate import (
    _area_profile,
    _citation_key,
    _extract_legal_references,
    _filter_verified_reference_sources,
    _format_legal_code,
    _normalize_model_payload,
)


def test_legal_references_filter_model_hallucinations():
    refs = _extract_legal_references("CIVA, artigo 19.º e CIVA artigo 36")
    payload = _normalize_model_payload(
        {
            "legal_references_used": [
                {"point": "valid point", "source": "CIVA, artigo 19", "status": "verified"},
                {"point": "invented point", "source": "CIVA, artigo 99.º", "status": "verified"},
            ]
        }
    )

    filtered = _filter_verified_reference_sources(payload["legal_references_used"], refs)

    assert filtered == [
        {
            "point": "valid point",
            "source": "CIVA, artigo 19.º",
            "status": "redação atual não verificada em fonte oficial",
        }
    ]

def test_model_payload_string_fields_are_normalized_to_lists():
    payload = _normalize_model_payload(
        {
            "case_theory": "história do contribuinte",
            "opponent_theory": "história da AT",
            "unverified_legal_points": "CIVA, artigo 19; validar redação atual",
            "burden_and_proof": "provar ligação fatura-projeto",
            "hearing_questions": "quem aprovou a despesa?",
            "next_actions": "criar tabela fatura-projeto",
            "risk_matrix": [{"title": "Prova", "points": "fatura genérica; sem contrato ligado"}],
        }
    )

    assert payload["case_theory"] == ["história do contribuinte"]
    assert payload["opponent_theory"] == ["história da AT"]
    assert payload["unverified_legal_points"] == ["CIVA, artigo 19", "validar redação atual"]
    assert payload["burden_and_proof"] == ["provar ligação fatura-projeto"]
    assert payload["hearing_questions"] == ["quem aprovou a despesa?"]
    assert payload["next_actions"] == ["criar tabela fatura-projeto"]
    assert payload["risk_matrix"] == [
        {"title": "Prova", "points": ["fatura genérica", "sem contrato ligado"]}
    ]


def test_extract_labor_legal_references():
    refs = _extract_legal_references(
        "O despedimento invoca o artigo 351.º do Código do Trabalho e o CPT, artigo 98."
    )

    assert refs == [
        "Código do Trabalho, artigo 351.º",
        "CPT, artigo 98.º",
    ]


def test_labor_area_profile_guides_practical_analysis():
    profile = _area_profile("Laboral", "pt")

    assert "cronologia" in profile
    assert "testemunhas" in profile
    assert "Código do Trabalho" in profile


# ── Novos testes laborais ──────────────────────────────────────────────


def test_extract_labor_legal_references_lat_ltfp_rct():
    """LAT, LTFP e RCT devem ser extraídos como referências legais."""
    refs = _extract_legal_references(
        "O sinistro enquadra-se na LAT, artigo 6.º. "
        "A arguida é trabalhadora em funções públicas (LTFP, artigo 297.º). "
        "Consultar também RCT, artigo 34.º."
    )

    assert "LAT, artigo 6.º" in refs
    assert "LTFP, artigo 297.º" in refs
    assert "RCT, artigo 34.º" in refs


def test_extract_labor_full_names():
    """Nomes completos também devem ser extraídos."""
    refs = _extract_legal_references(
        "O artigo 6.º da Lei de Acidentes de Trabalho e "
        "o artigo 297.º da Lei Geral do Trabalho em Funções Públicas."
    )

    assert len(refs) >= 2
    assert any("LAT" in r or "Acidentes" in r for r in refs)
    assert any("LTFP" in r or "Funções Públicas" in r for r in refs)


def test_format_legal_code_labor():
    """_format_legal_code deve formatar corretamente os novos códigos."""
    assert _format_legal_code("Lei de Acidentes de Trabalho") == "LAT"
    assert _format_legal_code("Lei Geral do Trabalho em Funções Públicas") == "LTFP"
    assert _format_legal_code("Regulamento do Código do Trabalho") == "RCT"
    assert _format_legal_code("Código do Trabalho") == "Código do Trabalho"
    assert _format_legal_code("CPT") == "CPT"


def test_format_legal_code_unknown_returns_upper():
    """Códigos desconhecidos são devolvidos em maiúsculas."""
    assert _format_legal_code("lal") == "LAL"


def test_labor_area_profile_detalhado():
    """O perfil laboral expandido deve mencionar os novos tópicos."""
    profile = _area_profile("Laboral", "pt")

    assert "justa causa" in profile
    assert "351" in profile
    assert "329" in profile
    assert "386" in profile
    assert "337" in profile
    assert "389" in profile
    assert "263" in profile
    assert "LAT" in profile
    assert "assédio" in profile
    assert "Lei 73/2017" in profile
    assert "discriminação" in profile
    assert "igualdade retributiva" in profile
    assert "LTFP" in profile
    assert "RCT" in profile


def test_labor_area_profile_trabalho_keyword():
    """'Trabalho' também deve ativar o perfil laboral."""
    profile = _area_profile("Direito do Trabalho", "pt")
    assert "Perfil Laboral" in profile


def test_citation_key_labor_dedup():
    """Dedup de citações laborais (CT, CPT)."""
    key1 = _citation_key("Código do Trabalho, artigo 351.º")
    key2 = _citation_key("CT, artigo 351.º")
    assert key1 == key2, f"Dedup falhou: '{key1}' != '{key2}'"


def test_citation_key_cpt():
    """CPT deve normalizar para 'cpt'."""
    key1 = _citation_key("Código de Processo do Trabalho, artigo 98.º")
    key2 = _citation_key("CPT, artigo 98")
    assert key1 == key2, f"Dedup CPT falhou: '{key1}' != '{key2}'"
