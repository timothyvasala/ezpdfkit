import imghdr
from PyPDF2 import PdfReader

def validate_pdf(uploaded_file, max_mb: int = 100): # 100 MB per file
    """
    Return (True, '') if:
      - Filename ends with .pdf
      - Size ≤ max_mb MB
      - Begins with '%PDF-'
      - Contains ≥1 page
    Otherwise returns (False, error_message).
    """
    name = uploaded_file.name
    # 1. Extension
    if not name.lower().endswith('.pdf'):
        return False, 'Invalid file extension; expected .pdf'
    # 2. Size per file
    size_mb = uploaded_file.size / (1024 ** 2)
    if size_mb > max_mb:
        return False, f'File too large ({size_mb:.1f} MB); max {max_mb} MB'
    # 3. Magic bytes
    header = uploaded_file.read(5)
    uploaded_file.seek(0)
    if header != b'%PDF-':
        return False, 'File is not a valid PDF (bad header)'
    # 4. Page count
    try:
        reader = PdfReader(uploaded_file)
        if len(reader.pages) == 0:
            return False, 'PDF has no pages'
    except Exception:
        return False, 'Unable to read PDF; file may be corrupted'
    finally:
        uploaded_file.seek(0)
    return True, ''

def validate_total_size(files, max_total_mb: int = 500): # 500 MB total
    """
    Return (True, '') if combined size of all uploaded files ≤ max_total_mb.
    Otherwise returns (False, error_message).
    """
    total_mb = sum(f.size for f in files) / (1024 ** 2)
    if total_mb > max_total_mb:
        return False, f'Total upload size too large ({total_mb:.1f} MB); max {max_total_mb} MB'
    return True, ''

def validate_image(uploaded_file, max_mb: int = 20):
    """
    Return (True, '') if:
      - Supported image extension
      - Size ≤ max_mb MB
      - Valid image header
    Otherwise returns (False, error_message).
    """
    name = uploaded_file.name
    ext = name.lower().rsplit('.', 1)[-1]
    # 1. Extension
    if ext not in ('jpg', 'jpeg', 'png', 'bmp', 'tiff', 'gif'):
        return False, f'Unsupported image type; .{ext} not allowed'
    # 2. Size per file
    size_mb = uploaded_file.size / (1024 ** 2)
    if size_mb > max_mb:
        return False, f'Image too large ({size_mb:.1f} MB); max {max_mb} MB'
    # 3. Header
    if not imghdr.what(uploaded_file):
        return False, 'Invalid or corrupted image file'
    uploaded_file.seek(0)
    return True, ''
