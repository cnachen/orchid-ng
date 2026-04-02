You are refining a research idea after a pairwise review.

Research Topic:
{topic_block}

Current Best Idea:
{winner_block}

Nearby Alternative:
{peer_block}

Evidence Notes:
{evidence_block}

Alignment Repair Hints:
{gap_block}

Required Refinement Actions:
{actions_block}

Style Contract:
- Keep the title paper-like and mechanism-specific.
- Keep the task summary in the 130-150 word range.
- Keep exactly 4 research questions, exactly 4 research objectives, and exactly 5 contributions.
- Keep exactly 5 modules with concrete structure, input, and output. At least 2 modules should expose a formula or explicit operation.
- Keep the framework in the 120-135 word range with 5 ordered stages and a believable evaluation note.
- Keep exactly 3 required conditions, exactly 3 open risks, and exactly 3 supporting evidence ids with realistic compute and fairness constraints.
- If the current best idea overlaps with the nearby alternative, switch to a different mechanism family instead of renaming the same one.

Archetype directions:
- Entropy-calibration style cards work when the signal is stable across perturbations and the pipeline isolates measurement, consistency scoring, and calibration.
- Provenance-clustering style cards work when the pipeline first builds a human reference space, then maps an input into that space, then adjusts the detection rule with an explanation.

Rewrite the current best idea into a stronger research idea card.

The refined idea must:
- keep the core topic but become more specific and technically grounded
- improve any listed alignment repair hints
- include a sharper central mechanism instead of a renamed variant
- stay distinct from the nearby alternative in signal family or intervention
- preserve feasibility under the stated constraints

Return one improved idea candidate as JSON only.
