"""Metadata attached to every page and chunk of the knowledge base.

Two kinds of fields:
- derived from the file: document_id, source, category, page, total_pages, product, doc_type, title
- set by the document owner in data/documents/metadata.json: date, valid, reviewed_at
  (reviewed_at is also set by the admin review API)

Everything else PyPDFLoader extracts (producer, creator, author, PDF timestamps)
is dropped: it is noise for retrieval and is stored with every chunk otherwise.
"""

import json
import os
import re
import uuid
# Aliased: a field called "date" would otherwise shadow the type in later annotations.
from datetime import date as Date, datetime, timezone
from pathlib import Path
from typing import Any
from pydantic import BaseModel, ConfigDict, ValidationError, field_validator
from src.app_logging.logger import logger

MANIFEST_FILE_NAME = "metadata.json"
ACRONYMS = {"faq": "FAQ"}
PRODUCT_PATTERN = re.compile(r"^(AIS-\d+)_", re.IGNORECASE)
# How a product is written in free text: "AIS-200", "AIS 200", "ais200".
PRODUCT_MENTION_PATTERN = re.compile(r"\bAIS[\s-]?(\d+)\b", re.IGNORECASE)

# PyPDFLoader fields kept as they are; all others are dropped.
KEPT_LOADER_FIELDS = ("page", "total_pages")

# Fixed namespace: the same file name always yields the same document_id, across ingestions and machines.
DOCUMENT_ID_NAMESPACE = uuid.UUID("6f1c2b7e-4d1a-5b8e-9c3f-a0e4d2b1c7f9")


class DocumentInfo(BaseModel):
    """Owner-managed information about one document."""

    model_config = ConfigDict(extra="forbid")

    date: Date | None = None
    """Effective date of the document."""
    valid: bool = True
    """False when the owner has withdrawn the document; retrieval then ignores it."""
    reviewed_at: datetime | None = None
    """When the owner last reviewed the document (UTC), or None if it was never reviewed.

    A plain date ("2026-06-01") is accepted and read as midnight UTC.
    """

    @field_validator("reviewed_at")
    @classmethod
    def _assume_utc(cls, value: datetime | None) -> datetime | None:
        return value.replace(tzinfo=timezone.utc) if value is not None and value.tzinfo is None else value


def document_id_from_source(source: str) -> str:
    """Stable id of a document, derived from its file name (a UUID v5).

    It needs no manual upkeep and is stored with every chunk, so the chunks of
    one document can be found and replaced. Renaming a file gives it a new id.
    """

    return str(uuid.uuid5(DOCUMENT_ID_NAMESPACE, Path(source).name))


def document_title(source: str) -> str:
    """Turn a file name into a readable title: "AIS-100_technical_specifications.pdf" -> "AIS-100 Technical Specifications"."""

    words = Path(source).stem.replace("_", " ").split()

    return " ".join(
        ACRONYMS.get(word.lower(), word if any(character.isupper() for character in word) else word.capitalize())
        for word in words
    )


def product_from_source(source: str) -> str | None:
    """Product the document is about: "AIS-500_user_manual.pdf" -> "AIS-500"; None for general documents."""

    match = PRODUCT_PATTERN.match(Path(source).name)

    return match.group(1).upper() if match else None


def products_mentioned(text: str) -> list[str]:
    """Products named in free text, in the form stored in the product field: "ais 200 vs AIS-500" -> ["AIS-200", "AIS-500"]."""

    return sorted({f"AIS-{number}" for number in PRODUCT_MENTION_PATTERN.findall(text)})


def doc_type_from_source(source: str) -> str:
    """Kind of document, without the product: "AIS-500_user_manual.pdf" -> "user_manual"."""

    return PRODUCT_PATTERN.sub("", Path(source).stem).lower()


def load_manifest(path: Path) -> dict[str, DocumentInfo]:
    """Read the owner manifest: a JSON object mapping each PDF file name to its DocumentInfo.

    A missing file yields an empty manifest. Invalid content raises ValueError,
    so a typo in a date or field name stops the ingestion instead of being ignored.
    """

    if not path.exists():
        logger.warning("Document metadata manifest not found", path=str(path))
        return {}

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path} is not valid JSON: {exc}") from exc

    if not isinstance(raw, dict):
        raise ValueError(f"{path} must contain a JSON object keyed by PDF file name.")

    manifest: dict[str, DocumentInfo] = {}

    for source, values in raw.items():
        try:
            manifest[source] = DocumentInfo.model_validate(values)
        except ValidationError as exc:
            raise ValueError(f"Invalid metadata for '{source}' in {path}: {exc}") from exc

    return manifest


def build_page_metadata(pdf_path: Path, loader_metadata: dict[str, Any], info: DocumentInfo) -> dict[str, Any]:
    """Build the metadata of one PDF page. Dates are ISO strings because metadata is stored as JSON."""

    source = pdf_path.name
    metadata: dict[str, Any] = {key: loader_metadata[key] for key in KEPT_LOADER_FIELDS if key in loader_metadata}

    metadata.update({
        "document_id": document_id_from_source(source),
        "source": source,
        "category": pdf_path.parent.name,
        "product": product_from_source(source),
        "doc_type": doc_type_from_source(source),
        "title": document_title(source),
        "date": info.date.isoformat() if info.date else None,
        "valid": info.valid,
        "reviewed_at": info.reviewed_at.isoformat() if info.reviewed_at else None
    })

    return metadata


def save_manifest(path: Path, manifest: dict[str, DocumentInfo]) -> None:
    """Write the owner manifest, one line per document as in the hand-written file.

    The file is written to a temporary file and then renamed, so a crash
    mid-write never leaves a truncated manifest that would stop the ingestion.
    """

    lines = [
        f"  {json.dumps(source)}: {json.dumps(info.model_dump(mode='json'))}"
        for source, info in manifest.items()
    ]
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text("{\n" + ",\n".join(lines) + "\n}\n", encoding="utf-8")
    os.replace(temporary, path)
