from typing import Any, List, Dict, Optional, Union
import asyncio
import logging
import argparse
from mcp.server.fastmcp import FastMCP
from pubmed_web_search import search_key_words, search_advanced, get_pubmed_metadata, download_full_text_pdf, deep_paper_analysis

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Initialize FastMCP server
mcp = FastMCP("pubmed")

@mcp.tool()
async def search_pubmed_key_words(key_words: str, num_results: int = 10) -> List[Dict[str, Any]]:
    logging.info(f"Searching for articles with key words: {key_words}, num_results: {num_results}")
    """
    Search for articles on PubMed using key words.

    Args:
        key_words: Search query string
        num_results: Number of results to return (default: 10)

    Returns:
        List of dictionaries containing article information
    """
    try:
        results = await asyncio.to_thread(search_key_words, key_words, num_results)
        return results
    except Exception as e:
        return [{"error": f"An error occurred while searching: {str(e)}"}]

@mcp.tool()
async def search_pubmed_advanced(
    term: Optional[str] = None,
    title: Optional[str] = None,
    author: Optional[str] = None,
    journal: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    num_results: int = 10
) -> List[Dict[str, Any]]:
    logging.info(f"Performing advanced search with parameters: {locals()}")
    """
    Perform an advanced search for articles on PubMed.

    Args:
        term: General search term
        title: Search in title
        author: Author name
        journal: Journal name
        start_date: Start date for search range (format: YYYY/MM/DD)
        end_date: End date for search range (format: YYYY/MM/DD)
        num_results: Number of results to return (default: 10)

    Returns:
        List of dictionaries containing article information
    """
    try:
        results = await asyncio.to_thread(
            search_advanced,
            term, title, author, journal, start_date, end_date, num_results
        )
        return results
    except Exception as e:
        return [{"error": f"An error occurred while performing advanced search: {str(e)}"}]

@mcp.tool()
async def get_pubmed_article_metadata(pmid: Union[str, int]) -> Dict[str, Any]:
    logging.info(f"Fetching metadata for PMID: {pmid}")
    """
    Fetch metadata for a PubMed article using its PMID.

    Args:
        pmid: PMID of the article (can be string or integer)

    Returns:
        Dictionary containing article metadata
    """
    try:
        pmid_str = str(pmid)
        metadata = await asyncio.to_thread(get_pubmed_metadata, pmid_str)
        return metadata if metadata else {"error": f"No metadata found for PMID: {pmid_str}"}
    except Exception as e:
        return {"error": f"An error occurred while fetching metadata: {str(e)}"}

@mcp.tool()
async def download_pubmed_pdf(pmid: Union[str, int]) -> str:
    logging.info(f"Attempting to download PDF for PMID: {pmid}")
    """
    Attempt to download the full text PDF for a PubMed article.

    Args:
        pmid: PMID of the article (can be string or integer)

    Returns:
        String indicating the result of the download attempt
    """
    try:
        pmid_str = str(pmid)
        result = await asyncio.to_thread(download_full_text_pdf, pmid_str)
        return result
    except Exception as e:
        return f"An error occurred while attempting to download the PDF: {str(e)}"

@mcp.prompt()
async def deep_paper_analysis(pmid: Union[str, int]) -> Dict[str, str]:
    logging.info(f"Performing deep paper analysis for PMID: {pmid}")
    """
    Perform a comprehensive analysis of a PubMed article.

    Args:
        pmid: PMID of the article

    Returns:
        Dictionary containing the comprehensive analysis structure
    """
    try:
        pmid_str = str(pmid)
        metadata = await asyncio.to_thread(get_pubmed_metadata, pmid_str)
        if not metadata:
            return {"error": f"No metadata found for PMID: {pmid_str}"}

        # 使用导入的 deep_paper_analysis 函数生成分析提示
        # 为避免递归调用，我们需要明确指定导入的函数
        from pubmed_web_search import deep_paper_analysis as web_deep_paper_analysis
        analysis_prompt = await asyncio.to_thread(web_deep_paper_analysis, metadata)

        # 返回包含分析提示的字典
        return {"analysis_prompt": analysis_prompt}
    except Exception as e:
        return {"error": f"An error occurred while performing the deep paper analysis: {str(e)}"}

def main():
    """Main entry point with command-line argument support for different transport modes."""
    import uvicorn
    from fastapi import FastAPI
    from fastapi.responses import StreamingResponse
    import json

    parser = argparse.ArgumentParser(description='PubMed MCP Server')
    parser.add_argument(
        '--transport',
        choices=['stdio', 'sse'],
        default='stdio',
        help='Transport mode: stdio for standard input/output (default), sse for HTTP Server-Sent Events'
    )
    parser.add_argument(
        '--host',
        default='0.0.0.0',
        help='Host to bind the HTTP server to (default: 0.0.0.0)'
    )
    parser.add_argument(
        '--port',
        type=int,
        default=8000,
        help='Port to bind the HTTP server to (default: 8000)'
    )

    args = parser.parse_args()

    if args.transport == 'sse':
        logging.info(f"Starting PubMed MCP server in HTTP/SSE mode on {args.host}:{args.port}")

        # Fallback HTTP JSON-RPC + simple SSE heartbeat at /sse
        app = FastAPI(title="PubMed MCP Server (HTTP)")

        @app.get("/sse")
        async def sse():
            async def generate():
                yield "data: {\"ready\": true}\n\n"
            return StreamingResponse(generate(), media_type="text/event-stream")

        def tool_specs():
            return [
                {
                    "name": "search_pubmed_key_words",
                    "description": "Search PubMed articles using keywords.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "key_words": {"type": "string"},
                            "num_results": {"type": "integer", "minimum": 1, "maximum": 50, "default": 10}
                        },
                        "required": ["key_words"]
                    }
                },
                {
                    "name": "search_pubmed_advanced",
                    "description": "Advanced PubMed search with filters.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "term": {"type": ["string", "null"]},
                            "title": {"type": ["string", "null"]},
                            "author": {"type": ["string", "null"]},
                            "journal": {"type": ["string", "null"]},
                            "start_date": {"type": ["string", "null"]},
                            "end_date": {"type": ["string", "null"]},
                            "num_results": {"type": "integer", "minimum": 1, "maximum": 50, "default": 10}
                        }
                    }
                },
                {
                    "name": "get_pubmed_article_metadata",
                    "description": "Get article metadata by PMID.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {"pmid": {"type": ["string", "integer"]}},
                        "required": ["pmid"]
                    }
                },
                {
                    "name": "download_pubmed_pdf",
                    "description": "Attempt to download full-text PDF by PMID.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {"pmid": {"type": ["string", "integer"]}},
                        "required": ["pmid"]
                    }
                }
            ]

        @app.post("/sse")
        async def rpc(payload: Dict[str, Any]):
            """Minimal JSON-RPC interface compatible with MCP clients expecting tools/list and tools/call."""
            try:
                method = payload.get("method")
                req_id = payload.get("id", None)
                params = payload.get("params", {})

                if method in ("tools/list", "tools.list", "list_tools"):
                    return {"jsonrpc": "2.0", "id": req_id, "result": {"tools": tool_specs()}}

                if method in ("tools/call", "tools.call", "call_tool"):
                    name = params.get("name")
                    arguments = params.get("arguments", {})

                    if name == "search_pubmed_key_words":
                        res = await search_pubmed_key_words(**arguments)
                        return {"jsonrpc": "2.0", "id": req_id, "result": {"content": res}}
                    if name == "search_pubmed_advanced":
                        res = await search_pubmed_advanced(**arguments)
                        return {"jsonrpc": "2.0", "id": req_id, "result": {"content": res}}
                    if name == "get_pubmed_article_metadata":
                        res = await get_pubmed_article_metadata(**arguments)
                        return {"jsonrpc": "2.0", "id": req_id, "result": {"content": res}}
                    if name == "download_pubmed_pdf":
                        res = await download_pubmed_pdf(**arguments)
                        return {"jsonrpc": "2.0", "id": req_id, "result": {"content": res}}

                    return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32601, "message": f"Unknown tool: {name}"}}

                if method in ("prompts/list", "prompts.list"):
                    return {"jsonrpc": "2.0", "id": req_id, "result": {"prompts": [{"name": "deep_paper_analysis"}]}}

                if method in ("prompts/call", "prompts.call"):
                    arguments = params.get("arguments", {})
                    pmid = arguments.get("pmid")
                    res = await deep_paper_analysis(pmid)
                    return {"jsonrpc": "2.0", "id": req_id, "result": {"content": res}}

                return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32601, "message": "Method not found"}}
            except Exception as e:
                logging.exception("RPC error")
                return {"jsonrpc": "2.0", "id": payload.get("id"), "error": {"code": -32000, "message": str(e)}}

        # Health endpoint remains
        @app.get("/health")
        async def health():
            return {"status": "healthy", "service": "pubmed-mcp"}

        # Serve app
        uvicorn.run(app, host=args.host, port=args.port, log_level="info")
    else:
        logging.info("Starting PubMed MCP server in STDIO mode")
        # Run in STDIO mode (original behavior)
        mcp.run(transport='stdio')

if __name__ == "__main__":
    main()
