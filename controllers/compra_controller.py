from datetime import date
from typing import Optional

from fastapi import APIRouter

from models.schemas import CompraIn
from process import compra_process

router = APIRouter(prefix="/compras", tags=["Compras"])


@router.get("")
def listar(
    fornecedor_id: Optional[int] = None,
    data_inicio: Optional[date] = None,
    data_fim: Optional[date] = None,
):
    return compra_process.listar(fornecedor_id, data_inicio, data_fim)


@router.get("/{compra_id}")
def obter(compra_id: int):
    return compra_process.obter(compra_id)


@router.post("", status_code=201)
def registrar(corpo: CompraIn):
    return compra_process.registrar(corpo.model_dump())
