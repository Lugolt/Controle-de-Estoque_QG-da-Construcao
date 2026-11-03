import sqlite3

from database import conexao
from exceptions import NaoEncontradoError, RegraDeNegocioError, exigir
from repositories import categoria_repository as repo


def listar():
    with conexao() as conn:
        return repo.listar(conn)


def obter(categoria_id):
    with conexao() as conn:
        categoria = repo.obter(conn, categoria_id)
    if categoria is None:
        raise NaoEncontradoError("Categoria não encontrada.")
    return categoria


def criar(dados):
    nome = (dados.get("nome") or "").strip()
    exigir(nome, "O nome da categoria é obrigatório.")
    try:
        with conexao() as conn:
            novo_id = repo.inserir(conn, nome)
    except sqlite3.IntegrityError:
        raise RegraDeNegocioError("Já existe uma categoria com esse nome.")
    return obter(novo_id)


def atualizar(categoria_id, dados):
    obter(categoria_id)
    nome = (dados.get("nome") or "").strip()
    exigir(nome, "O nome da categoria é obrigatório.")
    try:
        with conexao() as conn:
            repo.atualizar(conn, categoria_id, nome)
    except sqlite3.IntegrityError:
        raise RegraDeNegocioError("Já existe uma categoria com esse nome.")
    return obter(categoria_id)
