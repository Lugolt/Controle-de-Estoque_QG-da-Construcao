from datetime import date
from typing import Optional

from fastapi import APIRouter

from models.schemas import InventarioIn, MovimentacaoIn, TransferenciaIn
from process import movimentacao_process

router = APIRouter(prefix="/movimentacoes", tags=["Movimentações"])


@router.get("")
def listar(
    produto_id: Optional[int] = None,
    tipo: Optional[str] = None,
    data_inicio: Optional[date] = None,
    data_fim: Optional[date] = None,
    limite: int = 200,
):
    return movimentacao_process.listar(
        produto_id, tipo,
        str(data_inicio) if data_inicio else None,
        str(data_fim) if data_fim else None,
        limite,
    )


@router.post("", status_code=201)
def registrar(corpo: MovimentacaoIn):
    return movimentacao_process.registrar(corpo.model_dump())


@router.post("/transferencia", status_code=201)
def transferir(corpo: TransferenciaIn):
    return movimentacao_process.transferir(corpo.model_dump())


@router.post("/inventario", status_code=201)
def contar_inventario(corpo: InventarioIn):
    return movimentacao_process.contar_inventario(corpo.model_dump())
