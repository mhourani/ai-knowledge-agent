"""
LangGraph-powered AI Knowledge Agent.

This agent implements a reasoning loop:
1. Analyze the user's question
2. Search the knowledge base
3. Evaluate if results are sufficient
4. Either refine the search or generate a final answer

This is an agentic RAG pattern — the agent decides HOW to search
and WHEN it has enough information to answer, rather than blindly
returning the first results it finds.
"""

import operator
from typing import Annotated, TypedDict, Literal

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import StateGraph, END

from src.config import ANTHROPIC_API_KEY, MODEL_NAME, MAX_TOKENS
from src.vectorstore import search


# --- State Definition ---
# This is the "memory" that flows through the graph.
# Each node can read and write to this state.

class AgentState(TypedDict):
    """State that persists across all nodes in the agent graph."""
    question: str                    # The user's original question
    search_query: str               # The current search query (may differ from question)
    search_results: list            # Results from the vector store
    search_count: int               # How many searches we've done
    answer: str                     # The final generated answer
    is_sufficient: bool             # Whether results are good enough to answer
    chat_history: list              # Previous question/answer pairs for context


# --- LLM Setup ---

def get_llm() -> ChatAnthropic:
    """Create the Claude LLM instance."""
    return ChatAnthropic(
        model=MODEL_NAME,
        api_key=ANTHROPIC_API_KEY,
        max_tokens=MAX_TOKENS,
    )


# --- Node Functions ---
# Each function is a "node" in the graph — a step the agent takes.

def analyze_question(state: AgentState) -> AgentState:
    """
    Node 1: Analyze the question and generate an optimal search query.
    
    The user's question might be conversational or vague.
    This node rewrites it into an effective search query,
    using conversation history to resolve references like
    "tell me more about that" or "the first one."
    """
    llm = get_llm()

    history_text = ""
    if state.get("chat_history"):
        history_text = "Conversation so far:\n"
        for turn in state["chat_history"]:
            history_text += f"User: {turn['question']}\nAssistant: {turn['answer']}\n\n"

    messages = [
        SystemMessage(content=(
            "You are a search query optimizer. Given a user question and "
            "optional conversation history, generate a concise search query "
            "that will find the most relevant information in an enterprise "
            "knowledge base. If the question references something from the "
            "conversation history (like 'that', 'the first one', 'more details'), "
            "resolve the reference into a specific search query. "
            "Return ONLY the search query, nothing else."
        )),
        HumanMessage(content=f"{history_text}User question: {state['question']}"),
    ]

    response = llm.invoke(messages)

    return {
        **state,
        "search_query": response.content,
        "search_count": state.get("search_count", 0),
    }

def search_knowledge_base(state: AgentState) -> AgentState:
    """
    Node 2: Search the vector database using the optimized query.
    """
    results = search(
        query=state["search_query"],
        n_results=3,
    )

    return {
        **state,
        "search_results": results,
        "search_count": state.get("search_count", 0) + 1,
    }


def evaluate_results(state: AgentState) -> AgentState:
    """
    Node 3: Evaluate whether the search results are sufficient
    to answer the user's question.
    
    This is what makes it an AGENT — it reflects on its own
    results and decides whether to try again or proceed.
    """
    llm = get_llm()

    # Format the search results for the LLM to evaluate
    results_text = "\n\n".join(
        f"[Result {i+1}] (relevance: {1 - r['distance']:.2f})\n{r['content']}"
        for i, r in enumerate(state["search_results"])
    )

    messages = [
        SystemMessage(content=(
            "You are evaluating whether search results contain enough "
            "information to answer a user's question. Respond with ONLY "
            "'SUFFICIENT' or 'INSUFFICIENT'. Respond 'SUFFICIENT' if the "
            "results contain relevant information that addresses the core "
            "of the question, even if not perfectly complete."
        )),
        HumanMessage(content=(
            f"Question: {state['question']}\n\n"
            f"Search Results:\n{results_text}"
        )),
    ]

    response = llm.invoke(messages)
    is_sufficient = "SUFFICIENT" in response.content.upper()

    return {
        **state,
        "is_sufficient": is_sufficient,
    }


def refine_search(state: AgentState) -> AgentState:
    """
    Node 4 (conditional): Generate a refined search query
    when initial results weren't sufficient.
    """
    llm = get_llm()

    results_text = "\n".join(
        f"- {r['content'][:100]}..." for r in state["search_results"]
    )

    messages = [
        SystemMessage(content=(
            "The previous search didn't find sufficient information. "
            "Generate a different search query to find better results. "
            "Try using different keywords or approaching the topic from "
            "a different angle. Return ONLY the new search query."
        )),
        HumanMessage(content=(
            f"Original question: {state['question']}\n"
            f"Previous search query: {state['search_query']}\n"
            f"Previous results (insufficient):\n{results_text}"
        )),
    ]

    response = llm.invoke(messages)

    return {
        **state,
        "search_query": response.content,
    }


def generate_answer(state: AgentState) -> AgentState:
    """
    Node 5: Generate the final answer using the search results as context.
    
    This is the "generation" step of RAG — the LLM synthesizes
    information from retrieved documents into a coherent answer.
    Includes conversation history for multi-turn context.
    """
    llm = get_llm()

    results_text = "\n\n".join(
        f"[Source: {r['metadata'].get('source', 'unknown')}]\n{r['content']}"
        for r in state["search_results"]
    )

    # Build conversation history context
    history_text = ""
    if state.get("chat_history"):
        history_text = "Previous conversation:\n"
        for turn in state["chat_history"]:
            history_text += f"User: {turn['question']}\nAssistant: {turn['answer']}\n\n"

    messages = [
        SystemMessage(content=(
            "You are an enterprise AI knowledge assistant. Answer the "
            "user's question based on the provided context. Be specific "
            "and cite which source documents your answer comes from. "
            "If the context doesn't fully address the question, say what "
            "you can and note what information is missing. "
            "Use the conversation history to understand follow-up questions "
            "and maintain continuity."
        )),
        HumanMessage(content=(
            f"{history_text}"
            f"Question: {state['question']}\n\n"
            f"Context from knowledge base:\n{results_text}"
        )),
    ]

    response = llm.invoke(messages)

    return {
        **state,
        "answer": response.content,
    }
# --- Routing Logic ---

def should_refine_or_answer(state: AgentState) -> Literal["refine", "answer"]:
    """
    Conditional edge: decide whether to refine the search or generate an answer.
    
    Gives up after 2 searches to avoid infinite loops.
    """
    if state["is_sufficient"] or state["search_count"] >= 2:
        return "answer"
    return "refine"


# --- Graph Construction ---

def build_agent() -> StateGraph:
    """
    Build the LangGraph agent workflow.
    
    The graph looks like this:
    
    analyze_question → search → evaluate → [answer or refine]
                                               ↑        ↓
                                               └── search ←
    """
    workflow = StateGraph(AgentState)

    # Add nodes
    workflow.add_node("analyze_question", analyze_question)
    workflow.add_node("search_knowledge_base", search_knowledge_base)
    workflow.add_node("evaluate_results", evaluate_results)
    workflow.add_node("refine_search", refine_search)
    workflow.add_node("generate_answer", generate_answer)

    # Define the flow
    workflow.set_entry_point("analyze_question")
    workflow.add_edge("analyze_question", "search_knowledge_base")
    workflow.add_edge("search_knowledge_base", "evaluate_results")

    # Conditional: either refine or answer
    workflow.add_conditional_edges(
        "evaluate_results",
        should_refine_or_answer,
        {
            "refine": "refine_search",
            "answer": "generate_answer",
        },
    )

    # If refining, search again
    workflow.add_edge("refine_search", "search_knowledge_base")

    # End after generating answer
    workflow.add_edge("generate_answer", END)

    return workflow.compile()


class ConversationManager:
    """
    Manages conversation state across multiple questions.
    
    This is what gives the agent "memory" — it tracks previous
    question/answer pairs and passes them to the agent on each turn.
    """

    def __init__(self):
        self.chat_history: list = []

    def ask(self, question: str) -> str:
        """
        Ask the knowledge agent a question with conversation context.
        
        Args:
            question: Natural language question.
            
        Returns:
            The agent's answer based on the knowledge base and conversation history.
        """
        agent = build_agent()

        initial_state = {
            "question": question,
            "search_query": "",
            "search_results": [],
            "search_count": 0,
            "answer": "",
            "is_sufficient": False,
            "chat_history": self.chat_history,
        }

        final_state = agent.invoke(initial_state)

        # Store this turn in history
        self.chat_history.append({
            "question": question,
            "answer": final_state["answer"],
        })

        return final_state["answer"]

    def clear_history(self):
        """Clear conversation history to start fresh."""
        self.chat_history = []
        print("Conversation history cleared.")


# Keep a simple ask() function for backward compatibility
def ask(question: str) -> str:
    """Simple single-question interface (no memory)."""
    manager = ConversationManager()
    return manager.ask(question)