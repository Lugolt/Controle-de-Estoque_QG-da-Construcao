import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

DB_PATH = Path(os.getenv("ESTOQUE_DB", Path(__file__).parent / "PJIdb_v2.db"))


@contextmanager
def conexao():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def linha_para_dict(linha):
    return dict(linha) if linha is not None else None


def linhas_para_lista(linhas):
    return [dict(l) for l in linhas]
