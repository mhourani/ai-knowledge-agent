"""
Job Search Assistant - AI-powered tools for job hunting.

Uses Claude to analyze job descriptions, prepare for interviews,
and draft outreach messages based on your resume and experience.
"""

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import SystemMessage, HumanMessage

from src.config import ANTHROPIC_API_KEY, MODEL_NAME, MAX_TOKENS
from src.vectorstore import search


def get_llm() -> ChatAnthropic:
    """Create the Claude LLM instance."""
    return ChatAnthropic(
        model=MODEL_NAME,
        api_key=ANTHROPIC_API_KEY,
        max_tokens=4096,
    )


def match_resume_to_jd(job_description: str) -> str:
    """
    Analyze how the user's resume and experience match a job description.
    
    Searches the knowledge base for relevant experience, then generates
    a detailed match analysis with strengths, gaps, and recommendations.
    """
    llm = get_llm()

    # Search for relevant experience across all loaded documents
    experience_results = search(query="work experience skills accomplishments", n_results=10)
    technical_results = search(query="technical expertise programming languages tools", n_results=5)

    context = "\n\n".join(
        f"[Source: {r['metadata'].get('source', 'unknown')}]\n{r['content']}"
        for r in experience_results + technical_results
    )

    messages = [
        SystemMessage(content=(
            "You are an expert career advisor and resume analyst. Analyze how "
            "the candidate's background (provided as context from their knowledge base) "
            "matches the job description. Provide:\n\n"
            "1. **Match Score**: An overall fit rating (Strong Match / Good Match / "
            "Partial Match / Weak Match) with a brief explanation.\n\n"
            "2. **Key Strengths**: Specific experiences and skills from the candidate's "
            "background that directly address requirements in the JD. Be specific — "
            "reference actual projects, technologies, and accomplishments.\n\n"
            "3. **Gaps to Address**: Requirements in the JD where the candidate's "
            "experience is thin or missing. For each gap, suggest how to address it "
            "(upskill, reframe existing experience, or acknowledge honestly).\n\n"
            "4. **Talking Points**: 3-5 specific things the candidate should emphasize "
            "in an interview for this role. Each should connect a specific experience "
            "to a specific requirement in the JD.\n\n"
            "5. **Red Flags to Prepare For**: Anything in the candidate's background "
            "that might concern a hiring manager for this role, and how to address it.\n\n"
            "Be direct and honest. The candidate needs actionable guidance, not flattery."
        )),
        HumanMessage(content=(
            f"Candidate's Background:\n{context}\n\n"
            f"Job Description:\n{job_description}"
        )),
    ]

    response = llm.invoke(messages)
    return response.content


def generate_interview_prep(job_description: str, company_name: str = "") -> str:
    """
    Generate likely interview questions and STAR-format answer outlines
    based on the job description and the candidate's experience.
    """
    llm = get_llm()

    # Search for relevant experience
    experience_results = search(query="projects achievements leadership architecture", n_results=10)
    technical_results = search(query="AI ML platforms tools hands-on implementation", n_results=5)

    context = "\n\n".join(
        f"[Source: {r['metadata'].get('source', 'unknown')}]\n{r['content']}"
        for r in experience_results + technical_results
    )

    company_context = f" at {company_name}" if company_name else ""

    messages = [
        SystemMessage(content=(
            "You are an expert technical interview coach specializing in senior "
            "AI/ML architecture roles. Based on the job description and the "
            "candidate's background, generate interview preparation material.\n\n"
            "IMPORTANT: The candidate has received feedback that they are 'too high-level' "
            "in interviews. Every answer must lead with SPECIFIC technical details — "
            "tools, frameworks, architecture decisions, metrics — before any strategic framing.\n\n"
            "Provide:\n\n"
            "1. **Top 8 Likely Interview Questions**: Mix of technical, behavioral, and "
            "situational questions specific to this role.\n\n"
            "2. **STAR Answer Outlines**: For each question, provide a structured answer "
            "using the candidate's actual experience:\n"
            "   - **Situation**: Specific context (company, team, problem)\n"
            "   - **Task**: What they were responsible for\n"
            "   - **Action**: SPECIFIC technical actions — name the tools, the architecture "
            "decisions, the code, the infrastructure. This is where most detail should be.\n"
            "   - **Result**: Measurable outcomes (revenue, performance, adoption)\n\n"
            "3. **Questions to Ask the Interviewer**: 3-4 thoughtful questions that "
            "demonstrate understanding of the role and company.\n\n"
            "4. **2-Minute Pitch**: A concise self-introduction optimized for this "
            "specific role that leads with technical depth.\n\n"
            "Every answer should follow the '30-60 rule': answer the question specifically "
            "in 30 seconds, give one concrete technical example in 60 seconds, then stop."
        )),
        HumanMessage(content=(
            f"Candidate's Background:\n{context}\n\n"
            f"Job Description{company_context}:\n{job_description}"
        )),
    ]

    response = llm.invoke(messages)
    return response.content


def draft_outreach_message(
    contact_name: str,
    contact_company: str,
    contact_role: str = "",
    relationship: str = "former colleague",
    purpose: str = "reconnect and explore opportunities",
) -> str:
    """
    Draft a personalized LinkedIn outreach message.
    """
    llm = get_llm()

    # Get candidate background for context
    experience_results = search(query="experience background accomplishments", n_results=5)

    context = "\n\n".join(
        f"{r['content']}" for r in experience_results
    )

    messages = [
        SystemMessage(content=(
            "You are an expert networking coach. Draft a LinkedIn message that is:\n"
            "- Warm but professional\n"
            "- Short (under 150 words)\n"
            "- Specific to the recipient's company and role\n"
            "- NOT desperate or needy — positioned as a successful independent consultant\n"
            "- Includes a clear but soft ask\n\n"
            "The sender is an Enterprise AI Solution Architect who recently left HPE "
            "to launch an independent AI consulting practice. They hold US Patent #9119056 "
            "for AI knowledge management (a precursor to modern copilot technology). "
            "They are exploring both consulting engagements and senior full-time roles.\n\n"
            "Generate 2 versions:\n"
            "**Version A**: Focused on reconnecting and exploring opportunities\n"
            "**Version B**: More direct about specific interest in their company"
        )),
        HumanMessage(content=(
            f"Recipient: {contact_name}\n"
            f"Company: {contact_company}\n"
            f"Role: {contact_role}\n"
            f"Relationship: {relationship}\n"
            f"Purpose: {purpose}\n\n"
            f"Sender's Background:\n{context}"
        )),
    ]

    response = llm.invoke(messages)
    return response.content


def analyze_company(company_name: str, job_description: str = "") -> str:
    """
    Generate a company research brief for interview preparation.
    """
    llm = get_llm()

    messages = [
        SystemMessage(content=(
            "You are a career research analyst. Based on your knowledge of the company, "
            "provide a concise research brief that a job candidate can use to prepare "
            "for an interview. Include:\n\n"
            "1. **Company Overview**: What they do, market position, recent news\n"
            "2. **AI/Tech Strategy**: Their known AI initiatives, products, and investments\n"
            "3. **Culture & Values**: What they look for in employees\n"
            "4. **Recent News**: Any major announcements, product launches, or changes\n"
            "5. **Interview Insights**: Common interview patterns, what they value\n"
            "6. **How to Position Yourself**: Specific ways to connect your enterprise AI "
            "architecture experience to their needs\n\n"
            "Be factual and actionable. Note if any information may be outdated."
        )),
        HumanMessage(content=(
            f"Company: {company_name}\n"
            f"{'Job Description: ' + job_description if job_description else ''}"
        )),
    ]

    response = llm.invoke(messages)
    return response.content