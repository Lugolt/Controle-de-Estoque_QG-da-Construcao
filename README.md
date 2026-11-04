# API de Controle de Estoque — QG da Construção

## Como rodar

```bash
python -m venv .venv                 # cria um ambiente virtual isolado
.venv\Scripts\activate               # Windows   |   Linux/Mac: source .venv/bin/activate
pip install -r requirements.txt      # instala as dependências
python aplicar_migracao.py           # leva o banco ao modelo da API (seguro repetir)
uvicorn main:app --reload            # sobe a API
```

Para o back-end abra http://127.0.0.1:8000/docs: o Swagger permite testar todas as rotas pelo navegador.


## Rodar em caso de erro

```
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m uvicorn main:app --reload
```

## Para o Front-end
**Abra um terminal na pasta em que está o html do projeto e rode o comando abaixo e abra http://127.0.0.1:5173/interface_do_sistema_integrada.html**

```
python -m http.server 5173
```



## Estrutura

| Pasta / arquivo | Papel |
|---|---|
| `main.py` | Inicia a API, registra as rotas, o CORS (front em `localhost:5173`) e o tratamento de erros |
| `controllers/` | Recebe a requisição HTTP e chama o `process`. Não tem regra de negócio |
| `process/` | Regras de negócio e transações |
| `repositories/` | SQL de cada tabela. Não tem regra de negócio |
| `models/schemas.py` | Formato e validação dos dados de entrada (Pydantic) |
| `database.py` | Conexão com o banco e transação |
| `exceptions.py` | Erros de negócio |
| `aplicar_migracao.py` | Migração do banco |
| `tests/` | Testes automatizados |

Fluxo de uma chamada: `controller → process → repository → banco`.
Cada camada só conhece a de baixo. O `process` recebe e devolve `dict`/listas simples e não depende do
framework web, por isso é testável sozinho.

**Transações.** Cada função do `process` abre uma transação com `with conexao() as conn:`. Ao sair do bloco
sem erro há `commit`; se ocorrer uma exceção há `rollback` e nada fica gravado. Os repositories recebem
essa `conn` como primeiro parâmetro. A conexão sempre liga `PRAGMA foreign_keys = ON`, porque o SQLite
não valida chaves estrangeiras sem isso.

**Erros.** `NaoEncontradoError` vira HTTP 404 e `RegraDeNegocioError` vira HTTP 422, ambos com a
mensagem em `{"erro": "..."}`. Dados fora do formato esperado também geram 422, vindos do Pydantic.
Dentro do `process`, a função `exigir(condicao, mensagem)` lança `RegraDeNegocioError` quando a condição é falsa.

## Convenções do Python usadas aqui

- **Nomes:** `snake_case` para funções, variáveis e arquivos; `PascalCase` para classes; `MAIUSCULAS` para constantes.
- **Indentação (4 espaços) define o bloco**, não há chaves `{}`.
- **Nem tudo precisa ser classe:** um arquivo (módulo) agrupa funções. Por isso `produto_process.criar(...)` é uma função dentro de `produto_process.py`.
- **`with`** abre um recurso e o fecha sozinho, inclusive se ocorrer um erro.
- **`dict`** (`{"nome": "x"}`) representa as linhas do banco e os dados trafegados.
- **`None`** representa a ausência de valor; `Optional[int]` significa "int ou None".
- **`__init__.py`** marca uma pasta como pacote, permitindo importar de dentro dela.
- **`_nome`** (com sublinhado) indica uso interno do arquivo.

## Rotas principais

| Método e rota | O que faz |
|---|---|
| `GET /produtos?busca=&status=&categoria_id=&incluir_desativados=` | Lista com saldo (depósito, loja, total) e status. `busca` procura no nome e no código (SKU). `status`: `ZERADO`, `BAIXO`, `NORMAL` ou `EXCESSO` |
| `POST /produtos`, `PUT /produtos/{id}` | Cadastra e edita |
| `POST /produtos/{id}/desativar` | Desativa o produto (nunca apaga) |
| `POST /produtos/{id}/reativar` | Reativa um produto desativado |
| `POST /movimentacoes` | Entrada, saída ou perda |
| `POST /movimentacoes/transferencia` | Depósito ↔ loja |
| `POST /movimentacoes/inventario` | Contagem física: grava a divergência como ajuste |
| `GET /movimentacoes?produto_id=&tipo=&data_inicio=&data_fim=&limite=` | Histórico, do mais recente ao mais antigo (limite entre 1 e 1000, padrão 200) |
| `POST /compras`, `GET /compras`, `GET /compras/{id}` | Compra com itens; já gera entradas no estoque |
| `GET /alertas` | Painel: zerados, baixos e em excesso, com um resumo das contagens |
| `GET /alertas/lista-de-compras` | O que comprar, com quantidade sugerida |
| `GET /relatorios/movimentacao?data_inicio=&data_fim=` | Entradas, saídas e perdas por produto no período, dos mais vendidos para os menos |
| `GET /relatorios/auditoria` | Divergências entre saldo e histórico. Lista vazia = tudo certo |
| CRUD de `/categorias` e `/fornecedores` | Cadastros básicos (sem exclusão) |

Saída no balcão (`POST /movimentacoes`):
```json
{"produto_id": 1, "local": "loja", "tipo": "SAIDA", "quantidade": 3, "registrado_por": "Guilherme"}
```

Compra de fornecedor (`POST /compras`); `local_destino` é opcional e o padrão é `deposito`:
```json
{
  "fornecedor_id": 1, "data": "2026-10-01", "nota_fiscal": "12345", "local_destino": "deposito",
  "registrado_por": "Guilherme",
  "itens": [{"produto_id": 1, "quantidade": 10, "custo_unit": 50.0}]
}
```

Contagem de inventário (`POST /movimentacoes/inventario`):
```json
{"produto_id": 1, "local": "loja", "quantidade_contada": 6}
```

## Regras importantes

**Saldo e movimentações**

- O saldo **nunca** é editado direto. Toda alteração grava uma linha em `movimentacoes` e atualiza `estoque` na mesma transação: ou as duas acontecem, ou nenhuma.
- Tipos que **somam** ao saldo: `SALDO_INICIAL`, `ENTRADA`, `AJUSTE_POSITIVO`, `TRANSFERENCIA_ENTRADA`.
  Tipos que **subtraem**: `SAIDA`, `PERDA`, `AJUSTE_NEGATIVO`, `TRANSFERENCIA_SAIDA`.
- O que o usuário lança diretamente é apenas `ENTRADA`, `SAIDA` e `PERDA`. Ajuste só nasce da contagem de inventário, e transferência tem rota própria.
- A quantidade de uma movimentação é sempre maior que zero; a direção vem do tipo.
- Saída, perda ou transferência maior que o saldo do **local** é bloqueada, e nada é gravado.
- Comparações de saldo usam uma pequena tolerância (`1e-9`) para evitar erros de arredondamento de decimais.
- Movimentações só são aceitas para produtos existentes e **ativos**.
- Movimentações não são apagadas nem editadas; erro de lançamento se corrige com um novo lançamento.

**Transferência**

- Move quantidade entre `deposito` e `loja` e gera duas movimentações (`TRANSFERENCIA_SAIDA` na origem e `TRANSFERENCIA_ENTRADA` no destino) na mesma transação. Origem e destino não podem ser iguais.
- Se faltar saldo na origem, nenhuma das duas é gravada.

**Inventário**

- O usuário informa quanto **contou**; o sistema compara com o saldo e grava a diferença como `AJUSTE_POSITIVO` ou `AJUSTE_NEGATIVO`. Assim fica registrado exatamente quanto o real divergia do que se acreditava ter.
- Se a contagem for igual ao saldo, nada é gravado.
- A quantidade contada pode ser zero, nunca negativa.

**Compras**

- Uma compra grava, na mesma transação, a compra, seus itens e uma `ENTRADA` por item (com o `compra_id` e a nota fiscal na observação).
- Todos os produtos são validados **antes** de gravar qualquer coisa. Exige-se fornecedor existente, ao menos um item, quantidade maior que zero e custo não negativo.

**Produtos**

- Produtos não são apagados, apenas desativados, para que o histórico de movimentações continue existindo. Um produto desativado sai das listagens (a menos que `incluir_desativados=true`) e não pode ser movimentado até ser reativado.
- Ao criar um produto, são criadas as duas linhas de saldo (`deposito` e `loja`) zeradas, para ele aparecer nas consultas.
- O estoque máximo, quando informado, deve ser maior ou igual ao mínimo. Mínimo e máximo não podem ser negativos, nem os preços.
- O `sku` é único.

**Status do produto**

Não existe coluna de status: ele é calculado na consulta, com a soma de depósito + loja, nesta ordem:

| Status | Condição |
|---|---|
| `ZERADO` | saldo total ≤ 0 |
| `BAIXO` | mínimo > 0 e saldo total ≤ mínimo (saldo igual ao mínimo já conta como baixo) |
| `EXCESSO` | existe máximo cadastrado e saldo total > máximo |
| `NORMAL` | demais casos |

Produto sem mínimo (0) nunca fica `BAIXO`, e produto sem máximo nunca fica em `EXCESSO`.

**Lista de compras**

- Inclui os produtos `ZERADO` e `BAIXO`, ordenados por fornecedor e nome (os sem fornecedor ficam no fim).
- `quantidade_sugerida = alvo − saldo total`, onde o alvo é o estoque máximo, se existir, ou o dobro do mínimo. É apenas uma sugestão para o gerente decidir.

**Auditoria**

`GET /relatorios/auditoria` compara, por produto e local, o saldo de `estoque` com a soma das movimentações. Qualquer linha retornada é uma divergência; a lista deve vir vazia.

## Banco de dados e migração

O banco do projeto é o `PJIdb_v2.db` (SQLite). A versão enviada nesta pasta **já foi migrada**.
Para usar outro arquivo: `python aplicar_migracao.py caminho\outro.db` (também funciona definindo a variável de ambiente `ESTOQUE_DB`).

`aplicar_migracao.py` aceita a versão da equipe e a primeira versão do banco, e só faz o que falta:

1. Garante `itens_da_compra.itens_compra_quantidade` (nome corrigido) e `compras.compras_id`. Se vier como `compra_id` de uma migração antiga, volta para `compras_id`.
2. Garante `produtos.fornecedor_id` (com índice) e cria `produtos.produto_estoque_maximo`, vazio: precisa ser preenchido por produto para o alerta de excesso funcionar.
3. Cria ou reconstrói `movimentacoes` com os tipos `SALDO_INICIAL`, `ENTRADA`, `SAIDA`, `PERDA`, `AJUSTE_POSITIVO`, `AJUSTE_NEGATIVO`, `TRANSFERENCIA_ENTRADA`, `TRANSFERENCIA_SAIDA`.
   A versão da equipe tinha só `AJUSTE`, que não diz se o ajuste foi para mais ou para menos (a quantidade é sempre positiva). O SQLite não altera um `CHECK`, então a tabela é reconstruída copiando os dados, e os `AJUSTE` antigos viram `AJUSTE_NEGATIVO` com uma nota na observação (a direção é uma suposição; confira).
4. Reconcilia o histórico com a tabela `estoque`, que é considerada a verdade (a contagem física atual):
   - saldo maior que o histórico → cria `SALDO_INICIAL` com a diferença, datado 1 segundo antes da movimentação mais antiga;
   - saldo menor que o histórico → cria um `AJUSTE_NEGATIVO` marcado com `registrado_por = 'migracao'`.

   Esse passo só roda quando a tabela acaba de ser criada ou reconstruída, para não esconder divergências reais em execuções futuras.

Detalhes de funcionamento:

- Tudo roda em **uma transação**: se algo falhar, o banco fica como estava.
- Antes de alterar, é criada uma cópia `arquivo.db.AAAAMMDD-HHMMSS-micros.bak`, descartada automaticamente se nada precisou ser alterado.
- Pode ser repetida sem problema: quando não há o que fazer, apenas informa "Nada a fazer".
- Depois da migração, `GET /relatorios/auditoria` deve voltar vazio.

## Testes

```bash
python -m unittest discover -s tests -v
```

Não é preciso instalar nada. Os testes de regras (`tests/test_process.py`) usam uma cópia temporária do banco, então o banco real nunca é alterado. Os testes da migração (`tests/test_migracao.py`) rodam sobre as duas versões do banco guardadas em `tests/fixtures`:

- `PJIdb_v2_versao_equipe.db`: a versão enviada pela equipe, com `movimentacoes` e o tipo `AJUSTE`.
- `PJIdb_v2_primeira_versao.db`: a primeira versão, sem a tabela `movimentacoes`.

Os testes de regras supõem os dados de exemplo atuais (por exemplo, o produto 1 com 5 unidades no depósito e 8 na loja); se esses dados mudarem, alguns testes precisarão ser ajustados.
