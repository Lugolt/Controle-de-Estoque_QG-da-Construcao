import sqlite3

from database import conexao
from exceptions import NaoEncontradoError, RegraDeNegocioError, exigir
from repositories import (categoria_repository, estoque_repository,
                          fornecedor_repository, produto_repository as repo)

STATUS_VALIDOS = ("ZERADO", "BAIXO", "NORMAL", "EXCESSO")
LOCAIS = ("deposito", "loja")

def listar(busca=None, categoria_id=None, status=None, incluir_desativados=False):
    if status is not None:
        exigir(status in STATUS_VALIDOS, f"Status inválido. Use: {', '.join(STATUS_VALIDOS)}.")
    with conexao() as conn:
        return repo.listar_com_saldo(conn, busca, categoria_id, status, incluir_desativados)

def obter(produto_id):
    with conexao() as conn:
        produto = repo.obter_com_saldo(conn, produto_id)
    if produto is None:
        raise NaoEncontradoError("Produto não encontrado.")
    return produto

def _validar(conn, dados):
    nome = (dados.get("nome") or "").strip()
    exigir(nome, "O nome do produto é obrigatório.")

    minimo = dados.get("estoque_minimo") or 0
    maximo = dados.get("estoque_maximo")
    exigir(minimo >= 0, "O estoque mínimo não pode ser negativo.")
    if maximo is not None:
        exigir(maximo >= minimo, "O estoque máximo deve ser maior ou igual ao mínimo.")

    for campo in ("preco_custo", "preco_venda"):
        valor = dados.get(campo)
        exigir(valor is None or valor >= 0, f"O campo {campo} não pode ser negativo.")

    categoria_id = dados.get("categoria_id")
    if categoria_id is not None:
        exigir(categoria_repository.obter(conn, categoria_id), "Categoria não existe.")
    fornecedor_id = dados.get("fornecedor_id")
    if fornecedor_id is not None:
        exigir(fornecedor_repository.obter(conn, fornecedor_id), "Fornecedor não existe.")

    return {
        "sku": (dados.get("sku") or None),
        "nome": nome,
        "descricao": dados.get("descricao"),
        "categoria_id": categoria_id,
        "fornecedor_id": fornecedor_id,
        "unidade": dados.get("unidade") or "un",
        "preco_custo": dados.get("preco_custo"),
        "preco_venda": dados.get("preco_venda"),
        "estoque_minimo": minimo,
        "estoque_maximo": maximo,
    }

def criar(dados):
    try:
        with conexao() as conn:
            limpos = _validar(conn, dados)
            novo_id = repo.inserir(conn, limpos)
            for local in LOCAIS:
                estoque_repository.somar(conn, novo_id, local, 0)
    except sqlite3.IntegrityError:
        raise RegraDeNegocioError("Já existe um produto com esse código (SKU).")
    return obter(novo_id)

def atualizar(produto_id, dados):
    obter(produto_id)
    try:
        with conexao() as conn:
            limpos = _validar(conn, dados)
            repo.atualizar(conn, produto_id, limpos)
    except sqlite3.IntegrityError:
        raise RegraDeNegocioError("Já existe um produto com esse código (SKU).")
    return obter(produto_id)

def desativar(produto_id):
    obter(produto_id)
    with conexao() as conn:
        repo.definir_ativo(conn, produto_id, False)
    return obter(produto_id)

def reativar(produto_id):
    obter(produto_id)
    with conexao() as conn:
        repo.definir_ativo(conn, produto_id, True)
    return obter(produto_id)
