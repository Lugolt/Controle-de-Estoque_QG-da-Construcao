from database import conexao
from exceptions import NaoEncontradoError, exigir
from process import movimentacao_process
from repositories import compra_repository as repo
from repositories import fornecedor_repository, produto_repository

LOCAIS = ("deposito", "loja")


def registrar(dados):
    itens = dados.get("itens") or []
    exigir(len(itens) > 0, "A compra precisa ter ao menos um item.")
    exigir(dados.get("data"), "A data da compra é obrigatória.")
    local = dados.get("local_destino") or "deposito"
    exigir(local in LOCAIS, f"Local inválido. Use: {', '.join(LOCAIS)}.")
    for item in itens:
        exigir(item.get("quantidade", 0) > 0, "Todos os itens precisam de quantidade maior que zero.")
        exigir(item.get("custo_unit", -1) >= 0, "O custo unitário não pode ser negativo.")

    with conexao() as conn:
        exigir(fornecedor_repository.obter(conn, dados.get("fornecedor_id")), "Fornecedor não existe.")

        for item in itens:
            if produto_repository.obter(conn, item.get("produto_id")) is None:
                raise NaoEncontradoError(f"Produto {item.get('produto_id')} não encontrado.")

        compra_id = repo.inserir_compra(
            conn, dados["fornecedor_id"], str(dados["data"]), dados.get("nota_fiscal"))
        for item in itens:
            repo.inserir_item(conn, compra_id, item["produto_id"], item["quantidade"], item["custo_unit"])
            movimentacao_process.aplicar(conn, {
                "produto_id": item["produto_id"],
                "local": local,
                "tipo": "ENTRADA",
                "quantidade": item["quantidade"],
                "compra_id": compra_id,
                "observacao": f"Compra NF {dados.get('nota_fiscal') or compra_id}",
                "registrado_por": dados.get("registrado_por"),
            })
    return obter(compra_id)


def listar(fornecedor_id=None, data_inicio=None, data_fim=None):
    with conexao() as conn:
        return repo.listar(conn, fornecedor_id, data_inicio, data_fim)


def obter(compra_id):
    with conexao() as conn:
        compra = repo.obter(conn, compra_id)
        if compra is None:
            raise NaoEncontradoError("Compra não encontrada.")
        compra["itens"] = repo.listar_itens(conn, compra_id)
    compra["valor_total"] = sum(i["subtotal"] for i in compra["itens"])
    return compra
