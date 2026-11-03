from fastapi import APIRouter

from process import alerta_process

router = APIRouter(prefix="/alertas", tags=["Alertas"])


@router.get("")
def listar_alertas():
    return alerta_process.listar_alertas()


@router.get("/lista-de-compras")
def lista_de_compras():
    return alerta_process.lista_de_compras()
