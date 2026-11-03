from typing import Optional

from fastapi import APIRouter

from models.schemas import FornecedorIn
from process import fornecedor_process

router = APIRouter(prefix="/fornecedores", tags=["Fornecedores"])


@router.get("")
def listar(busca: Optional[str] = None):
    return fornecedor_process.listar(busca)


@router.get("/{fornecedor_id}")
def obter(fornecedor_id: int):
    return fornecedor_process.obter(fornecedor_id)


@router.post("", status_code=201)
def criar(corpo: FornecedorIn):
    return fornecedor_process.criar(corpo.model_dump())


@router.put("/{fornecedor_id}")
def atualizar(fornecedor_id: int, corpo: FornecedorIn):
    return fornecedor_process.atualizar(fornecedor_id, corpo.model_dump())
