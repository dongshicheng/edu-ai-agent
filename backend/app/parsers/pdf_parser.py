from app.models.parse_result import ParseResult


def parse_pdf(file_path: str) -> ParseResult:
    """Parse PDF using unstructured library."""
    try:
        from unstructured.partition.pdf import partition_pdf
        elements = partition_pdf(file_path, strategy="fast")

        texts = []
        tables = []
        for el in elements:
            if hasattr(el, "category") and el.category == "Table":
                tables.append(str(el))
            else:
                texts.append(str(el))

        return ParseResult(
            text="\n\n".join(texts),
            tables=tables,
            source_type="pdf",
            page_count=len(set(
                getattr(el, "metadata", {}).get("page_number", 0)
                for el in elements
                if hasattr(el, "metadata")
            )),
            metadata={"filename": file_path},
        )
    except ImportError:
        # Fallback to pypdf
        from pypdf import PdfReader
        reader = PdfReader(file_path)
        texts = [page.extract_text() or "" for page in reader.pages]
        return ParseResult(
            text="\n\n".join(texts),
            source_type="pdf",
            page_count=len(reader.pages),
            metadata={"filename": file_path},
        )
