import json
from datetime import date, datetime, timezone
from pathlib import Path
import pytest
from src.rag.document_metadata import (DocumentInfo, build_page_metadata, doc_type_from_source, document_id_from_source, document_title,
                                       load_manifest, product_from_source, products_mentioned, save_manifest)

PDF_METADATA = {
    "producer": "www.ilovepdf.com",
    "creator": "Microsoft Word 2016",
    "author": "Someone",
    "creationdate": "2026-09-28T10:35:39+00:00",
    "moddate": "2026-09-28T10:35:39+00:00",
    "source": "data/documents/manuals/AIS-500_user_manual.pdf",
    "total_pages": 12,
    "page": 3,
    "page_label": "4"
}


@pytest.mark.parametrize(("source", "product"), [
    ("AIS-500_user_manual.pdf", "AIS-500"),
    ("AIS-100_technical_specifications.pdf", "AIS-100"),
    ("ais-200_user_manual.pdf", "AIS-200"),
    ("warranty_policy.pdf", None),
    ("customer_faq.pdf", None)
])
def test_product_from_source(source: str, product: str | None) -> None:
    assert product_from_source(source) == product


@pytest.mark.parametrize(("text", "products"), [
    ("What is the maintenance interval of the AIS-200?", ["AIS-200"]),
    ("ais 500 weight", ["AIS-500"]),
    ("Is the AIS100 faster than the AIS-500 or the AIS-100?", ["AIS-100", "AIS-500"]),
    ("What does error code E-204 mean?", []),
    ("What are the support hours?", [])
])
def test_products_mentioned(text: str, products: list[str]) -> None:
    assert products_mentioned(text) == products


@pytest.mark.parametrize(("source", "doc_type"), [
    ("AIS-500_user_manual.pdf", "user_manual"),
    ("AIS-100_technical_specifications.pdf", "technical_specifications"),
    ("warranty_policy.pdf", "warranty_policy"),
    ("customer_faq.pdf", "customer_faq")
])
def test_doc_type_from_source(source: str, doc_type: str) -> None:
    assert doc_type_from_source(source) == doc_type


def test_document_title() -> None:
    assert document_title("AIS-100_technical_specifications.pdf") == "AIS-100 Technical Specifications"
    assert document_title("customer_faq.pdf") == "Customer FAQ"


def test_page_metadata_keeps_only_known_fields() -> None:
    info = DocumentInfo(date=date(2026, 1, 15), valid=True, reviewed_at=date(2026, 6, 1))

    metadata = build_page_metadata(Path("data/documents/manuals/AIS-500_user_manual.pdf"), PDF_METADATA, info)

    assert metadata == {
        "document_id": document_id_from_source("AIS-500_user_manual.pdf"),
        "source": "AIS-500_user_manual.pdf",
        "category": "manuals",
        "page": 3,
        "total_pages": 12,
        "product": "AIS-500",
        "doc_type": "user_manual",
        "title": "AIS-500 User Manual",
        "date": "2026-01-15",
        "valid": True,
        "reviewed_at": "2026-06-01T00:00:00+00:00"
    }


def test_page_metadata_without_owner_information() -> None:
    metadata = build_page_metadata(Path("data/documents/policies/warranty_policy.pdf"), {"page": 0}, DocumentInfo())

    assert metadata["product"] is None
    assert metadata["date"] is None
    assert metadata["reviewed_at"] is None
    assert metadata["valid"] is True


def write_manifest(path: Path, content: object) -> Path:
    path.write_text(json.dumps(content), encoding="utf-8")
    return path


def test_load_manifest(tmp_path: Path) -> None:
    path = write_manifest(tmp_path / "metadata.json", {
        "warranty_policy.pdf": {"date": "2026-01-01", "valid": False, "reviewed_at": "2026-03-10"},
        "customer_faq.pdf": {}
    })

    manifest = load_manifest(path)

    assert manifest["warranty_policy.pdf"] == DocumentInfo(date=date(2026, 1, 1), valid=False, reviewed_at=datetime(2026, 3, 10, tzinfo=timezone.utc))
    assert manifest["customer_faq.pdf"] == DocumentInfo()


def test_missing_manifest_is_empty(tmp_path: Path) -> None:
    assert load_manifest(tmp_path / "metadata.json") == {}


@pytest.mark.parametrize("entry", [
    {"date": "15/01/2026"},          # not ISO
    {"valid": "maybe"},              # not a boolean
    {"reviewedAt": "2026-01-01"}     # unknown field: a typo must not be ignored
])
def test_invalid_manifest_entry_raises(tmp_path: Path, entry: dict) -> None:
    path = write_manifest(tmp_path / "metadata.json", {"warranty_policy.pdf": entry})

    with pytest.raises(ValueError, match="warranty_policy.pdf"):
        load_manifest(path)


def test_manifest_must_be_an_object(tmp_path: Path) -> None:
    path = write_manifest(tmp_path / "metadata.json", ["warranty_policy.pdf"])

    with pytest.raises(ValueError, match="JSON object"):
        load_manifest(path)


def test_document_id_is_stable_and_unique() -> None:
    assert document_id_from_source("data/documents/manuals/AIS-500_user_manual.pdf") == document_id_from_source("AIS-500_user_manual.pdf")
    assert document_id_from_source("AIS-500_user_manual.pdf") != document_id_from_source("AIS-200_user_manual.pdf")


def test_reviewed_at_accepts_dates_and_timestamps_as_utc() -> None:
    assert DocumentInfo(reviewed_at="2026-06-01").reviewed_at == datetime(2026, 6, 1, tzinfo=timezone.utc)
    assert DocumentInfo(reviewed_at="2026-06-01T10:30:00Z").reviewed_at == datetime(2026, 6, 1, 10, 30, tzinfo=timezone.utc)


def test_save_manifest_round_trips_one_line_per_document(tmp_path: Path) -> None:
    path = tmp_path / "metadata.json"
    manifest = {
        "warranty_policy.pdf": DocumentInfo(date=date(2026, 1, 1), reviewed_at=datetime(2026, 11, 12, 9, 30, tzinfo=timezone.utc)),
        "customer_faq.pdf": DocumentInfo()
    }

    save_manifest(path, manifest)

    assert load_manifest(path) == manifest
    assert path.read_text(encoding="utf-8").splitlines() == [
        "{",
        '  "warranty_policy.pdf": {"date": "2026-01-01", "valid": true, "reviewed_at": "2026-11-12T09:30:00Z"},',
        '  "customer_faq.pdf": {"date": null, "valid": true, "reviewed_at": null}',
        "}"
    ]
    assert not list(tmp_path.glob(".*.tmp"))
