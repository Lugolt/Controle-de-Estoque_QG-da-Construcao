from datetime import date
from typing import List, Literal, Optional

from pydantic import BaseModel, Field

Local = Literal["deposito", "loja"]


class CategoriaIn(BaseModel):
    nome: str


class FornecedorIn(BaseModel):
    nome: str
    cnpj: Optional[str] = None
    telefone: Optional[str] = None


class ProdutoIn(BaseModel):
    sku: Optional[str] = None
    nome: str
    descricao: Optional[str] = None
    categoria_id: Optional[int] = None
    fornecedor_id: Optional[int] = None
    unidade: str = "un"
    preco_custo: Optional[float] = Field(default=None, ge=0)
    preco_venda: Optional[float] = Field(default=None, ge=0)
    estoque_minimo: float = Field(default=0, ge=0)
    estoque_maximo: Optional[float] = Field(default=None, ge=0)


class MovimentacaoIn(BaseModel):
    produto_id: int
    local: Local
    tipo: Literal["ENTRADA", "SAIDA", "PERDA"]
    quantidade: float = Field(gt=0)
    observacao: Optional[str] = None
    registrado_por: Optional[str] = None


class TransferenciaIn(BaseModel):
    produto_id: int
    origem: Local
    destino: Local
    quantidade: float = Field(gt=0)
    observacao: Optional[str] = None
    registrado_por: Optional[str] = None


class InventarioIn(BaseModel):
    produto_id: int
    local: Local
    quantidade_contada: float = Field(ge=0)
    observacao: Optional[str] = None
    registrado_por: Optional[str] = None


class ItemCompraIn(BaseModel):
    produto_id: int
    quantidade: float = Field(gt=0)
    custo_unit: float = Field(ge=0)


class CompraIn(BaseModel):
    fornecedor_id: int
    data: date
    nota_fiscal: Optional[str] = None
    local_destino: Local = "deposito"
    registrado_por: Optional[str] = None
    itens: List[ItemCompraIn]
