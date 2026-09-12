import socket
import threading
import time

import anyio
import pytest
import uvicorn
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

import pubmed_server_http as srv


def porta_livre() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture
def servidor(monkeypatch):
    monkeypatch.setattr(srv, "search_key_words", lambda key_words, num_results=10: [
        {"pmid": "1", "title": f"Artigo sobre {key_words}"}])
    porta = porta_livre()
    srv.mcp.settings.host = "127.0.0.1"
    srv.mcp.settings.port = porta
    config = uvicorn.Config(srv.mcp.streamable_http_app(), host="127.0.0.1", port=porta, log_level="warning")
    server = uvicorn.Server(config)
    t = threading.Thread(target=server.run, daemon=True)
    t.start()
    for _ in range(50):
        if server.started:
            break
        time.sleep(0.1)
    assert server.started
    yield f"http://127.0.0.1:{porta}"
    server.should_exit = True
    t.join(timeout=5)


async def _lista_e_chama(url):
    async with streamablehttp_client(f"{url}/mcp") as (r, w, _):
        async with ClientSession(r, w) as sessao:
            await sessao.initialize()
            tools = await sessao.list_tools()
            resultado = await sessao.call_tool("search_pubmed_key_words", {"key_words": "asma", "num_results": 1})
            return sorted(t.name for t in tools.tools), resultado


def test_lista_as_quatro_tools_e_executa_busca(servidor):
    nomes, resultado = anyio.run(_lista_e_chama, servidor)
    assert nomes == ["download_pubmed_pdf", "get_pubmed_article_metadata",
                     "search_pubmed_advanced", "search_pubmed_key_words"]
    assert not resultado.isError
    assert "Artigo sobre asma" in resultado.content[0].text


def test_health(servidor):
    import urllib.request
    with urllib.request.urlopen(f"{servidor}/health", timeout=3) as resp:
        assert resp.status == 200
        assert b'"ok"' in resp.read()
