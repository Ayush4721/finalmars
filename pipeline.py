import re
from typing import TypedDict

from langgraph.graph import StateGraph, START, END

from agents import (
    route_question,
    direct_answer,
    write_report
)
from tools import web_search,scrape_url


# ============================================================
# SHARED STATE
# ============================================================

class ResearchState(TypedDict, total=False):
    topic: str
    route: str
    search_results: str
    scraped_content: str
    report: str


# ============================================================
# NODE 0: ROUTER
# ============================================================

def router_node(state: ResearchState):
    print("\n" + "=" * 50)
    print("ROUTER AGENT")
    print("=" * 50)

    topic = state["topic"]
    route = route_question(topic)

    print(f"\n[ROUTER] -> {route}")

    return {"route": route}


# ============================================================
# NODE 1: DIRECT ANSWER
# ============================================================

def direct_node(state: ResearchState):
    print("\n" + "=" * 50)
    print("DIRECT ANSWER")
    print("=" * 50)

    report = direct_answer(state["topic"])

    print("\nDirect answer generated.")

    return {"report": report}


# ============================================================
# NODE 2: WEB SEARCH
# ============================================================

def search_node(state: ResearchState):
    print("\n" + "=" * 50)
    print("STEP 1 - WEB SEARCH")
    print("=" * 50)

    topic = state["topic"]

    print(f"\nSearching for: {topic}")

    search_results = web_search.invoke({
        "query": topic
    })

    if not isinstance(search_results, str):
        search_results = str(search_results)

    print("\nWeb search completed.")

    return {"search_results": search_results}


#---------------------scraper node ----------------------

# ============================================================
# NODE 2: SCRAPER
# ============================================================

def scrape_node(state: ResearchState):
    print("\n" + "=" * 50)
    print("STEP 2 - SCRAPER")
    print("=" * 50)

    search_results = state.get("search_results", "")

    # Extract URLs from the formatted Tavily search results.
    urls = re.findall(
        r"URL:\s*(https?://[^\s]+)",
        search_results
    )

    # Remove duplicate URLs while preserving search order.
    urls = list(dict.fromkeys(urls))

    print(f"URLs discovered: {len(urls)}")

    scraped_entries = []

    # Scrape only the top two unique URLs.
    for url in urls[:2]:
        print(f"\nScraping: {url}")

        try:
            content = scrape_url.invoke({"url": url})

            if not isinstance(content, str):
                content = str(content)

            if (
                content.strip()
                and not content.startswith((
                    "Could not scrape URL:",
                    "Scraping failed:",
                    "Invalid URL.",
                    "The URL does not return an HTML page.",
                    "No readable article content was found.",
                    "The page contains no readable text."
                ))
            ):
                print(f"Scrape successful: {len(content)} characters")
            else:
                print(f"Scrape returned an error or empty content: {url}")

            scraped_entries.append(
                f"Source URL: {url}\n{content}"
            )

        except Exception as e:
            print(f"Scrape failed: {url} - {e}")
            scraped_entries.append(
                f"Source URL: {url}\nScraping failed: {e}"
            )

    scraped_content = (
        "\n\n---\n\n".join(scraped_entries)
        if scraped_entries
        else "No URLs were found in the search results."
    )

    print(f"\nTotal scraped content: {len(scraped_content)} characters")

    return {"scraped_content": scraped_content}

# ============================================================
# NODE 3: WRITER
# ============================================================

def writer_node(state: ResearchState):
    print("\n" + "=" * 50)
    print("STEP 3 - WRITER")
    print("=" * 50)

    search_results = state.get(
        "search_results",
        "No search results available."
    )

    scraped_content = state.get(
        "scraped_content",
        "No scraped content available."
    )

    print(f"Search results length: {len(search_results)}")
    print(f"Scraped content length: {len(scraped_content)}")

    report = write_report(
        topic=state["topic"],
        research=search_results,
        scraped_content=scraped_content
    )

    print("\nFinal report generated.")

    return {"report": report}



# ============================================================
# ROUTING LOGIC
# ============================================================

def decide_route(state: ResearchState):
    if state.get("route") == "DIRECT":
        return "direct"

    return "research"


# ============================================================
# BUILD LANGGRAPH
# ============================================================

def build_research_graph():
    graph = StateGraph(ResearchState)

    graph.add_node("router", router_node)
    graph.add_node("direct", direct_node)
    graph.add_node("search", search_node)
    graph.add_node("scrape", scrape_node)  
    graph.add_node("writer", writer_node)
    # Start with the router.
    
    graph.add_edge(START, "router")

    # Select the direct-answer or research branch.
    graph.add_conditional_edges(
        "router",
        decide_route,
        {
            "direct": "direct",
            "research": "search"
        }
    )

    # Direct branch.
    graph.add_edge("direct", END)

    # Research branch.
    graph.add_edge("search", "scrape")    
    graph.add_edge("scrape", "writer")     
    graph.add_edge("writer", END)

    return graph.compile()


# ============================================================
# CREATE GRAPH
# ============================================================

research_graph = build_research_graph()


# ============================================================
# RUN PIPELINE
# ============================================================

def run_research_pipeline(topic: str) -> dict:
    topic = topic.strip()

    if not topic:
        raise ValueError("Please enter a research question.")

    result = research_graph.invoke({
        "topic": topic
    })

    print("\n" + "=" * 50)
    print("FINAL ANSWER")
    print("=" * 50)

    print(result.get("report", "No report was generated."))

    return result


# ============================================================
# DIRECT EXECUTION
# ============================================================

if __name__ == "__main__":
    topic = input("\nEnter a research topic: ").strip()

    if topic:
        try:
            run_research_pipeline(topic)
        except Exception as e:
            print(f"\nPipeline failed: {e}")
    else:
        print("Please enter a research topic.")
