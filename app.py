import time
import streamlit as st
from validators import validate_pdf, validate_total_size
from pdfutils import merge_pdfs, split_pdf
from uicomponents import show_success, show_error, download_button
from PyPDF2 import PdfReader, PdfWriter
import io, zipfile

st.set_page_config(page_title='EZPDFKit', layout='wide')
st.markdown("""
  <style>
    .stFileUploader > div { min-height: 200px; }
    .stButton>button { width: 100%; padding: 1em; font-size: 1.1rem; }
    .tab-content { margin-top: 2em; }
  </style>
""", unsafe_allow_html=True)

tools = ['Merge PDFs', 'Split PDF']
tool = st.selectbox('Select a tool', tools)

if 'last_merge_time' not in st.session_state:
    st.session_state.last_merge_time = 0

# MERGE PDF TOOL
if tool == 'Merge PDFs':
    st.subheader('Merge PDF Files')
    st.write('Upload two or more PDF files (max 100 MB each, 500 MB total) to merge them.')

    merge_files = st.file_uploader(
        label='Drag & drop or click to upload PDFs',
        type='pdf', accept_multiple_files=True, key='merge_files')

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

# SPLIT PDF TOOL, WITH MULTIPLE MODES IN TABS
elif tool == 'Split PDF':
    st.subheader('Split PDF — Choose a Mode')
    split_file = st.file_uploader('Upload a PDF (max 100 MB)', type='pdf', key='split_file')
    if not split_file:
        st.info('Please upload a PDF to enable split options.')
    else:
        valid, msg = validate_pdf(split_file, max_mb=100)
        if not valid:
            show_error(f'{split_file.name}: {msg}')
        else:
            reader = PdfReader(split_file)
            total_pages = len(reader.pages)
            split_tabs = st.tabs([
                "Extract selected pages/ranges",
                "Split at given page(s)",
                "Split every N pages",
                "Each page as separate file",
                "Split in half"
            ])

            # 1. Extract selected pages/ranges
            with split_tabs[0]:
                st.write('Enter page numbers and ranges, e.g. 1,3-5,8, to create a new PDF containing just those pages.')
                page_input = st.text_input('Pages/ranges to extract:', value="", key='ranges_input')
                if st.button('Extract Pages', key='extract_button'):
                    raw_tokens = [tok.strip() for tok in page_input.replace(' ', '').split(',') if tok.strip()]
                    valid_pages, invalid_tokens = [], []
                    for tok in raw_tokens:
                        if '-' in tok:
                            try:
                                s, e = map(int, tok.split('-'))
                                if s < 1 or e < 1 or s > total_pages and e > total_pages:
                                    invalid_tokens.append(tok)
                                else:
                                    s_clamped = max(1, s)
                                    e_clamped = min(total_pages, e)
                                    if s_clamped <= e_clamped:
                                        valid_pages.extend(range(s_clamped, e_clamped+1))
                                    else:
                                        invalid_tokens.append(tok)
                            except ValueError:
                                invalid_tokens.append(tok)
                        else:
                            try:
                                p = int(tok)
                                if 1 <= p <= total_pages:
                                    valid_pages.append(p)
                                else:
                                    invalid_tokens.append(tok)
                            except ValueError:
                                invalid_tokens.append(tok)
                    valid_pages = sorted(set(valid_pages))
                    if not valid_pages:
                        show_error('No valid pages to extract.')
                    else:
                        if invalid_tokens:
                            show_error(f'Ignored invalid entries: {", ".join(invalid_tokens)}')
                        writer = PdfWriter()
                        for n in valid_pages:
                            writer.add_page(reader.pages[n-1])
                        out = io.BytesIO()
                        writer.write(out)
                        show_success(f'Extracted {len(valid_pages)} page(s).')
                        download_button(out.getvalue(), 'split_extract.pdf', 'Download PDF')

            # 2. Split at given page(s)
            with split_tabs[1]:
                st.write(f'Enter page number(s) to split at (e.g. "10,35,50" creates splits at those pages).')
                split_points_input = st.text_input('Split at page(s):', value="", key='split_points_input')
                if st.button('Split at Pages', key='split_at_button'):
                    split_points = []
                    invalid_tokens = []
                    for tok in split_points_input.replace(' ', '').split(','):
                        if tok:
                            try:
                                idx = int(tok)
                                if 1 <= idx < total_pages:
                                    split_points.append(idx)
                                else:
                                    invalid_tokens.append(tok)
                            except ValueError:
                                invalid_tokens.append(tok)
                    split_points = sorted(set(split_points))
                    segments = [1] + split_points + [total_pages+1]
                    if len(segments) < 2:
                        show_error('No valid split points provided.')
                    else:
                        files = []
                        for i in range(len(segments)-1):
                            start, end = segments[i], segments[i+1] - 1
                            writer = PdfWriter()
                            for pg in range(start, end+1):
                                writer.add_page(reader.pages[pg-1])
                            buf = io.BytesIO()
                            writer.write(buf)
                            files.append((f'split_{start}-{end}.pdf', buf.getvalue()))
                        zip_buf = io.BytesIO()
                        with zipfile.ZipFile(zip_buf, 'w') as z:
                            for fname, data in files:
                                z.writestr(fname, data)
                        zip_buf.seek(0)
                        show_success(f'Split into {len(files)} file(s).')
                        download_button(zip_buf.getvalue(), 'split_segments.zip', 'Download ZIP')
                        if invalid_tokens:
                            show_error(f'Ignored invalid entries: {", ".join(invalid_tokens)}')

            # 3. Split every N pages
            with split_tabs[2]:
                st.write('Enter an interval N to split your PDF into parts of N pages each.')
                n_pages = st.number_input('Split every N pages:', min_value=1, max_value=total_pages, step=1, value=1, key='interval_input')
                if st.button('Split Every N Pages', key='interval_button'):
                    files = []
                    for start in range(1, total_pages+1, n_pages):
                        end = min(start + n_pages - 1, total_pages)
                        writer = PdfWriter()
                        for pg in range(start, end+1):
                            writer.add_page(reader.pages[pg-1])
                        buf = io.BytesIO()
                        writer.write(buf)
                        files.append((f'split_{start}-{end}.pdf', buf.getvalue()))
                    zip_buf = io.BytesIO()
                    with zipfile.ZipFile(zip_buf, 'w') as z:
                        for fname, data in files:
                            z.writestr(fname, data)
                    zip_buf.seek(0)
                    show_success(f'Split into {len(files)} file(s) (every {n_pages} pages).')
                    download_button(zip_buf.getvalue(), 'split_every_n.zip', 'Download ZIP')

            # 4. Each page as separate file
            with split_tabs[3]:
                st.write('Creates a ZIP file with each PDF page as its own file.')
                if st.button('Split Each Page', key='eachpage_button'):
                    files = []
                    for pg in range(1, total_pages+1):
                        writer = PdfWriter()
                        writer.add_page(reader.pages[pg-1])
                        buf = io.BytesIO()
                        writer.write(buf)
                        files.append((f'page_{pg}.pdf', buf.getvalue()))
                    zip_buf = io.BytesIO()
                    with zipfile.ZipFile(zip_buf, 'w') as z:
                        for fname, data in files:
                            z.writestr(fname, data)
                    zip_buf.seek(0)
                    show_success(f'Split into {total_pages} single-page files.')
                    download_button(zip_buf.getvalue(), 'split_individual_pages.zip', 'Download ZIP')

            # 5. Split in half
            with split_tabs[4]:
                st.write('Splits the PDF into two equal parts (first half and second half).')
                if st.button('Split in Half', key='splithalf_button'):
                    mid = total_pages // 2
                    files = []
                    writer1 = PdfWriter()
                    for i in range(1, mid+1):
                        writer1.add_page(reader.pages[i-1])
                    buf1 = io.BytesIO()
                    writer1.write(buf1)
                    files.append((f'split_1-{mid}.pdf', buf1.getvalue()))
                    writer2 = PdfWriter()
                    for i in range(mid+1, total_pages+1):
                        writer2.add_page(reader.pages[i-1])
                    buf2 = io.BytesIO()
                    writer2.write(buf2)
                    files.append((f'split_{mid+1}-{total_pages}.pdf', buf2.getvalue()))
                    zip_buf = io.BytesIO()
                    with zipfile.ZipFile(zip_buf, 'w') as z:
                        for fname, data in files:
                            z.writestr(fname, data)
                    zip_buf.seek(0)
                    show_success('PDF split in half as two files.')
                    download_button(zip_buf.getvalue(), 'split_half.zip', 'Download ZIP')
