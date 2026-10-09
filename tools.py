import os

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from tavily import TavilyClient
from langchain.tools import tool


load_dotenv()

api_key = os.getenv("TAVILY_API_KEY")

if not api_key:
    raise ValueError(
        "TAVILY_API_KEY is missing. Add it to your .env file."
    )

tavily = TavilyClient(api_key=api_key)


# ---------------- WEB SEARCH TOOL ----------------

@tool
def web_search(query: str) -> str:
    """Search the web and return relevant titles, URLs and snippets."""

    try:
        response = tavily.search(
            query=query,
            max_results=4
        )

        results = response.get("results", [])
        output = []

        for result in results:
            output.append(
                f"Title: {result.get('title', 'Unknown')}\n"
                f"URL: {result.get('url', 'Unknown')}\n"
                f"Snippet: {result.get('content', '')[:500]}\n"
            )

        if not output:
            return "No relevant search results were found."

        return "\n---\n".join(output)

    except Exception as e:
        return f"Web search failed: {str(e)}"


# ---------------- WEB SCRAPER TOOL ----------------

@tool
def scrape_url(url: str) -> str:
    """Scrape an HTTP or HTTPS article URL and return its clean text."""

    if not url.startswith(("http://", "https://")):
        return "Invalid URL. Only HTTP and HTTPS URLs are supported."

    try:

        response = requests.get(
            url,
            timeout=15,
            headers={
                "User-Agent": "Mozilla/5.0 ResearchBot/1.0"
            }
        )

        response.raise_for_status()

        content_type = response.headers.get(
            "Content-Type",
            ""
        )

        if "text/html" not in content_type.lower():
            return "The URL does not return an HTML page."

        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )

        # Remove irrelevant elements
        for tag in soup([
            "script",
            "style",
            "nav",
            "footer",
            "header",
            "aside",
            "form"
        ]):

            tag.decompose()

        # Prefer article content
        article = (
            soup.find("article")
            or soup.find("main")
            or soup.body
        )

        if article is None:
            return "No readable article content was found."

        text = article.get_text(
            separator=" ",
            strip=True
        )

        if not text:
            return "The page contains no readable text."

        return (
            f"Source URL: {url}\n\n"
            f"{text[:6000]}"
        )

    except requests.RequestException as e:

        return f"Could not scrape URL: {str(e)}"

    except Exception as e:

        return f"Scraping failed: {str(e)}"