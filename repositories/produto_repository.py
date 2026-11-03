from database import linha_para_dict, linhas_para_lista

_SQL_COM_SALDO = """
SELECT * FROM (
    SELECT
        p.produto_id, p.produto_sku, p.produto_nome, p.produto_descricao,
        p.categoria_id, c.categoria_nome,
        p.fornecedor_id, f.fornecedor_nome,
        p.produto_unidade, p.produto_preco_custo, p.produto_preco_venda,
        p.produto_estoque_minimo, p.produto_estoque_maximo, p.produto_ativo,
        COALESCE(SUM(e.estoque_quantidade), 0) AS saldo_total,
        COALESCE(SUM(CASE WHEN e.estoque_local = 'deposito' THEN e.estoque_quantidade END), 0) AS saldo_deposito,
        COALESCE(SUM(CASE WHEN e.estoque_local = 'loja'     THEN e.estoque_quantidade END), 0) AS saldo_loja
    FROM produtos p
    LEFT JOIN categorias c   ON c.categoria_id  = p.categoria_id
    LEFT JOIN fornecedores f ON f.fornecedor_id = p.fornecedor_id
    LEFT JOIN estoque e      ON e.produto_id    = p.produto_id
    GROUP BY p.produto_id
) t
"""

_SQL_STATUS = """
CASE
    WHEN saldo_total <= 0 THEN 'ZERADO'
    WHEN produto_estoque_minimo > 0 AND saldo_total <= produto_estoque_minimo THEN 'BAIXO'
    WHEN produto_estoque_maximo IS NOT NULL AND saldo_total > produto_estoque_maximo THEN 'EXCESSO'
    ELSE 'NORMAL'
END
"""


def listar_com_saldo(conn, busca=None, categoria_id=None, status=None, incluir_desativados=False):
    sql = f"SELECT *, {_SQL_STATUS} AS status FROM ({_SQL_COM_SALDO}) WHERE 1 = 1"
    params = []
    if not incluir_desativados:
        sql += " AND produto_ativo = 1"
    if busca:
        sql += " AND (produto_nome LIKE ? OR produto_sku LIKE ?)"
        params += [f"%{busca}%", f"%{busca}%"]
    if categoria_id:
        sql += " AND categoria_id = ?"
        params.append(categoria_id)
    if status:
        sql += f" AND ({_SQL_STATUS}) = ?"
        params.append(status)
    sql += " ORDER BY produto_nome"
    return linhas_para_lista(conn.execute(sql, params).fetchall())


def obter_com_saldo(conn, produto_id):
    sql = f"SELECT *, {_SQL_STATUS} AS status FROM ({_SQL_COM_SALDO}) WHERE produto_id = ?"
    return linha_para_dict(conn.execute(sql, (produto_id,)).fetchone())


def obter(conn, produto_id):
    linha = conn.execute(
        "SELECT * FROM produtos WHERE produto_id = ?", (produto_id,)
    ).fetchone()
    return linha_para_dict(linha)


def inserir(conn, dados):
    cur = conn.execute(
        """INSERT INTO produtos
           (produto_sku, produto_nome, produto_descricao, categoria_id, fornecedor_id,
            produto_unidade, produto_preco_custo, produto_preco_venda,
            produto_estoque_minimo, produto_estoque_maximo)
           VALUES (:sku, :nome, :descricao, :categoria_id, :fornecedor_id,
                   :unidade, :preco_custo, :preco_venda, :estoque_minimo, :estoque_maximo)""",
        dados,
    )
    return cur.lastrowid


def atualizar(conn, produto_id, dados):
    conn.execute(
        """UPDATE produtos SET
               produto_sku = :sku, produto_nome = :nome, produto_descricao = :descricao,
               categoria_id = :categoria_id, fornecedor_id = :fornecedor_id,
               produto_unidade = :unidade, produto_preco_custo = :preco_custo,
               produto_preco_venda = :preco_venda,
               produto_estoque_minimo = :estoque_minimo,
               produto_estoque_maximo = :estoque_maximo
           WHERE produto_id = :id""",
        {**dados, "id": produto_id},
    )


def definir_ativo(conn, produto_id, ativo):
    conn.execute(
        "UPDATE produtos SET produto_ativo = ? WHERE produto_id = ?",
        (1 if ativo else 0, produto_id),
    )
