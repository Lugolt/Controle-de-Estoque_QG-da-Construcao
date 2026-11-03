from database import linhas_para_lista


def inserir(conn, dados):
    cur = conn.execute(
        """INSERT INTO movimentacoes
           (produto_id, estoque_local, tipo, quantidade, compra_id, observacao, registrado_por)
           VALUES (:produto_id, :local, :tipo, :quantidade, :compra_id, :observacao, :registrado_por)""",
        dados,
    )
    return cur.lastrowid


def listar(conn, produto_id=None, tipo=None, data_inicio=None, data_fim=None, limite=200):
    sql = """
        SELECT m.movimentacao_id, m.produto_id, p.produto_sku, p.produto_nome,
               m.estoque_local, m.tipo, m.quantidade, m.compra_id,
               m.observacao, m.registrado_por, m.criado_em
        FROM movimentacoes m
        JOIN produtos p ON p.produto_id = m.produto_id
        WHERE 1 = 1"""
    params = []
    if produto_id:
        sql += " AND m.produto_id = ?"
        params.append(produto_id)
    if tipo:
        sql += " AND m.tipo = ?"
        params.append(tipo)
    if data_inicio:
        sql += " AND date(m.criado_em) >= date(?)"
        params.append(data_inicio)
    if data_fim:
        sql += " AND date(m.criado_em) <= date(?)"
        params.append(data_fim)
    sql += " ORDER BY m.criado_em DESC, m.movimentacao_id DESC LIMIT ?"
    params.append(limite)
    return linhas_para_lista(conn.execute(sql, params).fetchall())


def resumo_por_produto(conn, data_inicio=None, data_fim=None):
    sql = """
        SELECT p.produto_id, p.produto_sku, p.produto_nome, p.produto_unidade,
               COALESCE(SUM(CASE WHEN m.tipo = 'ENTRADA' THEN m.quantidade END), 0) AS total_entradas,
               COALESCE(SUM(CASE WHEN m.tipo = 'SAIDA'   THEN m.quantidade END), 0) AS total_saidas,
               COALESCE(SUM(CASE WHEN m.tipo = 'PERDA'   THEN m.quantidade END), 0) AS total_perdas
        FROM produtos p
        JOIN movimentacoes m ON m.produto_id = p.produto_id
        WHERE 1 = 1"""
    params = []
    if data_inicio:
        sql += " AND date(m.criado_em) >= date(?)"
        params.append(data_inicio)
    if data_fim:
        sql += " AND date(m.criado_em) <= date(?)"
        params.append(data_fim)
    sql += " GROUP BY p.produto_id ORDER BY total_saidas DESC"
    return linhas_para_lista(conn.execute(sql, params).fetchall())


def auditar_saldos(conn):
    sql = """
        SELECT e.produto_id, p.produto_nome, e.estoque_local,
               e.estoque_quantidade AS saldo_estoque,
               COALESCE((SELECT SUM(CASE
                    WHEN m.tipo IN ('SALDO_INICIAL','ENTRADA','AJUSTE_POSITIVO','TRANSFERENCIA_ENTRADA')
                         THEN m.quantidade ELSE -m.quantidade END)
                  FROM movimentacoes m
                  WHERE m.produto_id = e.produto_id AND m.estoque_local = e.estoque_local), 0)
               AS saldo_pelo_historico
        FROM estoque e
        JOIN produtos p ON p.produto_id = e.produto_id
        WHERE ABS(e.estoque_quantidade - saldo_pelo_historico) > 0.0001"""
    return linhas_para_lista(conn.execute(sql).fetchall())
