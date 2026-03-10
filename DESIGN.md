# Design Decisions & Tradeoffs

## Architecture Choice: Multi-Model Pipeline

**Decision**: Use Tavily for web search + Claude for both extraction and scoring (two separate Claude calls per org).

**Why**: Separating extraction from scoring produces more accurate results. The extraction call normalizes raw web data into structured fields (AUM, mandates, allocator status). The scoring call then operates on clean structured data with calibration anchors embedded in the system prompt. This separation enables re-scoring without re-searching and makes debugging straightforward — you can see exactly what data the scorer received.

**Tradeoff**: ~50% more Claude cost ($0.025 vs $0.016 per org) but significantly better accuracy. At $4.70 total for 94 orgs, the accuracy gain far outweighs the cost.

## Scoring Calibration

The most critical design element is the calibration-anchored scoring prompt. The 4 anchor organizations (Rockefeller Foundation, PBUCC, Inherent Group, Meridian Capital Group) span the full spectrum: from an ideal LP (sector=9, halo=9) to a non-LP service provider (sector=1). These anchors are embedded verbatim in the Claude system prompt with expected scores and reasoning, so every scoring call is calibrated against known reference points. A post-scoring validation step checks for calibration drift (>2 point deviation from expected).

## Org-Type-Aware Search Queries

Different org types require different search strategies. Foundations/Endowments/Pensions are searched with queries steering toward "investment portfolio allocations" rather than "charitable mission", because their public presence emphasizes programs but their investment offices are what matter for LP prospecting. Family offices get "fund allocations alternative investments" queries. RIA/FIAs get queries that intentionally surface "origination OR lending" alongside "fund allocations" to help the extraction step identify GP vs LP signals.

## Org-Level Deduplication + Alias Resolution

The system deduplicates at the organization level: BBR Partners with 2 contacts gets one enrichment call, not two. The PBUCC case (appears as both "PBUCC" and "Pension Boards United Church of Christ" with different org types) is handled via an alias table that maps abbreviations to canonical names. For multi-contact orgs, the max relationship depth across contacts becomes the org's D2 score — the deepest relationship is what matters for outreach.

## What I'd Improve With More Time

1. **Fuzzy dedup**: Use Claude to compare potentially similar org names rather than exact matching + manual aliases. Would catch more subtle duplicates at scale.
2. **Incremental enrichment**: Cache enrichment results with TTL and skip recently-enriched orgs on subsequent runs.
3. **SSE progress**: Replace polling with Server-Sent Events for real-time pipeline progress.
4. **Score override UI**: Let fundraising team manually override individual dimension scores with notes.
5. **Export**: CSV/PDF export of scored pipeline for offline use.
6. **Statistical outlier detection**: Z-score analysis on composite scores within each org type to catch anomalies the rule-based validators miss.
7. **Prompt A/B testing**: Run scoring with multiple prompt variants and compare outputs to iterate on accuracy.
