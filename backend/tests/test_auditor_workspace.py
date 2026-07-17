from auditor.ingestion import scan_input
from auditor.workspace import ensure_workspace


def test_ensure_workspace_creates_expected_folders(tmp_path):
    workspace = tmp_path / "empresa_x"

    ensure_workspace(workspace)

    assert (workspace / "input" / "faturas").is_dir()
    assert (workspace / "input" / "contratos").is_dir()
    assert (workspace / "db").is_dir()
    assert (workspace / "reports").is_dir()
    assert (workspace / "README.md").is_file()


def test_scan_input_detects_supported_documents(tmp_path):
    workspace = tmp_path / "empresa_x"
    ensure_workspace(workspace)
    invoice = workspace / "input" / "faturas" / "fatura.pdf"
    invoice.write_text("fake", encoding="utf-8")
    ignored = workspace / "input" / "faturas" / "thumb.tmp"
    ignored.write_text("fake", encoding="utf-8")

    docs = scan_input(workspace)

    assert len(docs) == 1
    assert docs[0].path == invoice
    assert docs[0].category == "faturas"
