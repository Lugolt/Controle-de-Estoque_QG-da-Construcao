from database import linha_para_dict, linhas_para_lista


def inserir_compra(conn, fornecedor_id, data, nota_fiscal):
    cur = conn.execute(
        "INSERT INTO compras (fornecedor_id, compra_data, compra_nota_fiscal) VALUES (?, ?, ?)",
        (fornecedor_id, data, nota_fiscal),
    )
    return cur.lastrowid


def inserir_item(conn, compra_id, produto_id, quantidade, custo_unit):
    conn.execute(
        """INSERT INTO itens_da_compra
           (compra_id, produto_id, itens_compra_quantidade, itens_custo_unit)
           VALUES (?, ?, ?, ?)""",
        (compra_id, produto_id, quantidade, custo_unit),
    )


def listar(conn, fornecedor_id=None, data_inicio=None, data_fim=None):
    sql = """
        SELECT c.compras_id AS compra_id, c.compra_data, c.compra_nota_fiscal,
               f.fornecedor_id, f.fornecedor_nome,
               COALESCE(SUM(i.itens_compra_quantidade * i.itens_custo_unit), 0) AS valor_total
        FROM compras c
        LEFT JOIN fornecedores f   ON f.fornecedor_id = c.fornecedor_id
        LEFT JOIN itens_da_compra i ON i.compra_id = c.compras_id
        WHERE 1 = 1"""
    params = []
    if fornecedor_id:
        sql += " AND c.fornecedor_id = ?"
        params.append(fornecedor_id)
    if data_inicio:
        sql += " AND c.compra_data >= ?"
        params.append(str(data_inicio))
    if data_fim:
        sql += " AND c.compra_data <= ?"
        params.append(str(data_fim))
    sql += " GROUP BY c.compras_id ORDER BY c.compra_data DESC"
    return linhas_para_lista(conn.execute(sql, params).fetchall())


def obter(conn, compra_id):
    linha = conn.execute(
        """SELECT c.compras_id AS compra_id, c.compra_data, c.compra_nota_fiscal,
                  f.fornecedor_id, f.fornecedor_nome
           FROM compras c LEFT JOIN fornecedores f ON f.fornecedor_id = c.fornecedor_id
           WHERE c.compras_id = ?""",
        (compra_id,),
    ).fetchone()
    return linha_para_dict(linha)


def listar_itens(conn, compra_id):
    sql = """
        SELECT i.itens_id, i.produto_id, p.produto_sku, p.produto_nome,
               i.itens_compra_quantidade AS quantidade, i.itens_custo_unit AS custo_unit,
               i.itens_compra_quantidade * i.itens_custo_unit AS subtotal
        FROM itens_da_compra i JOIN produtos p ON p.produto_id = i.produto_id
        WHERE i.compra_id = ?"""
    return linhas_para_lista(conn.execute(sql, (compra_id,)).fetchall())
