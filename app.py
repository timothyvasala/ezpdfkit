import time
import streamlit as st
from validators import validate_pdf, validate_total_size
from pdfutils import merge_pdfs, split_pdf
from uicomponents import show_success, show_error, download_button
from PyPDF2 import PdfReader, PdfWriter
import io, zipfile

# Page config and custom CSS
st.set_page_config(page_title='EZPDFKit', layout='wide')
st.markdown("""
  <style>
    .stFileUploader > div { min-height: 200px; }
    .stButton>button { width: 100%; padding: 1em; font-size: 1.1rem; }
  </style>
""", unsafe_allow_html=True)

# Tool selector
tools = ['Merge PDFs', 'Split PDF']
tool = st.selectbox('Select a tool', tools)

# Initialize rate-limiting timestamp for merge
if 'last_merge_time' not in st.session_state:
    st.session_state.last_merge_time = 0

# MERGE PDF TOOL BLOCK
if tool == 'Merge PDFs':
    st.subheader('Merge PDF Files')
    st.write('Upload two or more PDF files (max 100 MB each, 500 MB total) to merge them.')

    merge_files = st.file_uploader(
        label='Drag & drop or click to upload PDFs',
        type='pdf',
        accept_multiple_files=True,
        key='merge_files'
    )

    if st.button('Merge PDFs', type='primary', key='merge_button'):
        elapsed = time.time() - st.session_state.last_merge_time
        if elapsed < 30:
            show_error(f'Please wait {30 - int(elapsed)} s before merging again.')
        elif not merge_files or len(merge_files) < 2:
            show_error('Please upload at least two PDF files.')
        else:
            ok, msg = validate_total_size(merge_files, max_total_mb=500)
            if not ok:
                show_error(msg)
            else:
                all_valid = True
                for f in merge_files:
                    valid, msg = validate_pdf(f, max_mb=100)
                    if not valid:
                        show_error(f'{f.name}: {msg}')
                        all_valid = False
                if all_valid:
                    st.session_state.last_merge_time = time.time()
                    try:
                        merged_bytes = merge_pdfs(merge_files)
                        show_success('PDFs merged successfully!')
                        download_button(merged_bytes, 'merged.pdf', 'Download Merged PDF')
                    except Exception as e:
                        show_error(f'Error during merge: {str(e)}')

# SPLIT PDF TOOL BLOCK
elif tool == 'Split PDF':
    st.subheader('Split PDF File')
    st.write('Upload a PDF file (max 100 MB) and specify pages or ranges to extract or split at (e.g. 1,3-5,8 or 10 to split at page 10).')

    split_file = st.file_uploader(
        'Upload a PDF to split',
        type='pdf',
        key='split_file'
    )
    page_input = st.text_input(
        'Enter pages/ranges or split points (e.g. 1,3-5,8 or 10):',
        value="",
        max_chars=100,
        key='split_pages'
    )

    if st.button('Split PDF', type='primary', key='split_button'):
        if not split_file:
            show_error('Please upload a PDF.')
        else:
            valid, msg = validate_pdf(split_file, max_mb=100)
            if not valid:
                show_error(f'{split_file.name}: {msg}')
            else:
                try:
                    reader = PdfReader(split_file)
                    total_pages = len(reader.pages)
                    raw_tokens = [tok.strip() for tok in page_input.replace(' ', '').split(',') if tok.strip()]
                    if not raw_tokens:
                        show_error('No pages or ranges specified.')
                    else:
                        valid_pages = []
                        invalid_tokens = []
                        # Parse each token
                        for tok in raw_tokens:
                            if '-' in tok:
                                start, end = tok.split('-', 1)
                                try:
                                    s, e = int(start), int(end)
                                    if s < 1 or e < 1 or s > total_pages and e > total_pages:
                                        invalid_tokens.append(tok)
                                    else:
                                        # clamp to valid range
                                        s_clamped = max(1, s)
                                        e_clamped = min(total_pages, e)
                                        if s_clamped <= e_clamped:
                                            valid_pages.extend(range(s_clamped, e_clamped + 1))
                                        else:
                                            invalid_tokens.append(tok)
                                except ValueError:
                                    invalid_tokens.append(tok)
                            else:
                                # single page or split point
                                try:
                                    p = int(tok)
                                    if 1 <= p <= total_pages:
                                        valid_pages.append(p)
                                    else:
                                        invalid_tokens.append(tok)
                                except ValueError:
                                    invalid_tokens.append(tok)
                        valid_pages = sorted(set(valid_pages))

                        # Handle “split at page” if only single tokens and no ranges
                        if len(raw_tokens) == 1 and not '-' in raw_tokens[0]:
                            p = valid_pages[0] if valid_pages else None
                            if p:
                                # split into two docs: 1–p and p+1–end
                                writer1 = PdfWriter()
                                for i in range(1, p+1):
                                    writer1.add_page(reader.pages[i-1])
                                writer2 = PdfWriter()
                                for i in range(p+1, total_pages+1):
                                    writer2.add_page(reader.pages[i-1])
                                # bundle into a zip
                                zip_buf = io.BytesIO()
                                with zipfile.ZipFile(zip_buf, 'w') as z:
                                    out1 = io.BytesIO(); writer1.write(out1)
                                    out2 = io.BytesIO(); writer2.write(out2)
                                    z.writestr(f'split_1-{p}.pdf', out1.getvalue())
                                    z.writestr(f'split_{p+1}-{total_pages}.pdf', out2.getvalue())
                                zip_buf.seek(0)
                                show_success(f'Split into 2 files at page {p}.')
                                st.download_button('Download Split ZIP', zip_buf, file_name='split_pages.zip')
                                # warn if any invalid
                                if invalid_tokens:
                                    show_error(f'Invalid tokens ignored: {", ".join(invalid_tokens)}')

                        # Final extraction for explicit pages list
                        if not valid_pages:
                            show_error('No valid pages to extract after filtering invalid entries.')
                        else:
                            # warn about invalid tokens
                            if invalid_tokens:
                                show_error(f'Ignored invalid entries: {", ".join(invalid_tokens)}')
                            # extract valid_pages
                            writer = PdfWriter()
                            for n in valid_pages:
                                writer.add_page(reader.pages[n-1])
                            out = io.BytesIO()
                            writer.write(out)
                            show_success(f'Extracted {len(valid_pages)} page(s).')
                            download_button(out.getvalue(), 'split.pdf', 'Download Split PDF')
                except Exception as e:
                    show_error(f'Error during split: {str(e)}')
