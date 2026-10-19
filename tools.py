
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


# ============================================================
# WEB SEARCH TOOL
# ============================================================

@tool
def web_search(query: str) -> str:
    """Search the web and return titles, URLs, snippets and dates."""

    try:
        response = tavily.search(
            query=query,
            max_results=3,
            search_depth="basic"
        )

        results = response.get("results", [])
        output = []

        for result in results:
            title = result.get("title", "Unknown")
            url = result.get("url", "Unknown")
            snippet = result.get("content", "")
            published = (
                result.get("published_date")
                or "Not provided"
            )

            output.append(
                f"Title: {title}\n"
                f"URL: {url}\n"
                f"Published: {published}\n"
                f"Snippet: {snippet[:500]}"
            )

        if not output:
            return "No relevant search results were found."

        return "\n\n---\n\n".join(output)

    except Exception as e:
        return f"Web search failed: {str(e)}"


# ============================================================
# WEB SCRAPER TOOL
# Kept available for future use; not called by the current graph.
# ============================================================

@tool
def scrape_url(url: str) -> str:
    """Extract readable text from an HTTP or HTTPS webpage."""

    if not url.startswith(("http://", "https://")):
        return "Invalid URL. Only HTTP and HTTPS URLs are supported."

    try:
        response = requests.get(
            url,
            timeout=10,
            headers={
                "User-Agent": "Mozilla/5.0"
            }
        )

        response.raise_for_status()

        content_type = response.headers.get("Content-Type", "")

        if "text/html" not in content_type.lower():
            return "The URL does not return an HTML page."

        soup = BeautifulSoup(response.text, "html.parser")

        for tag in soup([
            "script",
            "style",
            "nav",
            "footer",
            "header",
            "aside",
            "form",
            "noscript"
        ]):
            tag.decompose()

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
            f"{text[:3000]}"
        )

    except requests.RequestException as e:
        return f"Could not scrape URL: {str(e)}"

    except Exception as e:
        return f"Scraping failed: {str(e)}"
