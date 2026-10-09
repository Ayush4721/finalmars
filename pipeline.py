from typing import TypedDict

from langgraph.graph import StateGraph, START, END

from agents import (
    route_question,
    direct_answer,
    build_search_agent,
    build_reader_agent,
    write_report
)


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

    return {
        "route": route
    }


# ============================================================
# NODE 1: DIRECT ANSWER
# ============================================================

def direct_node(state: ResearchState):

    print("\n" + "=" * 50)
    print("DIRECT ANSWER")
    print("=" * 50)

    topic = state["topic"]

    report = direct_answer(topic)

    print("\nDirect answer generated.")

    return {
        "report": report
    }


# ============================================================
# NODE 2: SEARCH
# ============================================================

def search_node(state: ResearchState):

    print("\n" + "=" * 50)
    print("STEP 1 - SEARCH AGENT")
    print("=" * 50)

    agent = build_search_agent()

    result = agent.invoke({
        "messages": [
            (
                "user",
                f"""
Find recent, reliable and relevant information about:

{state['topic']}

Use web_search to obtain:

- Source titles
- URLs
- Search snippets
- Publication dates when available

Focus on information that is relevant to the user's question.
"""
            )
        ]
    })

    search_results = result["messages"][-1].content

    print("\nSearch completed.")

    return {
        "search_results": search_results
    }


# ============================================================
# NODE 3: READER
# ============================================================

def reader_node(state: ResearchState):

    print("\n" + "=" * 50)
    print("STEP 2 - READER AGENT")
    print("=" * 50)

    agent = build_reader_agent()

    result = agent.invoke({
        "messages": [
            (
                "user",
                f"""
Research topic:

{state['topic']}


SEARCH RESULTS:

{state['search_results']}


Read the most relevant sources.

Use scrape_url to retrieve the article/page content.

Extract:

- Important facts
- Relevant details
- Publication dates
- Names
- Numbers
- Evidence
- Source URLs

Do not invent information.
"""
            )
        ]
    })

    scraped_content = result["messages"][-1].content

    print("\nReading completed.")

    return {
        "scraped_content": scraped_content
    }


# ============================================================
# NODE 4: WRITER
# ============================================================

def writer_node(state: ResearchState):

    print("\n" + "=" * 50)
    print("STEP 3 - WRITER AGENT")
    print("=" * 50)

    research = f"""
SEARCH RESULTS:

{state['search_results']}


SCRAPED ARTICLE CONTENT:

{state['scraped_content']}
"""

    report = write_report(
        topic=state["topic"],
        research=research
    )

    print("\nFinal report generated.")

    return {
        "report": report
    }


# ============================================================
# ROUTING LOGIC
# ============================================================

def decide_route(state: ResearchState):

    if state["route"] == "DIRECT":
        return "direct"

    return "research"


# ============================================================
# BUILD LANGGRAPH
# ============================================================

def build_research_graph():

    graph = StateGraph(ResearchState)

    # Add nodes
    graph.add_node("router", router_node)

    graph.add_node("direct", direct_node)

    graph.add_node("search", search_node)

    graph.add_node("reader", reader_node)

    graph.add_node("writer", writer_node)


    # --------------------------------------------------------
    # START → ROUTER
    # --------------------------------------------------------

    graph.add_edge(
        START,
        "router"
    )


    # --------------------------------------------------------
    # ROUTER → DIRECT / RESEARCH
    # --------------------------------------------------------

    graph.add_conditional_edges(
        "router",
        decide_route,
        {
            "direct": "direct",
            "research": "search"
        }
    )


    # --------------------------------------------------------
    # DIRECT → END
    # --------------------------------------------------------

    graph.add_edge(
        "direct",
        END
    )


    # --------------------------------------------------------
    # RESEARCH PIPELINE
    # --------------------------------------------------------

    graph.add_edge(
        "search",
        "reader"
    )

    graph.add_edge(
        "reader",
        "writer"
    )

    graph.add_edge(
        "writer",
        END
    )


    return graph.compile()


# ============================================================
# CREATE GRAPH
# ============================================================

research_graph = build_research_graph()


# ============================================================
# RUN PIPELINE
# ============================================================

def run_research_pipeline(topic: str) -> dict:

    result = research_graph.invoke({
        "topic": topic
    })


    print("\n" + "=" * 50)
    print("FINAL ANSWER")
    print("=" * 50)

    print(result["report"])


    return result


# ============================================================
# DIRECT EXECUTION
# ============================================================

if __name__ == "__main__":

    topic = input(
        "\nEnter a research topic: "
    ).strip()

    if topic:

        run_research_pipeline(topic)

    else:

        print(
            "Please enter a research topic."
        )