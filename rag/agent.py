"""
Agentic Reasoning Engine (ReAct-style)
For questions that need MULTIPLE queries to answer (e.g. "compare this year's
opioid spend to last year's and tell me if any state is a growing concern"),
a single NL2SQL call isn't enough. This agent plans a sequence of tool calls
(SQL queries, knowledge retrieval) and synthesizes a final answer — a scaled-
down ReAct (Reason+Act) loop, the same pattern behind LangChain/LangGraph agents.

Tools available to the agent:
  - query_database(sql_question: str) → runs NL2SQL and returns results
  - retrieve_knowledge(topic: str)    → RAG lookup for domain context
  - finish(answer: str)               → ends the loop with the final answer
"""

import os
import json
import logging
from openai import OpenAI

from nlsql.nl_to_sql import process_nl_query
from rag.retriever import retrieve_knowledge_context

logger = logging.getLogger("RAGAgent")
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY", "not-configured"))  # lazy-safe: client construction never validates the key; only an actual API call would fail, and DEMO_MODE routes around every such call site

MAX_AGENT_STEPS = 5

AGENT_SYSTEM_PROMPT = """You are a healthcare data analysis agent. You answer complex,
multi-part questions by breaking them into steps and using tools. At each step, decide
the next action.

Available tools:
1. query_database(question) — runs a natural-language question against the Medicare Part D
   data warehouse and returns SQL + results. Use for anything requiring actual numbers.
2. retrieve_knowledge(topic) — retrieves domain knowledge/context (drug policy, CMS rules,
   cost-driver explanations). Use for "why" or "what does X mean" type sub-questions.
3. finish(answer) — call this when you have enough information to give the final answer.

Respond ONLY with JSON in this exact format:
{"thought": "your reasoning", "action": "query_database|retrieve_knowledge|finish", "action_input": "..."}

Keep thoughts brief. Use at most 4 tool calls before finishing.
"""


def _call_tool(action: str, action_input: str) -> str:
    """Executes the chosen tool and returns an observation string for the agent."""
    if action == "query_database":
        try:
            result = process_nl_query(action_input)
            return (
                f"SQL: {result['generated_sql']}\n"
                f"Row count: {result['row_count']}\n"
                f"Summary: {result['summary']}\n"
                f"Sample data: {result['results'][:5]}"
            )
        except Exception as e:
            return f"Query failed: {str(e)}"

    elif action == "retrieve_knowledge":
        hits = retrieve_knowledge_context(action_input, top_k=2)
        if not hits:
            return "No relevant domain knowledge found."
        return "\n---\n".join(h["document"] for h in hits)

    return f"Unknown tool: {action}"


def run_agent(question: str) -> dict:
    """
    Executes the ReAct loop: Thought → Action → Observation → repeat → Finish.
    Returns the final answer plus a full trace of the reasoning steps taken
    (surfaced in the UI so the user can see *how* the agent got its answer —
    critical for trust in a healthcare analytics context).
    """
    messages = [
        {"role": "system", "content": AGENT_SYSTEM_PROMPT},
        {"role": "user", "content": question},
    ]
    trace = []

    for step in range(MAX_AGENT_STEPS):
        response = client.chat.completions.create(
            model="gpt-4o",
            temperature=0,
            messages=messages,
            response_format={"type": "json_object"},
        )
        raw = response.choices[0].message.content
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            trace.append({"step": step, "error": f"Malformed agent output: {raw}"})
            break

        thought = parsed.get("thought", "")
        action = parsed.get("action", "")
        action_input = parsed.get("action_input", "")

        logger.info(f"[Agent step {step}] Thought: {thought} | Action: {action}({action_input})")

        if action == "finish":
            trace.append({"step": step, "thought": thought, "action": "finish"})
            return {
                "question": question,
                "answer": action_input,
                "steps_taken": step + 1,
                "trace": trace,
            }

        observation = _call_tool(action, action_input)
        trace.append({
            "step": step, "thought": thought, "action": action,
            "action_input": action_input, "observation": observation,
        })

        messages.append({"role": "assistant", "content": raw})
        messages.append({"role": "user", "content": f"Observation: {observation}"})

    # Hit max steps without explicit finish — force a synthesis
    messages.append({"role": "user", "content": "You must finish now. Summarize your findings as the final answer (plain text, no JSON)."})
    final_response = client.chat.completions.create(
        model="gpt-4o", temperature=0.2,
        messages=[{"role": "system", "content": "Summarize the analysis into a final answer."}] + messages[1:],
    )
    return {
        "question": question,
        "answer": final_response.choices[0].message.content.strip(),
        "steps_taken": MAX_AGENT_STEPS,
        "trace": trace,
        "note": "Reached max reasoning steps — answer synthesized from partial findings.",
    }
