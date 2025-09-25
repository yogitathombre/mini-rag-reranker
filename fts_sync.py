# fts_sync.py
import sqlite3

con = sqlite3.connect("store/rag.db")
cur = con.cursor()

# 1. Create the FTS5 table if it doesn't already exist
cur.execute("""
CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts
USING fts5(text, content='chunks', content_rowid='rowid');
""")

# 2. Backfill: copy all rows from chunks → chunks_fts (only missing ones)
cur.execute("""
INSERT INTO chunks_fts(rowid, text)
SELECT rowid, text FROM chunks
WHERE rowid NOT IN (SELECT rowid FROM chunks_fts);
""")

con.commit()
con.close()
print("✅ chunks_fts created & synced with existing chunks")
