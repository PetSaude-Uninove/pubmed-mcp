import importlib

import pubmed_web_search as pws


def test_url_de_busca_inclui_email_e_api_key(monkeypatch):
    monkeypatch.setenv("PUBMED_EMAIL", "equipe@exemplo.org")
    monkeypatch.setenv("PUBMED_API_KEY", "chave123")
    importlib.reload(pws)
    url = pws.generate_pubmed_search_url(term="asma")
    assert "email=equipe%40exemplo.org" in url
    assert "api_key=chave123" in url
    assert "term=asma" in url


def test_url_de_busca_sem_credenciais_nao_inclui_parametros(monkeypatch):
    monkeypatch.delenv("PUBMED_EMAIL", raising=False)
    monkeypatch.delenv("PUBMED_API_KEY", raising=False)
    importlib.reload(pws)
    url = pws.generate_pubmed_search_url(term="asma")
    assert "email=" not in url
    assert "api_key=" not in url


def test_efetch_recebe_as_mesmas_credenciais(monkeypatch):
    monkeypatch.setenv("PUBMED_EMAIL", "equipe@exemplo.org")
    monkeypatch.setenv("PUBMED_API_KEY", "chave123")
    importlib.reload(pws)
    chamadas = []

    class Resp:
        status_code = 200
        text = "<PubmedArticleSet></PubmedArticleSet>"
        content = text.encode()

        def raise_for_status(self):
            return None

    monkeypatch.setattr(pws.requests, "get", lambda url, **kw: chamadas.append(url) or Resp())
    pws.get_pubmed_metadata("12345")
    assert chamadas and "api_key=chave123" in chamadas[0] and "email=equipe%40exemplo.org" in chamadas[0]
