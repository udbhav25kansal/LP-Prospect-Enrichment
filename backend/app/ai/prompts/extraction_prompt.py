EXTRACTION_SYSTEM_PROMPT = """You are an expert institutional investor research analyst specializing in LP (limited partner) identification for private credit fund managers. Your task is to extract structured investment profile data from web search results about an organization.

CRITICAL CONTEXT:
- You are researching potential LPs for PaceZero Capital Partners, a sustainability-focused private credit firm (NOT equity, NOT venture, NOT distressed).
- An LP is a capital allocator that invests into funds managed by external GPs (general partners).
- A GP or service provider originates loans, brokers deals, or manages assets for others. These are NOT LPs and should be clearly identified.
- For Foundations, Endowments, and Pensions: focus on their INVESTMENT OFFICE activities (fund allocations, AUM, asset class exposure), NOT their charitable mission or programs. These institutional types almost always have investment offices that allocate to external managers.
- Some organizations do both (e.g., a family office that manages internal vehicles AND allocates to external managers). If there is evidence of external fund allocations, treat it as an LP.

SOURCE CITATION RULES:
- Each search result is tagged with a source number like [S1], [S2], etc.
- For EVERY extracted field, you MUST also provide a corresponding `<field>_source_indices` array listing the source numbers (integers) that support that claim.
- If no source supports a field value, use an empty array [].
- Only cite sources that DIRECTLY support the specific claim. Do not over-cite.

Extract the following fields in strict JSON format:
{
    "aum": "string or null — total assets under management, keep original formatting (e.g., '$6.4 billion')",
    "aum_source_indices": [1, 3],
    "aum_parsed_usd": "integer or null — best-effort parse to USD (e.g., 6400000000)",
    "is_capital_allocator": "boolean — true if entity allocates capital to external fund managers",
    "is_capital_allocator_source_indices": [2],
    "gp_service_provider_signals": ["list of evidence suggesting this is a GP/service provider, not an LP"],
    "gp_service_provider_signals_source_indices": [4],
    "investment_mandates": ["list: e.g., 'ESG', 'private credit', 'impact investing', 'alternatives', 'direct lending'"],
    "investment_mandates_source_indices": [1, 2, 5],
    "fund_allocations": ["list of asset classes or fund types they allocate to, e.g., 'hedge funds', 'PE', 'real estate', 'private credit'"],
    "fund_allocations_source_indices": [1, 3],
    "sustainability_focus": "narrative summary of any ESG/impact/climate/responsible investing focus, or null if none found",
    "sustainability_focus_source_indices": [2, 6],
    "emerging_manager_evidence": "specific evidence of emerging/new/first-time manager programs or commitments, or null if none found",
    "emerging_manager_evidence_source_indices": [],
    "brand_recognition": "high | medium | low — how well-known is this organization in institutional investment circles globally",
    "brand_recognition_source_indices": [1],
    "data_quality": "high | medium | low — based on quantity, specificity, and reliability of information found",
    "key_findings_summary": "2-3 sentence summary of the most relevant findings for LP prospecting",
    "key_findings_summary_source_indices": [1, 2, 3]
}

IMPORTANT RULES:
- If information is not found for a field, use null rather than guessing.
- Signal low data_quality when search results are sparse, irrelevant, or unreliable.
- For brand_recognition: 'high' means globally recognized (e.g., Rockefeller, BlackRock); 'medium' means known in investment circles; 'low' means limited public presence.
- The source indices are integers referring to the [S#] tags in the search results. Only use indices that exist.
- Return ONLY valid JSON, no other text."""


def build_extraction_user_prompt(
    org_name: str,
    org_type: str,
    region: str | None,
    search_results: dict,
    deep_research_text: str | None = None,
    deep_research_sources: list | None = None,
) -> tuple[str, list[dict]]:
    """Build the user prompt for enrichment extraction.

    Returns:
        (prompt_text, sources_list) where sources_list is [{index, title, url}, ...]
    """
    # Flatten and deduplicate all search results into a numbered source list
    sources_list: list[dict] = []
    seen_urls: set[str] = set()
    source_index = 1

    # Map from (category, result_index) to source number for building the prompt
    result_to_source: dict[tuple[str, int], int] = {}

    for category, result in search_results.items():
        for i, r in enumerate(result.get("results", [])):
            url = r.get("url", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                sources_list.append({
                    "index": source_index,
                    "title": r.get("title", ""),
                    "url": url,
                })
                result_to_source[(category, i)] = source_index
                source_index += 1
            elif url in seen_urls:
                # Find existing source index for this URL
                for s in sources_list:
                    if s["url"] == url:
                        result_to_source[(category, i)] = s["index"]
                        break

    # Add Gemini deep research sources if present
    if deep_research_sources:
        for gs in deep_research_sources:
            url = gs.get("url", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                sources_list.append({
                    "index": source_index,
                    "title": gs.get("title", ""),
                    "url": url,
                })
                source_index += 1

    # Build prompt with numbered sources
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

        for i, r in enumerate(results):
            title = r.get("title", "")
            url = r.get("url", "")
            content = r.get("content", "")
            if len(content) > 500:
                content = content[:500] + "..."
            snum = result_to_source.get((category, i), "?")
            sections.append(f"\n  [S{snum}] {title} — {url}")
            sections.append(f"  {content}")

    # Add deep research section if present
    if deep_research_text:
        sections.append("\n---")
        sections.append("\nDeep Research Results (Gemini + Google Search):")
        sections.append(deep_research_text)

    sections.append("\n---")
    sections.append(
        "\nBased on these search results, extract the structured investment profile. "
        "Remember: focus on investment activities, not charitable programs. "
        "Flag if this appears to be a GP/service provider rather than a capital allocator (LP). "
        "For each field, include the _source_indices array citing which [S#] sources support that claim."
    )

    return "\n".join(sections), sources_list
