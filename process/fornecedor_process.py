from database import conexao
from exceptions import NaoEncontradoError, exigir
from repositories import fornecedor_repository as repo


def _validar(dados):
    exigir((dados.get("nome") or "").strip(), "O nome do fornecedor é obrigatório.")
    return {
        "nome": dados["nome"].strip(),
        "cnpj": (dados.get("cnpj") or None),
        "telefone": (dados.get("telefone") or None),
    }


def listar(busca=None):
    with conexao() as conn:
        return repo.listar(conn, busca)


def obter(fornecedor_id):
    with conexao() as conn:
        fornecedor = repo.obter(conn, fornecedor_id)
    if fornecedor is None:
        raise NaoEncontradoError("Fornecedor não encontrado.")
    return fornecedor


def criar(dados):
    limpos = _validar(dados)
    with conexao() as conn:
        novo_id = repo.inserir(conn, limpos)
    return obter(novo_id)


def atualizar(fornecedor_id, dados):
    obter(fornecedor_id)
    limpos = _validar(dados)
    with conexao() as conn:
        repo.atualizar(conn, fornecedor_id, limpos)
    return obter(fornecedor_id)
