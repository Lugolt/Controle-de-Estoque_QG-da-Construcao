def obter_saldo(conn, produto_id, local):
    linha = conn.execute(
        "SELECT estoque_quantidade FROM estoque WHERE produto_id = ? AND estoque_local = ?",
        (produto_id, local),
    ).fetchone()
    return linha["estoque_quantidade"] if linha else 0.0


def somar(conn, produto_id, local, variacao):
    conn.execute(
        """INSERT INTO estoque (produto_id, estoque_local, estoque_quantidade)
           VALUES (?, ?, ?)
           ON CONFLICT (produto_id, estoque_local)
           DO UPDATE SET estoque_quantidade = estoque_quantidade + excluded.estoque_quantidade""",
        (produto_id, local, variacao),
    )
