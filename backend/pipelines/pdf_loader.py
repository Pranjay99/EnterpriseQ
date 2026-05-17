from pypdf import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter


def load_pdf(file_path: str) -> list[str]:
    """
    Extract text from a PDF and split it into overlapping chunks
    ready for embedding / RAG retrieval.
    """
    reader = PdfReader(file_path)
    full_text = "\n".join(
        page.extract_text() or "" for page in reader.pages
    )
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    return splitter.split_text(full_text)
