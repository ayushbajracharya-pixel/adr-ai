"""
A single dictionary mapping a canonical heading to a list of its synonyms.

Headings are the distinct sections common in most of the adrs.
This is used to create chunks based on heading so that the meaningful information are contained in each chunk.
"""

canonical_headings_map = {
    "Context": [
        "Context",
        "Background",
        "Problem Statement",
        "Current Situation",
    ],
    "Considered Options": [
        "Considered Options",
        "Alternatives",
        "Options",
        "Proposals",
        "Evaluated Solutions",
    ],
    "Decision": [
        "Decision",
        "Chosen Option",
        "Selected Alternative",
        "The Decision",
    ],
    "Rationale": [
        "Rationale",
        "Reasoning",
        "Justification",
        "Explanation",
        "Decision Drivers",
    ],
    "Consequences": [
        "Consequences",
        "Implications",
        "Effects",
        "Outcomes",
        "Results",
        "Pros & Cons",
        "Trade-offs",
    ],
}
