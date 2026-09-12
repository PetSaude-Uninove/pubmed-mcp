import pytest

import pubmed_server_http as srv


@pytest.fixture(autouse=True)
def _reiniciar_session_manager_do_mcp():
    """Zera o StreamableHTTPSessionManager antes de cada teste.

    O FastMCP cria o StreamableHTTPSessionManager de forma lazy na primeira
    chamada a `streamable_http_app()` e o guarda na própria instância; esse
    gerenciador só pode ser executado (`run()`) uma vez. Como os testes deste
    módulo reutilizam o singleton `srv.mcp` para subir o servidor mais de uma
    vez no mesmo processo, é preciso descartar o gerenciador anterior antes de
    cada teste para que uma nova instância seja criada na próxima subida.
    Isso é só uma necessidade de teste: em produção o processo sobe o
    servidor uma única vez.
    """
    srv.mcp._session_manager = None
    yield
