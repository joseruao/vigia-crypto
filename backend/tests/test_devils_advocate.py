from Api.services.devils_advocate import (
    _extract_legal_references,
    _filter_verified_reference_sources,
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
            "status": "mencionada no documento; redação atual em fonte oficial não verificada nesta fase",
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
