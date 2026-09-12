[![MseeP.ai Security Assessment Badge](https://mseep.net/pr/jackkuo666-pubmed-mcp-server-badge.png)](https://mseep.ai/app/jackkuo666-pubmed-mcp-server)

# PubMed MCP Server

🔍 Enable AI assistants to search, access, and analyze PubMed articles through a simple MCP interface.

The PubMed MCP Server provides a bridge between AI assistants and PubMed's vast repository of biomedical literature through the Model Context Protocol (MCP). It allows AI models to search for scientific articles, access their metadata, and perform deep analysis in a programmatic way.

🤝 Contribute • 📝 Report Bug

## ✨ Core Features
- 🔎 Paper Search: Query PubMed articles with keywords or advanced search ✅
- 🚀 Efficient Retrieval: Fast access to paper metadata ✅
- 📊 Metadata Access: Retrieve detailed metadata for specific papers ✅
- 📊 Research Support: Facilitate biomedical sciences research and analysis ✅
- 📄 Paper Access: Attempt to download full-text PDF content ✅
- 🧠 Deep Analysis: Perform comprehensive analysis of papers ✅
- 📝 Research Prompts: A set of specialized prompts for paper analysis ✅

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- FastMCP library

### Installation

1. Clone the repository:
   ```
   git clone https://github.com/JackKuo666/PubMed-MCP-Server.git
   cd PubMed-MCP-Server
   ```

2. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

## 📊 Usage

### STDIO Mode (Default)

Start the MCP server in STDIO mode (for use with Claude Desktop and similar clients):

```bash
python pubmed_server.py
```

## Produção (PET Saúde)

Em produção, o servidor roda em Streamable HTTP, no caminho `/mcp`, que é o
transporte falado pelo cliente MCP do Open WebUI 0.6.x:

```bash
# Usando HOST e PORT padrão (0.0.0.0:8000)
python pubmed_server_http.py --transport streamable-http

# Sobrescrevendo host e porta
python pubmed_server_http.py --transport streamable-http --host 0.0.0.0 --port 8080

# Modo STDIO (uso local)
python pubmed_server_http.py --transport stdio
```

O servidor expõe:
- `POST/GET http://<host>:8000/mcp`: endpoint Streamable HTTP (stateless).
- `GET http://<host>:8000/health`: healthcheck, retorna `{"status": "ok"}`.

Variáveis de ambiente:
- `HOST` e `PORT`: endereço e porta do servidor (padrão `0.0.0.0` e `8000`).
- `PUBMED_EMAIL` e `PUBMED_API_KEY`: opcionais. Quando definidas, são enviadas
  em toda chamada ao E-utilities do NCBI, que passa a permitir 10 requisições
  por segundo em vez de 3.

Rodando a imagem publicada no GHCR:

```bash
docker run -p 8000:8000 ghcr.io/petsaude-uninove/pubmed-mcp:v1.0.0
```

Rodando os testes:

```bash
pytest -q
```

## Usage with Claude Desktop

Add this configuration to your `claude_desktop_config.json`:

(Mac OS)

```json
{
  "mcpServers": {
    "pubmed": {
      "command": "python",
      "args": ["-m", "pubmed-mcp-server"]
      }
  }
}
```

(Windows version):

```json
{
  "mcpServers": {
    "pubmed": {
      "command": "C:\\Users\\YOUR\\PATH\\miniconda3\\envs\\mcp_server\\python.exe",
      "args": [
        "D:\\code\\YOUR\\PATH\\PubMed-MCP-Server\\pubmed_server.py"
      ],
      "env": {},
      "disabled": false,
      "autoApprove": []
    }
  }
}
```
Using with Cline
```json
{
  "mcpServers": {
    "pubmed": {
      "command": "bash",
      "args": [
        "-c",
        "source /home/YOUR/PATH/mcp-server-pubmed/.venv/bin/activate && python /home/YOUR/PATH/pubmed-mcp-server.py"
      ],
      "env": {},
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

## 🛠 MCP Tools

The PubMed MCP Server provides the following tools:

1. `search_pubmed_key_words`: Search for articles on PubMed using keywords.
2. `search_pubmed_advanced`: Perform an advanced search for articles on PubMed with multiple parameters.
3. `get_pubmed_article_metadata`: Fetch metadata for a PubMed article using its PMID.
4. `download_pubmed_pdf`: Attempt to download the full-text PDF for a PubMed article.
5. `deep_paper_analysis`: Perform a comprehensive analysis of a PubMed article.

### Searching Papers

You can ask the AI assistant to search for papers using queries like:
```
Can you search PubMed for recent papers about CRISPR?
```

### Getting Paper Details

Once you have a PMID, you can ask for more details:
```
Can you show me the metadata for the paper with PMID 12345678?
```

### Analyzing Papers

You can request a deep analysis of a paper:
```
Can you perform a deep analysis of the paper with PMID 12345678?
```

## 📁 Project Structure

- `pubmed_server.py`: The main MCP server implementation using FastMCP
- `pubmed_web_search.py`: Contains the logic for searching PubMed and retrieving article information

## 🌐 Integração via Streamable HTTP

Com o servidor rodando em `--transport streamable-http`, qualquer cliente MCP
que fale Streamable HTTP (como o Open WebUI) pode se conectar em
`http://<host>:8000/mcp`. Exemplo em Python com o SDK oficial:

```python
import anyio
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client


async def main():
    async with streamablehttp_client("http://127.0.0.1:8000/mcp") as (r, w, _):
        async with ClientSession(r, w) as sessao:
            await sessao.initialize()
            resultado = await sessao.call_tool(
                "search_pubmed_key_words", {"key_words": "CRISPR", "num_results": 5}
            )
            print(resultado)


anyio.run(main)
```

## 🔧 Dependencies

- Python 3.10+
- FastMCP
- asyncio
- logging
- requests
- beautifulsoup4
- uvicorn (for HTTP mode)
- starlette (for HTTP mode)

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

This project is licensed under the MIT License.

## ⚠️ Disclaimer

This tool is for research purposes only. Please respect PubMed's terms of service and use this tool responsibly.
