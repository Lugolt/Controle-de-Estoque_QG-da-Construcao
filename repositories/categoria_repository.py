from database import linha_para_dict, linhas_para_lista


def listar(conn):
    linhas = conn.execute(
        "SELECT categoria_id, categoria_nome FROM categorias ORDER BY categoria_nome"
    ).fetchall()
    return linhas_para_lista(linhas)


def obter(conn, categoria_id):
    linha = conn.execute(
        "SELECT categoria_id, categoria_nome FROM categorias WHERE categoria_id = ?",
        (categoria_id,),
    ).fetchone()
    return linha_para_dict(linha)


def inserir(conn, nome):
    cur = conn.execute("INSERT INTO categorias (categoria_nome) VALUES (?)", (nome,))
    return cur.lastrowid


def atualizar(conn, categoria_id, nome):
    conn.execute(
        "UPDATE categorias SET categoria_nome = ? WHERE categoria_id = ?",
        (nome, categoria_id),
    )
