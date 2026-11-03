from datetime import date
from typing import Optional

from fastapi import APIRouter

from process import movimentacao_process

router = APIRouter(prefix="/relatorios", tags=["Relatórios"])


@router.get("/movimentacao")
def movimentacao_por_periodo(data_inicio: Optional[date] = None, data_fim: Optional[date] = None):
    return movimentacao_process.resumo_periodo(
        str(data_inicio) if data_inicio else None,
        str(data_fim) if data_fim else None,
    )


@router.get("/auditoria")
def auditoria():
    return movimentacao_process.auditar()
