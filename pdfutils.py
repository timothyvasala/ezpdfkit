from PyPDF2 import PdfWriter, PdfReader
from pdf2image import convert_from_bytes
from PIL import Image
import io, zipfile

def merge_pdfs(files):
    """Merge list of file-like PDFs and return bytes."""
    writer = PdfWriter()
    for f in files:
        reader = PdfReader(f)
        for page in reader.pages:
            writer.add_page(page)
    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()

def split_pdf(uploaded_file, page_numbers):
    """Extract specified pages from a PDF and return new PDF bytes."""
    reader = PdfReader(uploaded_file)
    writer = PdfWriter()
    for n in page_numbers:
        writer.add_page(reader.pages[n-1])
    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()
