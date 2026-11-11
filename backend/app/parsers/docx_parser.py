from app.models.parse_result import ParseResult


def parse_docx(file_path: str) -> ParseResult:
    """Parse DOCX using python-docx."""
    from docx import Document

    doc = Document(file_path)

    texts = []
    tables = []

    for para in doc.paragraphs:
        if para.text.strip():
            texts.append(para.text)

    for table in doc.tables:
        rows = []
        for row in table.rows:
            cells = [cell.text.strip() for cell in row.cells]
            rows.append(" | ".join(cells))
        tables.append("\n".join(rows))

    return ParseResult(
        text="\n\n".join(texts),
        tables=tables,
        source_type="docx",
        metadata={"filename": file_path},
    )
