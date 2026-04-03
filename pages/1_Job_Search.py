"""
Job Search Assistant - Streamlit Page

AI-powered tools for job hunting: resume matching, interview prep,
outreach drafting, and company research.
"""

import streamlit as st
from src.job_search import (
    match_resume_to_jd,
    generate_interview_prep,
    draft_outreach_message,
    analyze_company,
)
from src.vectorstore import get_chroma_client, get_or_create_collection


st.set_page_config(
    page_title="Job Search Assistant",
    page_icon="🎯",
    layout="wide",
)

st.markdown("# 🎯 Job Search Assistant")
st.markdown("AI-powered tools to help you land your next role. Make sure your resume "
            "and experience documents are ingested in the Knowledge Base first.")

# Check knowledge base
try:
    client = get_chroma_client()
    collection = get_or_create_collection(client)
    chunk_count = collection.count()
except Exception:
    chunk_count = 0

if chunk_count == 0:
    st.warning("Your knowledge base is empty. Go to the main page and ingest your resume "
               "and other documents first. The job search tools need your background to work.")
    st.stop()

st.success(f"Knowledge base loaded: {chunk_count} chunks available")

# --- Tabs ---
tab1, tab2, tab3, tab4 = st.tabs([
    "📋 Resume-JD Matcher",
    "🎤 Interview Prep",
    "✉️ Outreach Drafter",
    "🏢 Company Research",
])

# --- Tab 1: Resume-JD Matcher ---
with tab1:
    st.markdown("### Match Your Resume to a Job Description")
    st.markdown("Paste a job description below to see how your background aligns, "
                "where the gaps are, and what to emphasize.")

    jd_input = st.text_area(
        "Paste the job description here:",
        height=300,
        key="jd_matcher",
        placeholder="Paste the full job description...",
    )

    if st.button("🔍 Analyze Match", key="match_btn"):
        if not jd_input.strip():
            st.warning("Please paste a job description first.")
        else:
            with st.spinner("Analyzing your fit for this role..."):
                result = match_resume_to_jd(jd_input)
                st.markdown(result)

# --- Tab 2: Interview Prep ---
with tab2:
    st.markdown("### Prepare for Your Interview")
    st.markdown("Get likely questions, STAR-format answers using your real experience, "
                "and a tailored 2-minute pitch. Answers are designed to be technically "
                "specific — not high-level.")

    col1, col2 = st.columns(2)
    with col1:
        company_input = st.text_input(
            "Company name:",
            key="prep_company",
            placeholder="e.g., NVIDIA",
        )
    with col2:
        role_input = st.text_input(
            "Role title (optional):",
            key="prep_role",
            placeholder="e.g., Senior AI Solutions Architect",
        )

    jd_prep_input = st.text_area(
        "Paste the job description:",
        height=300,
        key="jd_prep",
        placeholder="Paste the full job description...",
    )

    if st.button("🎤 Generate Interview Prep", key="prep_btn"):
        if not jd_prep_input.strip():
            st.warning("Please paste a job description first.")
        else:
            with st.spinner("Generating interview prep material..."):
                result = generate_interview_prep(
                    jd_prep_input,
                    company_name=company_input or "",
                )
                st.markdown(result)

# --- Tab 3: Outreach Drafter ---
with tab3:
    st.markdown("### Draft an Outreach Message")
    st.markdown("Generate personalized LinkedIn messages for networking and job search.")

    col1, col2 = st.columns(2)
    with col1:
        contact_name = st.text_input("Contact name:", placeholder="e.g., Kari Ann Briski")
        contact_company = st.text_input("Their company:", placeholder="e.g., NVIDIA")
    with col2:
        contact_role = st.text_input("Their role (optional):", placeholder="e.g., VP Generative AI Software")
        relationship = st.selectbox(
            "Your relationship:",
            [
                "former colleague",
                "former client",
                "met at a conference",
                "mutual connection",
                "cold outreach",
                "former partner/vendor",
            ],
        )

    purpose = st.text_input(
        "Purpose of outreach:",
        value="reconnect and explore opportunities",
        placeholder="e.g., ask about AI architect roles on their team",
    )

    if st.button("✉️ Draft Message", key="outreach_btn"):
        if not contact_name.strip() or not contact_company.strip():
            st.warning("Please fill in at least the contact name and company.")
        else:
            with st.spinner("Drafting personalized message..."):
                result = draft_outreach_message(
                    contact_name=contact_name,
                    contact_company=contact_company,
                    contact_role=contact_role,
                    relationship=relationship,
                    purpose=purpose,
                )
                st.markdown(result)

# --- Tab 4: Company Research ---
with tab4:
    st.markdown("### Company Research Brief")
    st.markdown("Get a quick research brief on a company to prepare for interviews "
                "or outreach. Includes AI strategy, culture, and positioning tips.")

    research_company = st.text_input(
        "Company to research:",
        key="research_company",
        placeholder="e.g., NVIDIA",
    )

    research_jd = st.text_area(
        "Job description (optional — improves relevance):",
        height=200,
        key="research_jd",
        placeholder="Paste JD if you have one...",
    )

    if st.button("🏢 Research Company", key="research_btn"):
        if not research_company.strip():
            st.warning("Please enter a company name.")
        else:
            with st.spinner(f"Researching {research_company}..."):
                result = analyze_company(
                    research_company,
                    job_description=research_jd or "",
                )
                st.markdown(result)