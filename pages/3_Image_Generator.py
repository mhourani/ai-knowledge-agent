"""
Image Generator - Streamlit Page

Generate charts, architecture diagrams, and AI images
from natural language descriptions.
"""

import streamlit as st
import os
from src.image_gen import (
    generate_chart,
    generate_mermaid_diagram,
    generate_architecture_from_docs,
    generate_dalle_image,
)
from src.vectorstore import search, get_chroma_client, get_or_create_collection


st.set_page_config(
    page_title="Image Generator",
    page_icon="🎨",
    layout="wide",
)

st.markdown("# 🎨 Image Generator")
st.markdown("Generate charts, diagrams, and AI images from natural language descriptions.")

tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Charts & Graphs",
    "🏗️ Architecture Diagrams",
    "🎯 From Knowledge Base",
    "🖼️ AI Image Generation (DALL-E)",
])

# --- Tab 1: Charts ---
with tab1:
    st.markdown("### Generate Charts & Visualizations")
    st.markdown("Describe the chart you want. Optionally pull data from your knowledge base.")

    chart_prompt = st.text_area(
        "Describe your chart:",
        height=100,
        key="chart_prompt",
        placeholder="e.g., Bar chart comparing revenue growth across Q1-Q4 2025 for three product lines",
    )

data_source = st.radio(
        "Data source:",
        ["Analyze file directly (best for large data)", "Search knowledge base", "Enter data manually", "Let Claude use sample data"],
        key="data_source",
        horizontal=True,
    )

if data_source == "Analyze file directly (best for large data)":
        import glob
        data_files = sorted(
            glob.glob(os.path.join("docs", "*.xlsx"))
            + glob.glob(os.path.join("docs", "*.csv"))
            + glob.glob(os.path.join("docs", "*.xls"))
        )

        if not data_files:
            st.warning("No xlsx or csv files found in docs/ folder.")
        else:
            display_names = [os.path.basename(f) for f in data_files]
            selected_idx = st.selectbox(
                "Select data file:",
                range(len(display_names)),
                format_func=lambda i: display_names[i],
                key="direct_file_select",
            )
            selected_file = data_files[selected_idx]

            # Preview the file
            try:
                import pandas as pd
                preview_df = pd.read_excel(selected_file) if selected_file.endswith(('.xlsx', '.xls')) else pd.read_csv(selected_file)
                with st.expander(f"Preview: {display_names[selected_idx]} ({len(preview_df)} rows, {len(preview_df.columns)} columns)"):
                    st.dataframe(preview_df.head(20))
                    st.markdown(f"**Columns:** {', '.join(preview_df.columns)}")
            except Exception as e:
                st.warning(f"Could not preview: {e}")

elif data_source == "Enter data manually":
    chart_data = st.text_area(
        "Paste your data:",
        height=100,
        key="chart_data_manual",
        placeholder="e.g., Q1: 10M, Q2: 15M, Q3: 12M, Q4: 20M",
    )
    
elif data_source == "Search knowledge base":
    try:
        client = get_chroma_client()
        collection = get_or_create_collection(client)
        kb_count = collection.count()
    except Exception:
        kb_count = 0

    if kb_count == 0:
        st.warning("Knowledge base is empty. Ingest documents first.")
    else:
        kb_query = st.text_input(
            "Search knowledge base for data:",
            key="chart_kb_query",
            placeholder="e.g., budget numbers, revenue data, project timeline",
        )
        if kb_query:
            with st.spinner("Searching..."):
                results = search(kb_query, n_results=20)
                if results:
                    # Group by source and let user pick which docs to include
                    sources = {}
                    for r in results:
                        src = r["metadata"].get("source", "unknown")
                        if src not in sources:
                            sources[src] = []
                        sources[src].append(r["content"])

                    selected_sources = st.multiselect(
                        "Select which documents to use:",
                        options=list(sources.keys()),
                        default=list(sources.keys()),
                        key="chart_sources",
                    )

                    chart_data = ""
                    for src in selected_sources:
                        chart_data += f"\n\n[Data from {src}]:\n" + "\n".join(sources[src])

                    with st.expander(f"Data preview ({len(chart_data)} characters)"):
                        st.text(chart_data[:3000])
                else:
                    st.info("No relevant data found. Try different search terms.")

if st.button("📊 Generate Chart", key="gen_chart"):
    if not chart_prompt.strip():
        st.warning("Please describe the chart you want.")
    else:
        if data_source == "Analyze file directly (best for large data)" and 'selected_file' in dir():
            with st.spinner("Analyzing full dataset and generating chart..."):
                from src.image_gen import generate_chart_from_file
                result = generate_chart_from_file(selected_file, chart_prompt)
        else:
            with st.spinner("Claude is writing chart code..."):
                result = generate_chart(chart_prompt, data_context=chart_data)

        if "error" in result:
            st.error(result["error"])
            if "code" in result:
                with st.expander("View generated code"):
                    st.code(result["code"], language="python")
        else:
            st.image(result["filepath"])
            st.success(result["description"])

            with st.expander("View generated code"):
                st.code(result.get("code", ""), language="python")

            with open(result["filepath"], "rb") as f:
                st.download_button(
                    "⬇️ Download Chart",
                    data=f,
                    file_name=os.path.basename(result["filepath"]),
                    mime="image/png",
                )
                        
# --- Tab 2: Diagrams ---
with tab2:
    st.markdown("### Generate Architecture & Flow Diagrams")
    st.markdown("Describe your diagram and Claude will generate it using Mermaid syntax.")

    diagram_prompt = st.text_area(
        "Describe your diagram:",
        height=100,
        key="diagram_prompt",
        placeholder="e.g., Agentic RAG system with query analysis, vector search, evaluation loop, and answer generation",
    )

    diagram_type = st.selectbox(
        "Preferred diagram type:",
        [
            "Auto-detect (let Claude decide)",
            "Flowchart",
            "Sequence Diagram",
            "Class Diagram",
            "ER Diagram",
            "Gantt Chart",
        ],
        key="diagram_type",
    )

    if st.button("🏗️ Generate Diagram", key="gen_diagram"):
        if not diagram_prompt.strip():
            st.warning("Please describe the diagram you want.")
        else:
            full_prompt = diagram_prompt
            if diagram_type != "Auto-detect (let Claude decide)":
                full_prompt += f"\n\nUse a {diagram_type} format."

            with st.spinner("Claude is designing the diagram..."):
                result = generate_mermaid_diagram(full_prompt)

                if "error" in result:
                    st.error(result["error"])
                else:
                    st.markdown("#### Generated Diagram")
                    try:
                        st.markdown(f"```mermaid\n{result['mermaid_code']}\n```")
                    except Exception:
                        pass

                    with st.expander("View Mermaid code (copy for docs or presentations)"):
                        st.code(result["mermaid_code"], language="mermaid")
                        st.markdown(
                            "💡 *Paste this code into [mermaid.live](https://mermaid.live) "
                            "to edit, export as PNG/SVG, or embed in documentation.*"
                        )

# --- Tab 3: From Knowledge Base ---
with tab3:
    st.markdown("### Generate Diagrams from Your Documents")
    st.markdown("Search your knowledge base and generate architecture diagrams from the content.")

    try:
        client = get_chroma_client()
        collection = get_or_create_collection(client)
        chunk_count = collection.count()
    except Exception:
        chunk_count = 0

    if chunk_count == 0:
        st.warning("Knowledge base is empty. Ingest documents first.")
    else:
        st.info(f"Knowledge base has {chunk_count} chunks available.")

        kb_topic = st.text_input(
            "What system or architecture do you want to diagram?",
            key="kb_topic",
            placeholder="e.g., The AI-as-a-Service platform architecture",
        )

        if st.button("🎯 Generate from Knowledge Base", key="gen_kb"):
            if not kb_topic.strip():
                st.warning("Please enter a topic.")
            else:
                with st.spinner("Searching knowledge base and generating diagram..."):
                    results = search(kb_topic, n_results=8)
                    if not results:
                        st.warning("No relevant content found.")
                    else:
                        result = generate_architecture_from_docs(kb_topic, results)

                        st.markdown("#### Sources Used")
                        sources = set(r["metadata"].get("source", "unknown") for r in results)
                        for s in sources:
                            st.markdown(f"- 📄 {s}")

                        st.markdown("#### Generated Diagram")
                        try:
                            st.markdown(f"```mermaid\n{result['mermaid_code']}\n```")
                        except Exception:
                            pass

                        with st.expander("View Mermaid code"):
                            st.code(result["mermaid_code"], language="mermaid")

# --- Tab 4: DALL-E ---
with tab4:
    st.markdown("### AI Image Generation with DALL-E 3")
    st.markdown("Generate images from text descriptions using OpenAI's DALL-E 3.")

    dalle_key = os.getenv("OPENAI_API_KEY", "")

    if not dalle_key:
        st.info(
            "To use DALL-E, add your OpenAI API key to the `.env` file:\n\n"
            "`OPENAI_API_KEY=your-key-here`\n\n"
            "Get a key at [platform.openai.com](https://platform.openai.com/api-keys). "
            "DALL-E 3 costs about $0.04 per image."
        )

        dalle_key_input = st.text_input(
            "Or enter your OpenAI API key here (not saved):",
            type="password",
            key="dalle_key_input",
        )
        if dalle_key_input:
            dalle_key = dalle_key_input

    if dalle_key:
        dalle_prompt = st.text_area(
            "Describe the image you want to generate:",
            height=100,
            key="dalle_prompt",
            placeholder="e.g., A professional illustration of an AI system processing enterprise documents, modern flat design style",
        )

        if st.button("🖼️ Generate Image", key="gen_dalle"):
            if not dalle_prompt.strip():
                st.warning("Please describe the image you want.")
            else:
                with st.spinner("DALL-E is creating your image... (15-30 seconds)"):
                    result = generate_dalle_image(dalle_prompt, api_key=dalle_key)

                    if "error" in result:
                        st.error(result["error"])
                    else:
                        st.image(result["filepath"])
                        st.markdown(f"**DALL-E's interpretation:** {result['description']}")

                        with open(result["filepath"], "rb") as f:
                            st.download_button(
                                "⬇️ Download Image",
                                data=f,
                                file_name=os.path.basename(result["filepath"]),
                                mime="image/png",
                            )
