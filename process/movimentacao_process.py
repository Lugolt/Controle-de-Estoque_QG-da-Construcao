from database import conexao
from exceptions import NaoEncontradoError, exigir
from repositories import (estoque_repository, movimentacao_repository as repo,
                          produto_repository)

LOCAIS = ("deposito", "loja")

TIPOS_QUE_SOMAM = ("SALDO_INICIAL", "ENTRADA", "AJUSTE_POSITIVO", "TRANSFERENCIA_ENTRADA")
TIPOS_QUE_SUBTRAEM = ("SAIDA", "PERDA", "AJUSTE_NEGATIVO", "TRANSFERENCIA_SAIDA")

TIPOS_MANUAIS = ("ENTRADA", "SAIDA", "PERDA")

_TOLERANCIA = 1e-9


def aplicar(conn, dados):
    tipo = dados.get("tipo")
    local = dados.get("local")
    quantidade = dados.get("quantidade")

    exigir(tipo in TIPOS_QUE_SOMAM + TIPOS_QUE_SUBTRAEM, "Tipo de movimentação inválido.")
    exigir(local in LOCAIS, f"Local inválido. Use: {', '.join(LOCAIS)}.")
    exigir(quantidade is not None and quantidade > 0, "A quantidade deve ser maior que zero.")

    produto = produto_repository.obter(conn, dados.get("produto_id"))
    if produto is None:
        raise NaoEncontradoError("Produto não encontrado.")
    exigir(produto["produto_ativo"] == 1, "Produto desativado: reative-o antes de movimentar.")

    if tipo in TIPOS_QUE_SUBTRAEM:
        saldo = estoque_repository.obter_saldo(conn, produto["produto_id"], local)
        exigir(
            saldo - quantidade >= -_TOLERANCIA,
            f"Saldo insuficiente em '{local}': disponível {saldo:g}, solicitado {quantidade:g}.",
        )
        variacao = -quantidade
    else:
        variacao = quantidade

    movimentacao_id = repo.inserir(conn, {
        "produto_id": produto["produto_id"],
        "local": local,
        "tipo": tipo,
        "quantidade": quantidade,
        "compra_id": dados.get("compra_id"),
        "observacao": dados.get("observacao"),
        "registrado_por": dados.get("registrado_por"),
    })
    estoque_repository.somar(conn, produto["produto_id"], local, variacao)
    return movimentacao_id


def registrar(dados):
    exigir(dados.get("tipo") in TIPOS_MANUAIS,
           f"Tipo inválido. Use: {', '.join(TIPOS_MANUAIS)}. "
           "Para ajuste use a contagem de inventário; para transferir use a transferência.")
    with conexao() as conn:
        movimentacao_id = aplicar(conn, dados)
        saldo = estoque_repository.obter_saldo(conn, dados["produto_id"], dados["local"])
    return {"movimentacao_id": movimentacao_id, "novo_saldo": saldo, "local": dados["local"]}


def transferir(dados):
    origem, destino = dados.get("origem"), dados.get("destino")
    exigir(origem in LOCAIS and destino in LOCAIS, "Origem e destino devem ser 'deposito' ou 'loja'.")
    exigir(origem != destino, "Origem e destino não podem ser iguais.")
    base = {
        "produto_id": dados.get("produto_id"),
        "quantidade": dados.get("quantidade"),
        "observacao": dados.get("observacao") or f"Transferência {origem} -> {destino}",
        "registrado_por": dados.get("registrado_por"),
    }
    with conexao() as conn:
        saida_id = aplicar(conn, {**base, "local": origem, "tipo": "TRANSFERENCIA_SAIDA"})
        entrada_id = aplicar(conn, {**base, "local": destino, "tipo": "TRANSFERENCIA_ENTRADA"})
        saldo_origem = estoque_repository.obter_saldo(conn, base["produto_id"], origem)
        saldo_destino = estoque_repository.obter_saldo(conn, base["produto_id"], destino)
    return {"movimentacoes": [saida_id, entrada_id],
            "saldo_origem": saldo_origem, "saldo_destino": saldo_destino}


def contar_inventario(dados):
    quantidade_contada = dados.get("quantidade_contada")
    local = dados.get("local")
    exigir(local in LOCAIS, f"Local inválido. Use: {', '.join(LOCAIS)}.")
    exigir(quantidade_contada is not None and quantidade_contada >= 0,
           "A quantidade contada não pode ser negativa.")

    with conexao() as conn:
        produto = produto_repository.obter(conn, dados.get("produto_id"))
        if produto is None:
            raise NaoEncontradoError("Produto não encontrado.")
        saldo_sistema = estoque_repository.obter_saldo(conn, produto["produto_id"], local)
        diferenca = quantidade_contada - saldo_sistema

        if abs(diferenca) < _TOLERANCIA:
            return {"divergencia": 0, "saldo_sistema": saldo_sistema,
                    "mensagem": "Contagem confere com o sistema. Nenhum ajuste necessário."}

        aplicar(conn, {
            "produto_id": produto["produto_id"],
            "local": local,
            "tipo": "AJUSTE_POSITIVO" if diferenca > 0 else "AJUSTE_NEGATIVO",
            "quantidade": abs(diferenca),
            "observacao": dados.get("observacao")
                          or f"Inventário: sistema {saldo_sistema:g}, contado {quantidade_contada:g}",
            "registrado_por": dados.get("registrado_por"),
        })
    return {"divergencia": diferenca, "saldo_sistema": saldo_sistema,
            "novo_saldo": quantidade_contada,
            "mensagem": "Ajuste registrado."}


def listar(produto_id=None, tipo=None, data_inicio=None, data_fim=None, limite=200):
    exigir(tipo is None or tipo in TIPOS_QUE_SOMAM + TIPOS_QUE_SUBTRAEM, "Tipo inválido.")
    exigir(1 <= limite <= 1000, "O limite deve estar entre 1 e 1000.")
    with conexao() as conn:
        return repo.listar(conn, produto_id, tipo, data_inicio, data_fim, limite)


def resumo_periodo(data_inicio=None, data_fim=None):
    with conexao() as conn:
        return repo.resumo_por_produto(conn, data_inicio, data_fim)


def auditar():
    with conexao() as conn:
        return repo.auditar_saldos(conn)
