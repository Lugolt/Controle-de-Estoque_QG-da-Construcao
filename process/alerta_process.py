from database import conexao
from repositories import produto_repository


def listar_alertas():
    with conexao() as conn:
        zerados = produto_repository.listar_com_saldo(conn, status="ZERADO")
        baixos = produto_repository.listar_com_saldo(conn, status="BAIXO")
        excesso = produto_repository.listar_com_saldo(conn, status="EXCESSO")
    return {
        "resumo": {"zerados": len(zerados), "baixos": len(baixos), "excesso": len(excesso)},
        "zerados": zerados,
        "baixos": baixos,
        "excesso": excesso,
    }

def lista_de_compras():
    with conexao() as conn:
        produtos = (produto_repository.listar_com_saldo(conn, status="ZERADO")
                    + produto_repository.listar_com_saldo(conn, status="BAIXO"))
    lista = []
    for p in produtos:
        alvo = p["produto_estoque_maximo"] or (p["produto_estoque_minimo"] * 2)
        lista.append({
            "produto_id": p["produto_id"],
            "produto_sku": p["produto_sku"],
            "produto_nome": p["produto_nome"],
            "fornecedor_nome": p["fornecedor_nome"],
            "unidade": p["produto_unidade"],
            "status": p["status"],
            "saldo_total": p["saldo_total"],
            "estoque_minimo": p["produto_estoque_minimo"],
            "quantidade_sugerida": max(alvo - p["saldo_total"], 0),
        })
    lista.sort(key=lambda x: (x["fornecedor_nome"] or "zzz", x["produto_nome"]))
    return lista
