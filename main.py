"""
AI Knowledge Agent - Command Line Interface

An enterprise-grade agentic RAG system powered by LangGraph,
ChromaDB, and Anthropic's Claude.

Usage:
    python main.py ingest    Load documents from /docs into the knowledge base
    python main.py ask       Start an interactive Q&A session
    python main.py reset     Clear the knowledge base
"""

import sys

from src.loader import load_documents, split_documents
from src.vectorstore import ingest_documents, reset_collection
from src.agent import ask


def cmd_ingest():
    """Load and ingest documents into the vector store."""
    print("Loading documents...")
    docs = load_documents()
    if not docs:
        print("No documents found in /docs. Add some files and try again.")
        return
    chunks = split_documents(docs)
    ingest_documents(chunks)
    print("\nKnowledge base is ready.")


def cmd_ask():
    """Start an interactive Q&A session with conversation memory."""
    from src.agent import ConversationManager
    
    print("AI Knowledge Agent")
    print("=" * 40)
    print("Ask questions about your knowledge base.")
    print("Type 'clear' to reset conversation memory.")
    print("Type 'quit' to exit.\n")

    conversation = ConversationManager()

    while True:
        question = input("You: ").strip()
        if not question:
            continue
        if question.lower() in ("quit", "exit", "q"):
            print("Goodbye.")
            break
        if question.lower() == "clear":
            conversation.clear_history()
            continue

        print("\nThinking...\n")
        try:
            answer = conversation.ask(question)
            print(f"Agent: {answer}\n")
        except Exception as e:
            print(f"Error: {e}\n")

def cmd_reset():
    """Reset the knowledge base."""
    confirm = input("This will delete all ingested documents. Are you sure? (y/n): ")
    if confirm.lower() == "y":
        reset_collection()
        print("Knowledge base has been reset.")
    else:
        print("Cancelled.")


def main():
    """Route to the appropriate command."""
    if len(sys.argv) < 2:
        print(__doc__)
        return

    command = sys.argv[1].lower()

    commands = {
        "ingest": cmd_ingest,
        "ask": cmd_ask,
        "reset": cmd_reset,
    }

    if command not in commands:
        print(f"Unknown command: {command}")
        print(__doc__)
        return

    commands[command]()


if __name__ == "__main__":
    main()
