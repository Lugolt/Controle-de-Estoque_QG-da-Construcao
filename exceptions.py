class NaoEncontradoError(Exception):
    pass


class RegraDeNegocioError(Exception):
    pass


def exigir(condicao, mensagem):
    if not condicao:
        raise RegraDeNegocioError(mensagem)
