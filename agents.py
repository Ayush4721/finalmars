
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI


load_dotenv()


# ============================================================
# MODEL
# ============================================================

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0
)


# ============================================================
# ROUTER AGENT
# ============================================================

class RouteDecision(BaseModel):
    route: str = Field(
        description="The route must be either DIRECT or RESEARCH."
    )


router_llm = llm.with_structured_output(RouteDecision)


def route_question(question: str) -> str:
    """Choose direct answering or current web research."""

    prompt = f"""
You are the Router Agent of an AI research system.

Choose DIRECT when the question can be answered using stable,
general knowledge.

Choose RESEARCH when the answer requires current, recent,
live, time-sensitive, or external web information.

Choose DIRECT for questions such as:
- What is Machine Learning?
- Explain neural networks.
- What is Python?
- How does RAG work?
- Explain a programming concept.

Choose RESEARCH for questions such as:
- Latest AI news.
- News from the last 24 hours.
- Current product prices.
- Today's cricket results.
- Current weather.
- Recent events and developments.
- Current information about companies or public figures.

A long question does not automatically require research.
Use RESEARCH if the answer depends on information that may
have changed or needs external verification.

User question:
{question}

Return the appropriate route using the required schema.
"""

    try:
        result = router_llm.invoke(prompt)
        route = result.route.upper().strip()

        if route in ("DIRECT", "RESEARCH"):
            return route

        return "DIRECT"

    except Exception as e:
        # Prefer research if routing fails, so current questions
        # are less likely to receive a stale answer.
        print(f"[ROUTER ERROR] {e}")
        return "RESEARCH"


# ============================================================
# DIRECT ANSWER
# ============================================================

def direct_answer(question: str) -> str:
    """Answer general questions without web research."""

    prompt = f"""
You are a helpful AI assistant.

Answer the user's question clearly and accurately.

User question:
{question}

Instructions:
- Give a medium-length answer, not too short or too long.
- Start with the direct answer.
- Explain important concepts in simple language.
- Use Markdown headings when helpful.
- Use bullet points when appropriate.
- Include an example when useful.
- Avoid unnecessary background information and repetition.
- Do not invent facts.
- Do not mention internal routing, agents, or pipelines.

Return only the final answer.
"""

    response = llm.invoke(prompt)
    return response.content


# ============================================================
# WRITER AGENT
# ============================================================

def write_report(topic: str, research: str, scraped_content: str) -> str:
    """Generate a final report from web search results."""

    prompt = f"""
You are the research report writer in an AI research system.

User question:
{topic}

Web search results:
{research}

Scraped content:
{scraped_content}

Write a clear, useful answer based on the available evidence.

Instructions:
- Answer the user's actual question.
- Use Markdown for readability.
- Summarize the most important findings.
- Preserve relevant source titles and URLs.
- Include publication dates only when supplied in the results.
- Never invent sources, dates, quotations, or facts.
- Distinguish facts from uncertainty where necessary.
- If the search results are insufficient, clearly say so.
- Do not treat a missing publication date as proof that an
  article is recent.
- For news questions, organize findings into concise bullet points.
- For current events, include dates when available.
- Avoid repeating the same information.
- Do not mention internal agents or pipeline implementation.

Return only the final report.
"""

    response = llm.invoke(prompt)
    return response.content
