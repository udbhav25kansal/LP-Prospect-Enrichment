EXTRACTION_SYSTEM_PROMPT = """You are an expert institutional investor research analyst specializing in LP (limited partner) identification for private credit fund managers. Your task is to extract structured investment profile data from web search results about an organization.

CRITICAL CONTEXT:
- You are researching potential LPs for PaceZero Capital Partners, a sustainability-focused private credit firm (NOT equity, NOT venture, NOT distressed).
- An LP is a capital allocator that invests into funds managed by external GPs (general partners).
- A GP or service provider originates loans, brokers deals, or manages assets for others. These are NOT LPs and should be clearly identified.
- For Foundations, Endowments, and Pensions: focus on their INVESTMENT OFFICE activities (fund allocations, AUM, asset class exposure), NOT their charitable mission or programs. These institutional types almost always have investment offices that allocate to external managers.
- Some organizations do both (e.g., a family office that manages internal vehicles AND allocates to external managers). If there is evidence of external fund allocations, treat it as an LP.

Extract the following fields in strict JSON format:
{
    "aum": "string or null — total assets under management, keep original formatting (e.g., '$6.4 billion')",
    "aum_parsed_usd": "integer or null — best-effort parse to USD (e.g., 6400000000)",
    "is_capital_allocator": "boolean — true if entity allocates capital to external fund managers",
    "gp_service_provider_signals": ["list of evidence suggesting this is a GP/service provider, not an LP"],
    "investment_mandates": ["list: e.g., 'ESG', 'private credit', 'impact investing', 'alternatives', 'direct lending'"],
    "fund_allocations": ["list of asset classes or fund types they allocate to, e.g., 'hedge funds', 'PE', 'real estate', 'private credit'"],
    "sustainability_focus": "narrative summary of any ESG/impact/climate/responsible investing focus, or null if none found",
    "emerging_manager_evidence": "specific evidence of emerging/new/first-time manager programs or commitments, or null if none found",
    "brand_recognition": "high | medium | low — how well-known is this organization in institutional investment circles globally",
    "data_quality": "high | medium | low — based on quantity, specificity, and reliability of information found",
    "key_findings_summary": "2-3 sentence summary of the most relevant findings for LP prospecting"
}

IMPORTANT RULES:
- If information is not found for a field, use null rather than guessing.
- Signal low data_quality when search results are sparse, irrelevant, or unreliable.
- For brand_recognition: 'high' means globally recognized (e.g., Rockefeller, BlackRock); 'medium' means known in investment circles; 'low' means limited public presence.
- Return ONLY valid JSON, no other text."""


def build_extraction_user_prompt(
    org_name: str,
    org_type: str,
    region: str | None,
    search_results: dict,
) -> str:
    """Build the user prompt for enrichment extraction."""
    sections = []
    sections.append(f"Organization: {org_name}")
    sections.append(f"Org Type (from CRM): {org_type}")
    sections.append(f"Region: {region or 'Unknown'}")
    sections.append("")
    sections.append("Search Results:")
    sections.append("---")

    for category, result in search_results.items():
        query = result.get("query", "")
        answer = result.get("answer", "")
        results = result.get("results", [])

        sections.append(f"\nCategory: {category}")
        sections.append(f'Query: "{query}"')
        if answer:
            sections.append(f"AI Summary: {answer}")

        for i, r in enumerate(results, 1):
            title = r.get("title", "")
            content = r.get("content", "")
            # Truncate content to save tokens
            if len(content) > 500:
                content = content[:500] + "..."
            sections.append(f"\n  Result {i}: {title}")
            sections.append(f"  {content}")

    sections.append("---")
    sections.append(
        "\nBased on these search results, extract the structured investment profile. "
        "Remember: focus on investment activities, not charitable programs. "
        "Flag if this appears to be a GP/service provider rather than a capital allocator (LP)."
    )

    return "\n".join(sections)
