import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

from database import DB_PATH

TIPOS_QUE_SOMAM = ("SALDO_INICIAL", "ENTRADA", "AJUSTE_POSITIVO", "TRANSFERENCIA_ENTRADA")

_SQL_CRIAR_MOVIMENTACOES = """
CREATE TABLE {nome} (
    movimentacao_id  INTEGER PRIMARY KEY AUTOINCREMENT,
    produto_id       INTEGER NOT NULL REFERENCES produtos(produto_id),
    estoque_local    TEXT NOT NULL CHECK (estoque_local IN ('deposito','loja')),
    tipo             TEXT NOT NULL CHECK (tipo IN (
                        'SALDO_INICIAL','ENTRADA','SAIDA','PERDA',
                        'AJUSTE_POSITIVO','AJUSTE_NEGATIVO',
                        'TRANSFERENCIA_ENTRADA','TRANSFERENCIA_SAIDA')),
    quantidade       REAL NOT NULL CHECK (quantidade > 0),
    compra_id        INTEGER REFERENCES compras(compras_id),
    observacao       TEXT,
    registrado_por   TEXT,
    criado_em        TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
)"""


def _colunas(conn, tabela):
    return [c[1] for c in conn.execute(f"PRAGMA table_info({tabela})")]


def _sql_da_tabela(conn, tabela):
    r = conn.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (tabela,)).fetchone()
    return r[0] if r else None


def _conciliar_historico(conn, avisos):
    soma = ",".join(f"'{t}'" for t in TIPOS_QUE_SOMAM)
    linhas = conn.execute(f"""
        SELECT e.produto_id, e.estoque_local, e.estoque_quantidade AS saldo,
               COALESCE((SELECT SUM(CASE WHEN m.tipo IN ({soma}) THEN m.quantidade ELSE -m.quantidade END)
                         FROM movimentacoes m
                         WHERE m.produto_id = e.produto_id AND m.estoque_local = e.estoque_local), 0) AS historico
        FROM estoque e""").fetchall()

    ts = conn.execute("SELECT datetime(MIN(criado_em), '-1 second') FROM movimentacoes").fetchone()[0]
    criados = corrigidos = 0
    for produto_id, local, saldo, historico in linhas:
        dif = saldo - historico
        if abs(dif) < 1e-9:
            continue
        if dif > 0:
            conn.execute(
                """INSERT INTO movimentacoes (produto_id, estoque_local, tipo, quantidade,
                                              observacao, registrado_por, criado_em)
                   VALUES (?, ?, 'SALDO_INICIAL', ?, 'Saldo existente na migração', 'migracao',
                           COALESCE(?, CURRENT_TIMESTAMP))""",
                (produto_id, local, dif, ts))
            criados += 1
        else:
            conn.execute(
                """INSERT INTO movimentacoes (produto_id, estoque_local, tipo, quantidade,
                                              observacao, registrado_por)
                   VALUES (?, ?, 'AJUSTE_NEGATIVO', ?,
                           'Migração: o histórico anterior somava mais que o saldo do estoque', 'migracao')""",
                (produto_id, local, -dif))
            corrigidos += 1
            avisos.append(f"produto {produto_id} ({local}): histórico anterior somava {historico:g}, "
                          f"saldo real é {saldo:g}; ajuste de {-dif:g} registrado")
    return criados, corrigidos


def migrar(caminho, fazer_backup=True):
    caminho = Path(caminho)
    msgs, avisos = [], []
    backup = None
    if fazer_backup:
        backup = Path(f"{caminho}.{datetime.now():%Y%m%d-%H%M%S-%f}.bak")
        shutil.copy(caminho, backup)

    conn = sqlite3.connect(caminho)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.isolation_level = None
    try:
        conn.execute("BEGIN")

        if "itens_compptra_quantidade" in _colunas(conn, "itens_da_compra"):
            conn.execute("ALTER TABLE itens_da_compra "
                         "RENAME COLUMN itens_compptra_quantidade TO itens_compra_quantidade")
            msgs.append("coluna itens_compra_quantidade corrigida")
        if "compra_id" in _colunas(conn, "compras"):
            conn.execute("ALTER TABLE compras RENAME COLUMN compra_id TO compras_id")
            msgs.append("compras.compras_id restaurado (nome usado pela equipe)")

        if "fornecedor_id" not in _colunas(conn, "produtos"):
            conn.execute("ALTER TABLE produtos ADD COLUMN fornecedor_id "
                         "INTEGER REFERENCES fornecedores(fornecedor_id)")
            msgs.append("produtos.fornecedor_id criada")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_produtos_fornecedor ON produtos (fornecedor_id)")
        if "produto_estoque_maximo" not in _colunas(conn, "produtos"):
            conn.execute("ALTER TABLE produtos ADD COLUMN produto_estoque_maximo REAL")
            msgs.append("produtos.produto_estoque_maximo criada (vazia: preencher por produto)")

        sql_atual = _sql_da_tabela(conn, "movimentacoes")
        precisa_conciliar = False
        if sql_atual is None:
            conn.execute(_SQL_CRIAR_MOVIMENTACOES.format(nome="movimentacoes"))
            msgs.append("tabela movimentacoes criada")
            precisa_conciliar = True
        elif "AJUSTE_POSITIVO" not in sql_atual:
            conn.execute(_SQL_CRIAR_MOVIMENTACOES.format(nome="movimentacoes_nova"))
            conn.execute("""
                INSERT INTO movimentacoes_nova
                    (movimentacao_id, produto_id, estoque_local, tipo, quantidade, compra_id,
                     observacao, registrado_por, criado_em)
                SELECT movimentacao_id, produto_id, estoque_local,
                       CASE WHEN tipo = 'AJUSTE' THEN 'AJUSTE_NEGATIVO' ELSE tipo END,
                       quantidade, compra_id,
                       CASE WHEN tipo = 'AJUSTE'
                            THEN COALESCE(observacao, '') || ' [migração: direção do ajuste assumida como negativa]'
                            ELSE observacao END,
                       registrado_por, criado_em
                FROM movimentacoes""")
            n_ajustes = conn.execute("SELECT COUNT(*) FROM movimentacoes WHERE tipo = 'AJUSTE'").fetchone()[0]
            conn.execute("DROP TABLE movimentacoes")
            conn.execute("ALTER TABLE movimentacoes_nova RENAME TO movimentacoes")
            msgs.append("tabela movimentacoes reconstruída com os tipos AJUSTE_POSITIVO/AJUSTE_NEGATIVO")
            if n_ajustes:
                avisos.append(f"{n_ajustes} movimentação(ões) 'AJUSTE' antiga(s) foram marcadas como "
                              "AJUSTE_NEGATIVO (o tipo antigo não informava a direção). Confira se é o caso.")
            precisa_conciliar = True
        conn.execute("CREATE INDEX IF NOT EXISTS idx_mov_produto ON movimentacoes(produto_id, criado_em)")

        if precisa_conciliar:
            criados, corrigidos = _conciliar_historico(conn, avisos)
            msgs.append(f"histórico reconciliado com o estoque ({criados} saldo(s) inicial(is), "
                        f"{corrigidos} correção(ões))")

        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    finally:
        conn.close()
    if backup is not None and not msgs:
        backup.unlink()
    return msgs, avisos


def main():
    caminho = Path(sys.argv[1]) if len(sys.argv) > 1 else DB_PATH
    msgs, avisos = migrar(caminho)
    print(f"Banco: {caminho}")
    if not msgs:
        print("Nada a fazer: o banco já está atualizado.")
    for m in msgs:
        print(f"- {m}")
    for a in avisos:
        print(f"ATENÇÃO: {a}")
    if msgs:
        print("(uma cópia de segurança do banco anterior foi salva ao lado do arquivo, com extensão .bak)")
    print("Migração concluída.")


if __name__ == "__main__":
    main()
