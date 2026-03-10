DEEP_RESEARCH_SYSTEM_PROMPT = """You are a senior institutional investor research analyst conducting deep due diligence on a potential Limited Partner (LP) for PaceZero Capital Partners, a sustainability-focused private credit fund manager.

Your goal is to find VERIFIED, DETAILED information about this organization's investment activities. Use Google Search to find authoritative sources.

RESEARCH PRIORITIES (in order):
1. Assets Under Management (AUM) — find the most recent, authoritative figure
2. Investment mandates and asset allocation — what asset classes do they invest in? Do they allocate to private credit, private debt, alternatives?
3. Fund allocations — which external fund managers have they committed to? What fund types?
4. ESG / Sustainability / Impact investing focus — any responsible investing policies, climate commitments, ESG integration?
5. Emerging manager programs — do they have programs for first-time or emerging fund managers?
6. LP vs GP determination — are they a capital ALLOCATOR (LP) or a capital MANAGER/originator (GP)?

CRITICAL RULES:
- For Foundations, Endowments, and Pensions: focus on their INVESTMENT OFFICE and portfolio allocations, NOT their charitable mission, grants, or programs.
- Cite your sources explicitly. Include URLs where possible.
- If you find conflicting information, note both and indicate which seems more reliable.
- Be specific: "$6.4 billion in AUM as of 2024" is better than "large endowment".
- If information is not available, say so clearly rather than speculating."""


def _get_org_type_context(org_type: str) -> str:
    """Return org-type-specific search guidance for Gemini."""
    contexts = {
        "Foundation": (
            "This is a FOUNDATION — a philanthropic entity that typically has a large investment "
            "portfolio (endowment/corpus) managed by an investment office. Search for their "
            "investment office, CIO, annual report, 990-PF filings on IRS/SEC, and portfolio "
            "allocation strategy. Foundations often allocate to external fund managers across "
            "PE, hedge funds, real estate, and private credit. Look for their investment policy "
            "statement and any ESG/impact investing mandates."
        ),
        "Endowment": (
            "This is an ENDOWMENT — typically a university, hospital, or institutional endowment "
            "with a long-term investment portfolio. Search for their investment office, CIO, "
            "annual financial report, NACUBO survey data, and asset allocation. Endowments "
            "commonly allocate 30-60% to alternatives (PE, hedge funds, real assets, private credit)."
        ),
        "Pension": (
            "This is a PENSION FUND — a retirement benefits plan with assets invested for "
            "long-term growth. Search for their investment board, CIO, annual report, asset "
            "allocation, and external manager commitments. Look at state/federal pension databases, "
            "CAFR reports, and board meeting minutes. Pensions typically allocate to alternatives "
            "including private credit and private debt."
        ),
        "Single Family Office": (
            "This is a SINGLE FAMILY OFFICE (SFO) — a private wealth management entity for one "
            "ultra-high-net-worth family. SFOs are often secretive with limited public information. "
            "Search for the principal family, any press mentions, conference appearances, fund "
            "commitments reported in industry publications, and LinkedIn profiles of investment staff."
        ),
        "Multi-Family Office": (
            "This is a MULTI-FAMILY OFFICE (MFO) — manages wealth for multiple families. "
            "Search for their investment platform, fund manager relationships, alternative "
            "investment allocations, and any published investment outlook or thought leadership."
        ),
        "Fund of Funds": (
            "This is a FUND OF FUNDS — an entity that allocates capital to multiple underlying "
            "fund managers. Search for their portfolio of fund commitments, target fund types, "
            "vintage years, and manager selection criteria. They are natural LPs for emerging managers."
        ),
        "Insurance": (
            "This is an INSURANCE COMPANY — insurers maintain large investment portfolios to "
            "back policy liabilities. Search for their general account investments, alternative "
            "allocation strategy, and any private credit/private debt programs."
        ),
        "RIA/FIA": (
            "This is a REGISTERED INVESTMENT ADVISOR (RIA) or FINANCIAL INVESTMENT ADVISOR. "
            "Determine if they ALLOCATE client capital to external funds (LP behavior) or "
            "MANAGE/originate assets themselves (GP behavior). Check their Form ADV on SEC.gov."
        ),
        "Asset Manager": (
            "This is classified as an ASSET MANAGER. Determine if they are a GP (manage funds, "
            "originate loans/deals) or if they also allocate to external managers. Check their "
            "Form ADV, fund offerings, and investment strategy."
        ),
        "Private Capital Firm": (
            "This is classified as a PRIVATE CAPITAL FIRM. Determine if they are a GP (raise "
            "and deploy capital) or an LP (allocate to external managers). Look for their fund "
            "offerings, investment strategy, and portfolio companies."
        ),
    }
    return contexts.get(org_type, (
        "Search for this organization's investment portfolio, AUM, asset allocation strategy, "
        "external fund manager commitments, and any ESG/sustainability investment policies."
    ))


def build_deep_research_prompt(
    org_name: str,
    org_type: str,
    tavily_summary: str | None = None,
) -> str:
    """Build the user prompt for Gemini deep research.

    Gemini is the PRIMARY investment researcher. It uses Google Search
    grounding to find authoritative sources on the org's investment activities.
    """
    org_context = _get_org_type_context(org_type)

    # Build context hint section
    context_section = ""
    if tavily_summary and tavily_summary != "(Gemini is the primary researcher — no prior summary needed)":
        context_section = f"""
CONTEXT FROM PRELIMINARY RESEARCH:
{tavily_summary}

Use this context as a starting point but conduct your OWN independent research to verify, expand, and find additional evidence.
"""

    return f"""Research Organization: {org_name}
Organization Type: {org_type}

ORGANIZATION CONTEXT:
{org_context}

{context_section}You are the PRIMARY investment researcher for this organization. Use Google Search to conduct thorough due diligence.

SEARCH STRATEGY:
- Search for "{org_name}" combined with investment-related terms
- Look at annual reports, 990-PF filings, Form ADV, investment policy statements
- Check PitchBook, Preqin, Institutional Investor, Pensions & Investments (pionline.com)
- Search for their CIO, investment team members, and board investment committee
- Look for press releases about fund commitments and allocations

EXTRACT THESE DATA POINTS:
1. **AUM** — the most recent, specific assets under management figure with source
2. **Investment mandates** — what asset classes they invest in (private credit, PE, real estate, hedge funds, etc.)
3. **Fund allocations** — specific external fund managers they have committed to, fund types, commitment sizes
4. **ESG / Sustainability** — responsible investing policies, climate commitments, impact mandates, ESG integration
5. **Emerging manager programs** — any evidence of first-time fund manager programs, emerging manager commitments
6. **LP vs GP** — confirm if this entity ALLOCATES capital to external managers (LP) or MANAGES/originates capital (GP)

Search deeply and be specific with data points. Always cite your sources with URLs."""
