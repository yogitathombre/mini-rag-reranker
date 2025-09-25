import os, json, zipfile, shutil
from pathlib import Path
from pypdf import PdfReader
import sqlite3
import uuid

def extract_pdfs():
    zip_path = "data/industrial-safety-pdfs.zip"
    out_dir = Path("pdfs")
    out_dir.mkdir(exist_ok=True)

    with zipfile.ZipFile(zip_path, 'r') as z:
        print("Files inside the zip:")
        print(z.namelist())
        z.extractall(out_dir)

    # remove __MACOSX folder if present (macOS resource fork)
    macosx_dir = out_dir / "__MACOSX"
    if macosx_dir.exists():
        shutil.rmtree(macosx_dir, ignore_errors=True)

    print("Extracted to:", out_dir)
    print("Now inside pdfs/:", [p.name for p in out_dir.iterdir()])

def load_sources():
    """Load sources.json in a tolerant way.
       Supports:
       A) list of objects: [{"filename": "...", "title": "...", "url": "..."}, ...]
       B) dict mapping: {"file.pdf": {"title": "...", "url": "..."}, ...}
       C) list of objects with 'file' or 'name' instead of 'filename'
    """
    path = "data/sources.json"
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    mapping = {}

    # Case A/C: list of dicts
    if isinstance(data, list):
        for i, entry in enumerate(data):
            if not isinstance(entry, dict):
                continue
            # try multiple possible filename keys
            fname = entry.get("filename") or entry.get("file") or entry.get("name")
            title = entry.get("title") or entry.get("doc_title") or entry.get("Title")
            url   = entry.get("url")   or entry.get("link")      or entry.get("source") or entry.get("URL")
            if not fname:
                print(f"[warn] sources.json item {i} has no filename-like key; keys={list(entry.keys())}")
                continue
            mapping[fname] = (title or fname, url or "")
    # Case B: dict of filename → {title,url}
    elif isinstance(data, dict):
        for fname, meta in data.items():
            if isinstance(meta, dict):
                title = meta.get("title") or meta.get("doc_title") or meta.get("Title") or fname
                url   = meta.get("url")   or meta.get("link")      or meta.get("source") or meta.get("URL") or ""
                mapping[fname] = (title, url)
            else:
                # If value is a string, assume it's a URL with no title
                mapping[fname] = (fname, str(meta))
    else:
        raise ValueError("sources.json has an unexpected structure.")

    # Debug: show what we loaded
    print(f"Loaded {len(mapping)} source entries. Sample:")
    for k in list(mapping.keys())[:3]:
        print("  ", k, "→", mapping[k])

    return mapping



# 3. Extract text from a PDF
def pdf_to_text(path):
    try:
        reader = PdfReader(path)

        # If encrypted, try to decrypt with empty password
        if reader.is_encrypted:
            try:
                reader.decrypt("")
            except Exception as e:
                print(f"[warn] Could not decrypt {path.name}: {e}")
                return ""

        text = []
        for page in reader.pages:
            try:
                text.append(page.extract_text() or "")
            except Exception as e:
                print(f"[warn] Failed extracting from page in {path.name}: {e}")
                text.append("")
        return "\n".join(text)

    except Exception as e:
        print(f"[warn] Skipping {path.name} (could not open: {e})")
        return ""



def chunk_text(text, min_len=300, max_len=900):
    paras = [p.strip() for p in text.split("\n") if p.strip()]
    chunks, buf = [], ""
    for p in paras:
        if len(buf) + len(p) < max_len:
            buf += " " + p
        else:
            chunks.append(buf.strip())
            buf = p
    if buf:
        chunks.append(buf.strip())
    return [c for c in chunks if len(c) > min_len]

def setup_db():
   
    conn = sqlite3.connect("store/rag.db")
    cur = conn.cursor()
    cur.executescript("""
    CREATE TABLE IF NOT EXISTS docs(
        id TEXT PRIMARY KEY, 
        title TEXT, 
        url TEXT
    );

    CREATE TABLE IF NOT EXISTS chunks(
        id TEXT PRIMARY KEY, 
        doc_id TEXT, 
        chunk_id INTEGER, 
        text TEXT
    );

    -- Full-text search table for BM25
    CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts 
    USING fts5(text, content='chunks', content_rowid='rowid');
    """)
    conn.commit()
    return conn


def insert_doc(conn, title, url):
    """Insert a new document row and return its id."""
    doc_id = str(uuid.uuid4())
    conn.execute(
        "INSERT INTO docs(id,title,url) VALUES(?,?,?)",
        (doc_id, title, url)
    )
    return doc_id

def insert_chunks(conn, doc_id, chunks):
    for i, chunk in enumerate(chunks):
        cid = str(uuid.uuid4())
        conn.execute(
            "INSERT INTO chunks(id, doc_id, chunk_id, text) VALUES(?,?,?,?)",
            (cid, doc_id, i, chunk),
        )
        # Also insert into FTS so BM25 works
        conn.execute(
            "INSERT INTO chunks_fts(rowid, text) VALUES(last_insert_rowid(), ?)",
            (chunk,)
        )



# 4. Main test block
if __name__ == "__main__":
    # 1. Unzip PDFs
    extract_pdfs()
    sources = load_sources()

    # 2. Setup database
    conn = setup_db()

    # 3. Loop through all PDFs
    for pdf_path in Path("pdfs").rglob("*.pdf"):
        filename = pdf_path.name
        title, url = sources.get(filename, (filename, ""))  # fallback if missing

        # insert doc row
        doc_id = insert_doc(conn, title, url)

        # extract + chunk text
        content = pdf_to_text(pdf_path)
        chunks = chunk_text(content)

        # insert chunk rows
        insert_chunks(conn, doc_id, chunks)

        print(f"Inserted {len(chunks)} chunks from {filename}")

    # 4. Commit + close
    conn.commit()
    conn.close()
    print("All PDFs processed and stored in SQLite ✅")
