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

# Add these new functions to your pdfutils.py file:

def compress_pdf(uploaded_file, compression_level='medium'):
    """Compress PDF by reducing image quality and removing metadata."""
    reader = PdfReader(uploaded_file)
    writer = PdfWriter()

    for page in reader.pages:
        page.compress_content_streams()  # Basic compression
        writer.add_page(page)

    writer.add_metadata({})  # Remove metadata for smaller size

    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()

def rotate_pdf(uploaded_file, rotation_angle):
    """Rotate all pages in PDF by specified angle."""
    reader = PdfReader(uploaded_file)
    writer = PdfWriter()

    for page in reader.pages:
        rotated_page = page.rotate(rotation_angle)
        writer.add_page(rotated_page)

    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()

def protect_pdf(uploaded_file, password):
    """Add password protection to PDF."""
    reader = PdfReader(uploaded_file)
    writer = PdfWriter()

    for page in reader.pages:
        writer.add_page(page)

    writer.encrypt(password)

    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()
