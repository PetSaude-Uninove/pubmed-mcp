"""
Example HTTP client for the PubMed MCP Server using SSE transport.

This script demonstrates how to interact with the PubMed MCP Server
when it's running in HTTP/SSE mode.
"""

import requests
import json
from typing import Dict, Any

class PubMedMCPClient:
    """Simple client for interacting with PubMed MCP Server via HTTP/SSE."""

    def __init__(self, base_url: str = "http://127.0.0.1:8000"):
        """
        Initialize the client.

        Args:
            base_url: Base URL of the MCP server (default: http://127.0.0.1:8000)
        """
        self.base_url = base_url
        self.sse_endpoint = f"{base_url}/sse"

    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """
        Call a tool on the MCP server.

        Args:
            tool_name: Name of the tool to call
            arguments: Dictionary of arguments for the tool

        Returns:
            The result from the tool execution
        """
        # Create MCP message
        message = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }

        try:
            # Send POST request to SSE endpoint
            response = requests.post(
                self.sse_endpoint,
                json=message,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            response.raise_for_status()

            # Parse response
            result = response.json()
            if "error" in result:
                return {"error": result["error"]}

            return result.get("result", result)

        except requests.exceptions.RequestException as e:
            return {"error": f"Request failed: {str(e)}"}

    def search_key_words(self, key_words: str, num_results: int = 10) -> Any:
        """Search PubMed with keywords."""
        return self.call_tool("search_pubmed_key_words", {
            "key_words": key_words,
            "num_results": num_results
        })

    def search_advanced(self, **kwargs) -> Any:
        """Perform advanced search on PubMed."""
        return self.call_tool("search_pubmed_advanced", kwargs)

    def get_metadata(self, pmid: str) -> Any:
        """Get metadata for a specific PMID."""
        return self.call_tool("get_pubmed_article_metadata", {"pmid": pmid})

    def download_pdf(self, pmid: str) -> Any:
        """Attempt to download PDF for a PMID."""
        return self.call_tool("download_pubmed_pdf", {"pmid": pmid})


def main():
    """Example usage of the PubMed MCP Client."""
    # Initialize client
    client = PubMedMCPClient("http://127.0.0.1:8000")

    print("=== PubMed MCP HTTP Client Example ===\n")

    # Example 1: Search with keywords
    print("1. Searching for CRISPR articles...")
    results = client.search_key_words("CRISPR gene editing", num_results=5)
    print(f"Results: {json.dumps(results, indent=2)}\n")

    # Example 2: Advanced search
    print("2. Performing advanced search...")
    results = client.search_advanced(
        term="cancer",
        journal="Nature",
        start_date="2023/01/01",
        num_results=3
    )
    print(f"Results: {json.dumps(results, indent=2)}\n")

    # Example 3: Get metadata for a specific article
    # Note: Replace with an actual PMID from your search results
    print("3. Getting metadata for a specific article...")
    # This is an example PMID - replace with a real one
    # metadata = client.get_metadata("36753762")
    # print(f"Metadata: {json.dumps(metadata, indent=2)}\n")

    print("=== Examples completed ===")


if __name__ == "__main__":
    main()
