from dotenv import load_dotenv
from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import create_agent

from tools import web_search, scrape_url

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
    """
    Decide whether the question needs web research.
    """

    prompt = f"""
You are the Router Agent of a multi-agent AI research system.

Your ONLY job is to decide whether the user's question needs
current web research.

Choose DIRECT when the question can be answered using stable
general knowledge.

Choose RESEARCH when the question requires current, recent,
live, time-sensitive, or external web information.

DIRECT examples:

"What is Machine Learning?"
"What is Python?"
"What is a deadlock?"
"Explain neural networks"
"What is RAG?"
"How does CNN work?"

RESEARCH examples:

"Latest AI news"
"Last 24 hours news of Delhi"
"Current price of iPhone 17"
"Who won today's cricket match?"
"Latest developments in Generative AI"
"Current weather in Delhi"

Important:

Do NOT choose RESEARCH just because the question is long.

Ask:

"Does answering this question require current web information?"

If NO → DIRECT

If YES → RESEARCH

USER QUESTION:

{question}

Return exactly one route:
DIRECT
or
RESEARCH
"""

    result = router_llm.invoke(prompt)

    route = result.route.upper().strip()

    if route not in ["DIRECT", "RESEARCH"]:
        route = "DIRECT"

    return route


# ============================================================
# DIRECT ANSWER
# ============================================================

def direct_answer(question: str) -> str:
    """
    Answer stable/general questions without web research.
    """

    prompt = f"""
You are an expert AI assistant.

Answer the user's question with a clear, useful, medium-length response.

User question:
{question}

Instructions:
- Keep the answer medium length: not too short and not overly detailed.
- Give enough explanation for the user to understand the topic properly.
- Usually aim for around 300-500 words, depending on the question.
- Start with a clear and direct answer.
- Use Markdown headings only when they improve readability.
- Use bullet points or numbered lists when useful.
- Include a simple example when appropriate.
- Explain important advantages, limitations, or practical applications when relevant.
- Avoid unnecessary background information and repetition.
- Do not make the answer excessively detailed.
- Do not mention agents, routing, pipelines, web research, or internal system processes.

Return only the final answer.
"""

    response = llm.invoke(prompt)

    return response.content


# ============================================================
# SEARCH AGENT
# ============================================================

def build_search_agent():

    return create_agent(
        model=llm,
        tools=[web_search],
        system_prompt="""
You are the Search Agent in a multi-agent AI research system.

Your job is to search the web and find relevant information
for the user's research question.

Instructions:

- Use web_search to search the internet.
- Search for recent and reliable information.
- Prefer authoritative and trustworthy sources.
- Look for multiple relevant sources.
- Collect source titles.
- Collect URLs.
- Collect search snippets.
- Collect publication dates when available.
- Do not invent information.
- Do not write the final answer.
- Return structured research findings for the Reader Agent.

The Reader Agent will later open and analyze the sources.
"""
    )


# ============================================================
# READER AGENT
# ============================================================

def build_reader_agent():

    return create_agent(
        model=llm,
        tools=[scrape_url],
        system_prompt="""
You are the Reader Agent in a multi-agent research system.

Your job is to read the web sources found by the Search Agent.

Instructions:

- Examine the search results provided by the Search Agent.
- Identify the most relevant URLs.
- Use scrape_url to read useful articles/pages.
- Extract important facts and evidence.
- Pay attention to publication dates.
- Pay attention to names, numbers and important claims.
- Compare information across sources when useful.
- Do not invent information.
- If one URL cannot be scraped, use another relevant source.
- Return useful research notes for the Writer Agent.
- Do not write the final polished answer.
"""
    )


# ============================================================
# WRITER AGENT
# ============================================================

def write_report(topic: str, research: str) -> str:
    """
    Generate the final answer from researched information.
    """

    prompt = f"""
You are the Writer Agent in a multi-agent research system.

The user asked:

{topic}


The Search Agent and Reader Agent produced the following research:

{research}


Write the final answer for the user.

IMPORTANT:

If the question asks for current information, news,
recent events or explicit research:

- Provide a well-structured research report.
- Summarize the most important findings.
- Include relevant dates.
- Include source titles and URLs.
- Clearly separate important facts.
- Do not invent information.

If the question is general informational content:

- Keep the answer concise.
- Explain the concept clearly.
- Use simple examples when useful.
- Do not turn it into a long academic research paper.

General rules:

- Use Markdown.
- Do not mention Search Agent.
- Do not mention Reader Agent.
- Do not mention Writer Agent.
- Do not mention the internal pipeline.
- Do not repeat the same information.
- Do not invent facts.
"""

    response = llm.invoke(prompt)

    return response.content