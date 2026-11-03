import os
import shutil
import tempfile
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent


class BaseTeste(unittest.TestCase):
    def setUp(self):
        self.pasta = tempfile.mkdtemp()
        copia = Path(self.pasta) / "teste.db"
        shutil.copy(RAIZ / "PJIdb_v2.db", copia)
        import database
        database.DB_PATH = copia

    def tearDown(self):
        shutil.rmtree(self.pasta, ignore_errors=True)


from exceptions import NaoEncontradoError, RegraDeNegocioError
from process import (alerta_process, compra_process, movimentacao_process,
                     produto_process)


class TestMovimentacao(BaseTeste):
    def _saldo(self, produto_id, campo="saldo_deposito"):
        return produto_process.obter(produto_id)[campo]

    def test_entrada_aumenta_saldo_e_gera_historico(self):
        antes = self._saldo(1)
        movimentacao_process.registrar(
            {"produto_id": 1, "local": "deposito", "tipo": "ENTRADA", "quantidade": 7})
        self.assertEqual(self._saldo(1), antes + 7)
        self.assertEqual(movimentacao_process.listar(produto_id=1, tipo="ENTRADA")[0]["quantidade"], 7)

    def test_saida_maior_que_saldo_e_bloqueada_e_nao_altera_nada(self):
        antes = self._saldo(1)
        with self.assertRaises(RegraDeNegocioError):
            movimentacao_process.registrar(
                {"produto_id": 1, "local": "deposito", "tipo": "SAIDA", "quantidade": antes + 1})
        self.assertEqual(self._saldo(1), antes)

    def test_quantidade_zero_ou_negativa_e_bloqueada(self):
        for q in (0, -3):
            with self.assertRaises(RegraDeNegocioError):
                movimentacao_process.registrar(
                    {"produto_id": 1, "local": "loja", "tipo": "SAIDA", "quantidade": q})

    def test_produto_inexistente(self):
        with self.assertRaises(NaoEncontradoError):
            movimentacao_process.registrar(
                {"produto_id": 9999, "local": "loja", "tipo": "ENTRADA", "quantidade": 1})

    def test_transferencia_mantem_total(self):
        total = self._saldo(1, "saldo_total")
        movimentacao_process.transferir(
            {"produto_id": 1, "origem": "deposito", "destino": "loja", "quantidade": 2})
        self.assertEqual(self._saldo(1, "saldo_total"), total)
        self.assertEqual(self._saldo(1, "saldo_deposito"), 3)
        self.assertEqual(self._saldo(1, "saldo_loja"), 10)

    def test_transferencia_sem_saldo_desfaz_tudo(self):
        with self.assertRaises(RegraDeNegocioError):
            movimentacao_process.transferir(
                {"produto_id": 1, "origem": "deposito", "destino": "loja", "quantidade": 999})
        self.assertEqual(self._saldo(1, "saldo_loja"), 8)

    def test_inventario_registra_divergencia(self):
        r = movimentacao_process.contar_inventario(
            {"produto_id": 1, "local": "loja", "quantidade_contada": 6})
        self.assertEqual(r["divergencia"], -2)
        self.assertEqual(self._saldo(1, "saldo_loja"), 6)
        r2 = movimentacao_process.contar_inventario(
            {"produto_id": 1, "local": "loja", "quantidade_contada": 6})
        self.assertEqual(r2["divergencia"], 0)

    def test_auditoria_fecha_apos_varias_operacoes(self):
        movimentacao_process.registrar({"produto_id": 1, "local": "loja", "tipo": "SAIDA", "quantidade": 3})
        movimentacao_process.registrar({"produto_id": 2, "local": "deposito", "tipo": "ENTRADA", "quantidade": 10})
        movimentacao_process.transferir({"produto_id": 2, "origem": "deposito", "destino": "loja", "quantidade": 4})
        movimentacao_process.contar_inventario({"produto_id": 1, "local": "deposito", "quantidade_contada": 1})
        self.assertEqual(movimentacao_process.auditar(), [])


class TestProduto(BaseTeste):
    DADOS = {"sku": "SKU-TESTE", "nome": "CIMENTO CP II 50KG", "unidade": "saco",
             "estoque_minimo": 20, "estoque_maximo": 100}

    def test_criar_produto_nasce_zerado(self):
        p = produto_process.criar(self.DADOS)
        self.assertEqual(p["saldo_total"], 0)
        self.assertEqual(p["status"], "ZERADO")

    def test_sku_duplicado(self):
        produto_process.criar(self.DADOS)
        with self.assertRaises(RegraDeNegocioError):
            produto_process.criar(self.DADOS)

    def test_maximo_menor_que_minimo(self):
        with self.assertRaises(RegraDeNegocioError):
            produto_process.criar({**self.DADOS, "estoque_minimo": 50, "estoque_maximo": 10})

    def test_status_baixo_normal_excesso(self):
        p = produto_process.criar(self.DADOS)
        pid = p["produto_id"]
        mov = lambda q: movimentacao_process.registrar(
            {"produto_id": pid, "local": "deposito", "tipo": "ENTRADA", "quantidade": q})
        mov(15)
        self.assertEqual(produto_process.obter(pid)["status"], "BAIXO")
        mov(30)
        self.assertEqual(produto_process.obter(pid)["status"], "NORMAL")
        mov(100)
        self.assertEqual(produto_process.obter(pid)["status"], "EXCESSO")

    def test_desativar_nao_apaga_e_bloqueia_movimentacao(self):
        produto_process.desativar(1)
        self.assertNotIn(1, [p["produto_id"] for p in produto_process.listar()])
        self.assertIn(1, [p["produto_id"] for p in produto_process.listar(incluir_desativados=True)])
        with self.assertRaises(RegraDeNegocioError):
            movimentacao_process.registrar(
                {"produto_id": 1, "local": "loja", "tipo": "ENTRADA", "quantidade": 1})

    def test_busca_por_nome_ou_sku(self):
        self.assertTrue(len(produto_process.listar(busca="BICA")) > 0)
        self.assertEqual(len(produto_process.listar(busca="SKU-0001")), 1)


class TestCompraEAlertas(BaseTeste):
    def test_compra_gera_entradas_no_estoque(self):
        antes = produto_process.obter(1)["saldo_deposito"]
        c = compra_process.registrar({
            "fornecedor_id": 1, "data": "2026-10-01", "nota_fiscal": "999",
            "itens": [{"produto_id": 1, "quantidade": 10, "custo_unit": 50.0}]})
        self.assertEqual(c["valor_total"], 500.0)
        self.assertEqual(produto_process.obter(1)["saldo_deposito"], antes + 10)
        self.assertEqual(movimentacao_process.auditar(), [])

    def test_compra_com_item_invalido_nao_grava_nada(self):
        antes = len(compra_process.listar())
        with self.assertRaises(NaoEncontradoError):
            compra_process.registrar({
                "fornecedor_id": 1, "data": "2026-10-01",
                "itens": [{"produto_id": 1, "quantidade": 5, "custo_unit": 1.0},
                          {"produto_id": 9999, "quantidade": 5, "custo_unit": 1.0}]})
        self.assertEqual(len(compra_process.listar()), antes)
        self.assertEqual(movimentacao_process.auditar(), [])

    def test_compra_sem_itens(self):
        with self.assertRaises(RegraDeNegocioError):
            compra_process.registrar({"fornecedor_id": 1, "data": "2026-10-01", "itens": []})

    def test_alertas_e_lista_de_compras(self):
        movimentacao_process.contar_inventario({"produto_id": 1, "local": "deposito", "quantidade_contada": 0})
        movimentacao_process.contar_inventario({"produto_id": 1, "local": "loja", "quantidade_contada": 0})
        alertas = alerta_process.listar_alertas()
        self.assertIn(1, [p["produto_id"] for p in alertas["zerados"]])
        compras = alerta_process.lista_de_compras()
        item = next(c for c in compras if c["produto_id"] == 1)
        self.assertEqual(item["quantidade_sugerida"], 20)


if __name__ == "__main__":
    unittest.main()
