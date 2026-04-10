"""
Image generation capabilities for the AI Knowledge Agent.

Three modes:
1. Charts & visualizations from data (matplotlib/plotly)
2. Architecture & flow diagrams (Mermaid syntax)
3. AI-generated images from text prompts (DALL-E, optional)
"""

from multiprocessing import context
import os
import json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import plotly.graph_objects as go
import plotly.io as pio
from typing import Optional

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import SystemMessage, HumanMessage

from src.config import ANTHROPIC_API_KEY, MODEL_NAME

# Output directory for generated images
OUTPUT_DIR = "generated_images"


def get_llm() -> ChatAnthropic:
    """Create the Claude LLM instance."""
    return ChatAnthropic(
        model=MODEL_NAME,
        api_key=ANTHROPIC_API_KEY,
        max_tokens=4096,
    )


def ensure_output_dir():
    """Create output directory if it doesn't exist."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)


# --- Chart Generation ---

def generate_chart(prompt: str, data_context: str = "") -> dict:
    """
    Generate a chart using matplotlib based on a natural language description.
    
    Claude writes the matplotlib code, then we execute it safely.
    
    Args:
        prompt: Description of the chart to create.
        data_context: Optional data from the knowledge base to visualize.
        
    Returns:
        Dict with 'filepath' and 'description' keys.
    """
    ensure_output_dir()
    llm = get_llm()

    data_section = f"\n\nAvailable data:\n{data_context}" if data_context else ""
    messages = [
        SystemMessage(content=(
            "You are a data visualization expert. Generate Python matplotlib code "
            "to create the requested chart. Follow these rules strictly:\n\n"
            "1. Return ONLY valid Python code, no markdown fences, no explanation\n"
            "2. Import matplotlib.pyplot as plt at the top\n"
            "3. Use plt.figure(figsize=(10, 6)) for consistent sizing\n"
            "4. Always include title, axis labels, and legend where appropriate\n"
            "5. Use a clean, professional style: plt.style.use('seaborn-v0_8-whitegrid')\n"
            "6. Save the figure with: plt.savefig('OUTPUT_PATH', dpi=150, bbox_inches='tight')\n"
            "7. End with plt.close()\n"
            "8. If sample data is needed, create realistic data inline\n"
            "9. Use colors that are professional and accessible\n"
            "10. DO NOT call plt.show()\n\n"
            "Replace OUTPUT_PATH with the exact string 'OUTPUT_PATH' — it will be replaced later."
        )),
        HumanMessage(content=f"Create this chart: {prompt}{data_section}"),
    ]

    response = llm.invoke(messages)
    code = response.content.strip()

    # Clean up code - remove markdown fences if present
    if code.startswith("```"):
        code = "\n".join(code.split("\n")[1:])
    if code.endswith("```"):
        code = "\n".join(code.split("\n")[:-1])

    # Set output path
    filename = f"chart_{hash(prompt) % 10000:04d}.png"
    filepath = os.path.join(OUTPUT_DIR, filename)
    code = code.replace("OUTPUT_PATH", filepath)

    # Execute the code
    try:
        exec_globals = {}
        exec(code, exec_globals)

        if os.path.exists(filepath):
            return {
                "filepath": filepath,
                "description": f"Chart generated: {prompt}",
                "code": code,
            }
        else:
            return {"error": "Chart code executed but no image was saved."}
    except Exception as e:
        return {"error": f"Chart generation failed: {str(e)}", "code": code}


# --- Diagram Generation ---

def generate_mermaid_diagram(prompt: str, context: str = "") -> dict:
    """
    Generate a Mermaid diagram based on a natural language description.
    
    Returns the Mermaid syntax for rendering in Streamlit.
    
    Args:
        prompt: Description of the diagram to create.
        context: Optional context from the knowledge base.
        
    Returns:
        Dict with 'mermaid_code' and 'description' keys.
    """
    llm = get_llm()

    context_section = f"\n\nContext:\n{context}" if context else ""
    messages = [
        SystemMessage(content=(
            "You are a technical diagram expert. Generate Mermaid diagram syntax "
            "for the requested diagram. Follow these rules:\n\n"
            "1. Return ONLY valid Mermaid syntax, no markdown fences, no explanation\n"
            "2. Use clear, descriptive labels for all nodes\n"
            "3. Use appropriate diagram types:\n"
            "   - flowchart TD/LR for process flows\n"
            "   - sequenceDiagram for API/service interactions\n"
            "   - classDiagram for data models\n"
            "   - erDiagram for database schemas\n"
            "   - gantt for project timelines\n"
            "   - graph for architecture diagrams\n"
            "4. Keep it readable — don't overcomplicate\n"
            "5. Use styling where it adds clarity"
        )),
        HumanMessage(content=f"Create this diagram: {prompt}{context_section}"),
    ]

    response = llm.invoke(messages)
    mermaid_code = response.content.strip()

    # Clean up
    if mermaid_code.startswith("```"):
        mermaid_code = "\n".join(mermaid_code.split("\n")[1:])
    if mermaid_code.endswith("```"):
        mermaid_code = "\n".join(mermaid_code.split("\n")[:-1])

    return {
        "mermaid_code": mermaid_code,
        "description": f"Diagram generated: {prompt}",
    }


# --- Architecture Diagram from Knowledge Base ---

def generate_architecture_from_docs(topic: str, search_results: list) -> dict:
    """
    Generate an architecture diagram based on knowledge base content.
    
    Args:
        topic: The system or architecture to diagram.
        search_results: Relevant chunks from the vector store.
        
    Returns:
        Dict with 'mermaid_code' and 'description'.
    """
    context = "\n\n".join(
        f"[{r['metadata'].get('source', 'unknown')}]: {r['content']}"
        for r in search_results
    )

    return generate_mermaid_diagram(
        prompt=f"Create a detailed architecture diagram for: {topic}",
        context=context,
    )


# --- DALL-E Integration (Optional) ---

def generate_dalle_image(prompt: str, api_key: Optional[str] = None) -> dict:
    """
    Generate an image using OpenAI's DALL-E 3.
    
    Requires an OpenAI API key. Set OPENAI_API_KEY in .env or pass directly.
    
    Args:
        prompt: Text description of the image to generate.
        api_key: OpenAI API key. Falls back to environment variable.
        
    Returns:
        Dict with 'filepath', 'url', and 'description' keys.
    """
    ensure_output_dir()

    key = api_key or os.getenv("OPENAI_API_KEY")
    if not key:
        return {"error": "OpenAI API key required. Set OPENAI_API_KEY in your .env file."}

    try:
        import requests

        response = requests.post(
            "https://api.openai.com/v1/images/generations",
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
            },
            json={
                "model": "dall-e-3",
                "prompt": prompt,
                "n": 1,
                "size": "1024x1024",
                "quality": "standard",
            },
        )

        response.raise_for_status()
        data = response.json()

        image_url = data["data"][0]["url"]
        revised_prompt = data["data"][0].get("revised_prompt", prompt)

        # Download the image
        img_response = requests.get(image_url)
        img_response.raise_for_status()

        filename = f"dalle_{hash(prompt) % 10000:04d}.png"
        filepath = os.path.join(OUTPUT_DIR, filename)

        with open(filepath, "wb") as f:
            f.write(img_response.content)

        return {
            "filepath": filepath,
            "url": image_url,
            "description": revised_prompt,
        }

    except ImportError:
        return {"error": "requests library required. Run: pip install requests"}
    except Exception as e:
        return {"error": f"DALL-E generation failed: {str(e)}"}
    
def generate_chart_from_file(filepath: str, prompt: str) -> dict:
    """
    Generate a chart by analyzing a file directly with pandas,
    bypassing the vector store. Better for large datasets.
    
    Args:
        filepath: Path to the data file (xlsx, csv).
        prompt: Description of the chart to create.
        
    Returns:
        Dict with 'filepath' and 'description' keys.
    """
    ensure_output_dir()
    import pandas as pd

    ext = os.path.splitext(filepath)[1].lower()

    # Read the file and get a data summary
    try:
        if ext in [".xlsx", ".xls"]:
            df = pd.read_excel(filepath)
        elif ext == ".csv":
            df = pd.read_csv(filepath)
        else:
            return {"error": f"Unsupported file type: {ext}. Use xlsx or csv."}
    except Exception as e:
        return {"error": f"Failed to read file: {e}"}

    # Build a comprehensive data summary for Claude
    columns_info = f"Columns: {list(df.columns)}"
    shape_info = f"Rows: {len(df)}, Columns: {len(df.columns)}"
    dtypes_info = f"Data types:\n{df.dtypes.to_string()}"
    sample_rows = f"First 5 rows:\n{df.head().to_string()}"

    # For each column, provide value counts if categorical
    column_summaries = []
    for col in df.columns:
        nunique = df[col].nunique()
        if nunique <= 50 and df[col].dtype == "object":
            counts = df[col].value_counts().head(30).to_string()
            column_summaries.append(f"\nValue counts for '{col}' ({nunique} unique):\n{counts}")
        elif nunique > 50 and df[col].dtype == "object":
            top_counts = df[col].value_counts().head(50).to_string()
            column_summaries.append(
                f"\nTop 50 value counts for '{col}' ({nunique} unique total):\n{top_counts}"
            )
        elif df[col].dtype in ["int64", "float64"]:
            stats = df[col].describe().to_string()
            column_summaries.append(f"\nStats for '{col}':\n{stats}")

    full_summary = "\n".join([
        shape_info,
        columns_info,
        dtypes_info,
        sample_rows,
        "\n--- Column Analysis ---",
        "\n".join(column_summaries),
    ])

    llm = get_llm()

    messages = [
        SystemMessage(content=(
            "You are a data visualization expert. Generate Python code using "
            "matplotlib AND pandas to create the requested chart.\n\n"
            "CRITICAL RULES:\n"
            "1. Return ONLY valid Python code, no markdown fences, no explanation\n"
            "2. FIRST import pandas and read the source file directly:\n"
            "   import pandas as pd\n"
            "   df = pd.read_excel('SOURCE_PATH')  # or read_csv\n"
            "3. Do ALL data processing in pandas — groupby, value_counts, sort, filter, etc.\n"
            "4. Then plot using matplotlib\n"
            "5. Use plt.figure(figsize=(14, 8)) for readability with many categories\n"
            "6. Rotate x-axis labels if there are many categories: plt.xticks(rotation=45, ha='right')\n"
            "7. Always include title and axis labels\n"
            "8. Use plt.tight_layout() before saving\n"
            "9. Save with: plt.savefig('OUTPUT_PATH', dpi=150, bbox_inches='tight')\n"
            "10. End with plt.close()\n"
            "11. DO NOT call plt.show()\n"
            "12. Show top 30 categories max for readability — but PROCESS ALL DATA for counts\n\n"
            "Replace SOURCE_PATH and OUTPUT_PATH with those exact strings — they will be replaced later."
        )),
        HumanMessage(content=(
            f"Create this chart: {prompt}\n\n"
            f"Data file summary:\n{full_summary}"
        )),
    ]

    response = llm.invoke(messages)
    code = response.content.strip()

    if code.startswith("```"):
        code = "\n".join(code.split("\n")[1:])
    if code.endswith("```"):
        code = "\n".join(code.split("\n")[:-1])

    filename = f"chart_file_{hash(prompt) % 10000:04d}.png"
    out_filepath = os.path.join(OUTPUT_DIR, filename)
    code = code.replace("OUTPUT_PATH", out_filepath)
    code = code.replace("SOURCE_PATH", filepath)

    try:
        exec_globals = {}
        exec(code, exec_globals)

        if os.path.exists(out_filepath):
            return {
                "filepath": out_filepath,
                "description": f"Chart generated from {os.path.basename(filepath)}: {prompt}",
                "code": code,
            }
        else:
            return {"error": "Chart code executed but no image was saved.", "code": code}
    except Exception as e:
        return {"error": f"Chart generation failed: {str(e)}", "code": code}