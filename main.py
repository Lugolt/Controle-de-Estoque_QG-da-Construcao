from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from controllers import (alerta_controller, categoria_controller, compra_controller,
                         fornecedor_controller, movimentacao_controller,
                         produto_controller, relatorio_controller)
from exceptions import NaoEncontradoError, RegraDeNegocioError

app = FastAPI(title="Controle de Estoque - QG da Construção", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(NaoEncontradoError)
def tratar_nao_encontrado(request: Request, erro: NaoEncontradoError):
    return JSONResponse(status_code=404, content={"erro": str(erro)})


@app.exception_handler(RegraDeNegocioError)
def tratar_regra_de_negocio(request: Request, erro: RegraDeNegocioError):
    return JSONResponse(status_code=422, content={"erro": str(erro)})


for modulo in (categoria_controller, fornecedor_controller, produto_controller,
               movimentacao_controller, compra_controller, alerta_controller,
               relatorio_controller):
    app.include_router(modulo.router)


@app.get("/", tags=["Saúde"])
def raiz():
    return {"status": "ok", "docs": "/docs"}
