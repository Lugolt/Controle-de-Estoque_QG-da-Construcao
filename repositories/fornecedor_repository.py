from database import linha_para_dict, linhas_para_lista

_COLUNAS = "fornecedor_id, fornecedor_nome, fornecedor_cnpj, fornecedor_telefone"


def listar(conn, busca=None):
    sql = f"SELECT {_COLUNAS} FROM fornecedores"
    params = []
    if busca:
        sql += " WHERE fornecedor_nome LIKE ?"
        params.append(f"%{busca}%")
    sql += " ORDER BY fornecedor_nome"
    return linhas_para_lista(conn.execute(sql, params).fetchall())


def obter(conn, fornecedor_id):
    linha = conn.execute(
        f"SELECT {_COLUNAS} FROM fornecedores WHERE fornecedor_id = ?", (fornecedor_id,)
    ).fetchone()
    return linha_para_dict(linha)


def inserir(conn, dados):
    cur = conn.execute(
        "INSERT INTO fornecedores (fornecedor_nome, fornecedor_cnpj, fornecedor_telefone) "
        "VALUES (:nome, :cnpj, :telefone)",
        dados,
    )
    return cur.lastrowid


def atualizar(conn, fornecedor_id, dados):
    conn.execute(
        "UPDATE fornecedores SET fornecedor_nome = :nome, fornecedor_cnpj = :cnpj, "
        "fornecedor_telefone = :telefone WHERE fornecedor_id = :id",
        {**dados, "id": fornecedor_id},
    )
