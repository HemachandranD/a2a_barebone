"""LangGraph RAG agent over the seeded policy/manual documents."""

import re
from pathlib import Path
from typing import List, TypedDict

from ...shared import config
from ...shared.llm import langchain_llm


class RagState(TypedDict):
    question: str
    chunks: List[str]
    answer: str


_STOPWORDS = {
    "the", "a", "an", "of", "and", "or", "to", "in", "on", "for", "is", "are",
    "was", "were", "be", "been", "with", "what", "how", "when", "does", "do",
    "did", "our", "we", "you", "your", "i", "can", "many", "much", "there",
}


def _load_chunks(docs_dir: Path = config.SEED_DOCS_DIR) -> List[dict]:
    chunks: List[dict] = []
    for md in sorted(docs_dir.glob("*.md")):
        text = md.read_text(encoding="utf-8")
        current_heading = md.stem
        buffer: List[str] = []
        for line in text.splitlines():
            if line.startswith("## "):
                if buffer:
                    chunks.append(
                        {"source": md.name, "heading": current_heading, "text": "\n".join(buffer).strip()}
                    )
                current_heading = line[3:].strip()
                buffer = [line]
            else:
                buffer.append(line)
        if buffer:
            chunks.append(
                {"source": md.name, "heading": current_heading, "text": "\n".join(buffer).strip()}
            )
    return [c for c in chunks if c["text"]]


_CHUNK_CACHE: List[dict] | None = None


def _chunks() -> List[dict]:
    global _CHUNK_CACHE
    if _CHUNK_CACHE is None:
        _CHUNK_CACHE = _load_chunks()
    return _CHUNK_CACHE


def _tokenize(text: str) -> set[str]:
    return {
        t.lower() for t in re.findall(r"[A-Za-z0-9]+", text) if t.lower() not in _STOPWORDS
    }


def retrieve(state: RagState) -> RagState:
    q_tokens = _tokenize(state["question"])
    scored: list[tuple[int, dict]] = []
    for c in _chunks():
        c_tokens = _tokenize(c["text"])
        overlap = len(q_tokens & c_tokens)
        if overlap:
            scored.append((overlap, c))
    scored.sort(key=lambda x: x[0], reverse=True)
    top = scored[:3] if scored else [(0, c) for c in _chunks()[:2]]
    picked = [
        f"[{c['source']} > {c['heading']}]\n{c['text']}" for _, c in top
    ]
    return {"question": state["question"], "chunks": picked, "answer": ""}


def generate(state: RagState) -> RagState:
    llm = langchain_llm(config.RAG_MODEL)
    context = "\n\n---\n\n".join(state["chunks"])
    prompt = (
        "You are a policy assistant. Answer the user's question using ONLY the context. "
        "If the answer is not in the context, say you don't know. "
        "Cite the source document at the end of each fact in square brackets.\n\n"
        f"Context:\n{context}\n\n"
        f"Question: {state['question']}"
    )
    response = llm.invoke(prompt)
    answer = getattr(response, "content", str(response))
    return {"question": state["question"], "chunks": state["chunks"], "answer": answer}


def _build_graph():
    from langgraph.graph import END, START, StateGraph

    graph = StateGraph(RagState)
    graph.add_node("retrieve", retrieve)
    graph.add_node("generate", generate)
    graph.add_edge(START, "retrieve")
    graph.add_edge("retrieve", "generate")
    graph.add_edge("generate", END)
    return graph.compile()


_GRAPH = None


def _graph():
    global _GRAPH
    if _GRAPH is None:
        _GRAPH = _build_graph()
    return _GRAPH


async def invoke(query: str) -> str:
    from real_a2a.shared.observent_capture import capture_output, open_or_enrich_span, set_error, set_ok

    with open_or_enrich_span(
        {"query": query},
        name="rag.run",
        agent_name="rag",
        agent_role="policy-qa",
        agent_framework="langgraph",
    ) as span:
        try:
            result = await _graph().ainvoke({"question": query, "chunks": [], "answer": ""})
        except BaseException as exc:
            set_error(exc, span)
            raise
        answer = result["answer"]
        capture_output(answer, span)
        set_ok(span)
        return answer
