from fastapi import APIRouter

from models.schemas import CategoriaIn
from process import categoria_process

router = APIRouter(prefix="/categorias", tags=["Categorias"])


@router.get("")
def listar():
    return categoria_process.listar()


@router.get("/{categoria_id}")
def obter(categoria_id: int):
    return categoria_process.obter(categoria_id)


@router.post("", status_code=201)
def criar(corpo: CategoriaIn):
    return categoria_process.criar(corpo.model_dump())


@router.put("/{categoria_id}")
def atualizar(categoria_id: int, corpo: CategoriaIn):
    return categoria_process.atualizar(categoria_id, corpo.model_dump())
