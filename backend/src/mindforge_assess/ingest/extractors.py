"""The handbook extractors: one per region of the MindForge handbook.

Each entry pairs a strict tool schema with an instruction and the pages it reads. Broad
regions are split into several `Pass` objects because `strict: true` compiles the schema
into a decoding grammar and the API rejects one that grows too large.
"""

from __future__ import annotations

from typing import Any

from . import schema_util as s
from .engine import (
    DIMENSIONS,
    RATINGS,
    Extractor,
    Pass,
    _check_sources,
    source_schema,
)
from .page_map import PageMap

# ------------------------------------------------------------ dimensions_taxonomy (B)


def _dimensions_tool() -> dict[str, Any]:
    risk = s.obj(
        {
            "name": s.string("The risk's name exactly as printed in the taxonomy."),
            "description": s.string("The risk's description as printed, lightly condensed."),
            "ai_specific_elements": s.nullable_string(
                "Text from the 'AI-specific elements' column for this risk, or null if "
                "the table has no such column or the cell is empty."
            ),
            "secondary_dimensions": s.arr(
                s.string("A dimension named in the 'Secondary Dimensions Impacted' cell."),
                description="Empty array if the cell is blank or the column is absent.",
            ),
            "lifecycle_stages": s.arr(
                s.string("A lifecycle stage as printed in its cell, e.g. '2' or '3'."),
                description="Empty array if the cell is blank or the column is absent.",
            ),
            "is_abs_top_10": {
                "type": ["boolean", "null"],
                "description": (
                    "True if this page marks the risk as one of the ABS 'top 10' AI risks, "
                    "false if it is explicitly not, null if the pages do not say."
                ),
            },
            "source": source_schema(),
        }
    )
    dimension = s.obj(
        {
            "dimension": s.enum(DIMENSIONS, "Which of the seven risk dimensions this is."),
            "printed_name": s.string("The dimension's name exactly as printed in Appendix B."),
            "definition": s.nullable_string(
                "The dimension's definition as printed, or null if none is given."
            ),
            "risks": s.arr(risk, description="Every named risk listed under this dimension."),
            "source": source_schema(),
        }
    )
    return s.tool(
        "record_risk_taxonomy",
        "Record the seven-dimension AI risk taxonomy from Appendix B.",
        s.obj(
            {
                "dimensions": s.arr(dimension, description="All seven dimensions, in order."),
                "table_columns": s.arr(
                    s.string("A column header as printed."),
                    description="The column headers of the taxonomy table, in order.",
                ),
                "abs_top_10_risks": s.arr(
                    s.string("Name of a risk identified on these pages as an ABS top-10 risk."),
                    description="Risks these pages mark as ABS 'top 10'. Empty if not marked.",
                ),
                "dimension_renaming": s.arr(
                    s.obj(
                        {
                            "current_title": s.string("The dimension's current title."),
                            "former_title": s.nullable_string(
                                "Its earlier (Phase 1) title, or null if unchanged."
                            ),
                            "source": source_schema(),
                        }
                    ),
                    description=(
                        "The table mapping current dimension titles to their former ones. "
                        "Empty array if these pages carry no such table."
                    ),
                ),
                "risk_changes": s.arr(
                    s.obj(
                        {
                            "risk_name": s.string("The risk that was changed or added."),
                            "change": s.string("The nature of the change, as printed."),
                            "source": source_schema(),
                        }
                    ),
                    description=(
                        "The table of risks revised or added in a later phase. "
                        "Empty array if absent from these pages."
                    ),
                ),
                "lifecycle_stage_legend": s.arr(
                    s.obj(
                        {
                            "number": s.integer("The stage's number as printed."),
                            "name": s.string("The stage's name as printed."),
                        }
                    ),
                    description=(
                        "The numbered lifecycle stages, needed to read the numeric "
                        "'Lifecycle Stages Impacted' column. Empty array if absent."
                    ),
                ),
                "total_risk_rows_counted": s.integer(
                    "The total number of risk rows you counted across the whole table. "
                    "Count them on the page; this is cross-checked against your output."
                ),
                "unreadable_items": s.arr(
                    s.string("Describe anything on these pages you could not read."),
                    description="Empty array if everything was legible.",
                ),
            }
        ),
    )


DIMENSIONS_INSTRUCTION = """\
These pages are Appendix B, the MindForge AI Risk Taxonomy.

Transcribe the taxonomy in full. For EVERY dimension, list EVERY named risk that appears
under it -- do not summarise, sample or skip rows, including rows that continue onto a
following page. Work through the table row by row.

Map each dimension onto one of the seven enum values, and also record its name exactly as
printed in `printed_name` (the printed wording may differ slightly from the enum).

`total_risk_rows_counted` must be your own count of risk rows on the page. Count first,
then transcribe, so that a mismatch reveals a dropped row.

For `source.page`, read the PRINTED page number from the page footer. For `source.quote`,
copy 5-25 words verbatim from that page.

Capture EVERY column of the table for every row, including 'Secondary Dimensions
Impacted' and 'Lifecycle Stages Impacted'. Record the lifecycle stage cells exactly as
printed (they may be bare numbers) and use `lifecycle_stage_legend` for the table that
says what those numbers mean.

These pages also carry smaller supporting tables before the main taxonomy: one mapping
each dimension's current title to its former title, and one listing risks revised or
added in a later phase. Transcribe both. Return an empty array for any that is not on
these pages.

If a column such as 'AI-specific elements' does not exist, return null for it rather than
inventing content. If the pages never mark which risks are ABS 'top 10', return null for
`is_abs_top_10` and an empty `abs_top_10_risks` array."""


# ----------------------------------------------------------- materiality_factors (2.4)


def _materiality_factors_tool() -> dict[str, Any]:
    factor = s.obj(
        {
            "factor": s.string("The factor's name as printed, e.g. 'Impact on stakeholders'."),
            "description": s.string("What the handbook says this factor covers."),
            "sub_criteria": s.arr(
                s.string("A sub-criterion named under this factor."),
                description="Sub-criteria named under the factor, e.g. severity, "
                "probability, number of stakeholders affected. Empty if none.",
            ),
            "low_guidance": s.nullable_string("Guidance for rating this factor low, else null."),
            "medium_guidance": s.nullable_string("Guidance for a medium rating, else null."),
            "high_guidance": s.nullable_string("Guidance for a high rating, else null."),
            "source": source_schema(),
        }
    )
    tier = s.obj(
        {
            "tier": s.enum(RATINGS, "The materiality tier."),
            "printed_name": s.string("The tier's name as printed, e.g. 'High materiality'."),
            "definition": s.string("What the handbook says qualifies for this tier."),
            "governance_implications": s.nullable_string(
                "What controls or review depth this tier triggers, or null."
            ),
            "source": source_schema(),
        }
    )
    return s.tool(
        "record_materiality_factors",
        "Record Section 2.4's inherent-risk factors and materiality tiering.",
        s.obj(
            {
                "inherent_risk_factors": s.arr(
                    factor, description="Every inherent-risk materiality factor named in 2.4."
                ),
                "tiers": s.arr(tier, description="The low/medium/high tiering guidance."),
                "tiering_method": s.nullable_string(
                    "How the handbook says factor ratings combine into an overall tier "
                    "(e.g. weighted, highest-wins, judgement), or null if unstated."
                ),
                "residual_risk_logic": s.nullable_string(
                    "How residual materiality is derived from inherent materiality and "
                    "control evaluation, in the handbook's own terms, or null."
                ),
                "agentic_or_genai_factors": s.arr(
                    s.string("A factor 2.4 singles out for Gen AI or agentic use cases."),
                    description="Empty array if Section 2.4 names none.",
                ),
                "total_factors_counted": s.integer(
                    "Your own count of distinct inherent-risk factors on these pages."
                ),
                "unreadable_items": s.arr(
                    s.string("Anything on these pages you could not read."),
                    description="Empty array if everything was legible.",
                ),
            }
        ),
    )


def _materiality_matrix_tool() -> dict[str, Any]:
    matrix_cell = s.obj(
        {
            "inherent_tier": s.enum(RATINGS, "The inherent risk materiality tier (input)."),
            "evaluation_result": s.string(
                "The evaluation/control-effectiveness outcome as printed on the figure, "
                "e.g. 'Min.', 'Exceeds Min.', 'Best Practice'."
            ),
            "residual_label": s.string(
                "The cell's text EXACTLY as printed, e.g. 'Low Risk' or "
                "'Medium Risk/High Risk'. Do not normalise or pick one of two values."
            ),
            "residual_tiers": s.arr(
                s.enum(RATINGS, "A tier named by the printed label."),
                description=(
                    "Every tier the printed label names, in printed order. A cell printed "
                    "'Medium Risk/High Risk' yields ['medium', 'high']; 'Low Risk' yields "
                    "['low']. Never collapse a dual-valued cell to one tier."
                ),
            ),
            "note": s.nullable_string("Any caveat printed in or beside this cell, else null."),
        }
    )
    figure = s.obj(
        {
            "label": s.string("The figure label, e.g. 'Figure 2.4.3'."),
            "caption": s.string("The figure caption exactly as printed."),
            "read_successfully": {
                "type": "boolean",
                "description": "False if any part of the figure was illegible.",
            },
            "axis_inherent_values": s.arr(
                s.string("A value on the inherent-risk axis, as printed."),
                description="The inherent-risk axis categories, in printed order.",
            ),
            "axis_evaluation_values": s.arr(
                s.string("A value on the evaluation-result axis, as printed."),
                description="The evaluation-result axis categories, in printed order.",
            ),
            "cells": s.arr(
                matrix_cell,
                description="One entry for EVERY cell of the matrix. Do not omit cells.",
            ),
            "always_high_note": s.nullable_string(
                "The note about use cases that may always remain high materiality "
                "regardless of controls, verbatim, or null if no such note appears."
            ),
            "always_high_note_applies_to": s.nullable_string(
                "Which cell or column that note is printed against, e.g. "
                "'high inherent / best practice', or null if it is not cell-specific."
            ),
            "failure_to_meet_minimum_note": s.nullable_string(
                "Any note on the figure about use cases that fail to meet the minimum "
                "threshold, verbatim, or null."
            ),
            "source": source_schema(),
        }
    )
    return s.tool(
        "record_materiality_matrix",
        "Record Figure 2.4.3's inherent-to-residual risk materiality matrix.",
        s.obj(
            {
                "figure_2_4_3": figure,
                "unreadable_items": s.arr(
                    s.string("Anything on these pages you could not read."),
                    description="Empty array if everything was legible.",
                ),
            }
        ),
    )


MATERIALITY_FACTORS_INSTRUCTION = """\
These pages are Section 2.4, 'Enhance Use Case-Level AI Risk Management'.

List EVERY factor the section names for assessing inherent risk materiality -- work
through the prose and any table or figure that enumerates them, and do not stop at the
first list you find. Capture each factor's description and any low/medium/high guidance.
If the section gives no explicit guidance for a rating level, return null for it rather
than paraphrasing the description.

Also capture the materiality tiers themselves, how the handbook says factor ratings
combine into an overall tier, and how residual materiality relates to inherent
materiality. Where the section singles out Gen AI or agentic use cases for extra
weighting, record that too.

For `source.page`, read the PRINTED page number from the page footer. For `source.quote`,
copy 5-25 words verbatim from that page. Return null rather than guessing."""


MATERIALITY_MATRIX_INSTRUCTION = """\
These pages are Section 2.4. Find Figure 2.4.3, 'Illustrative Approach to Residual Risk
Materiality Assessment Based on Inherent Risk Materiality'.

READ THE FIGURE ITSELF, not the surrounding prose. Encode it as a complete matrix: for
every combination of inherent-risk tier and evaluation result shown, record what the
figure puts in that cell. Include EVERY cell -- 3 inherent tiers by 3 evaluation results
means 9 cells. Use the axis labels exactly as printed.

Transcribe each cell's text EXACTLY as printed into `residual_label`, then list every
tier that label names in `residual_tiers`. Some cells name two tiers (for example
'Medium Risk/High Risk'); such a cell must yield two entries, never one. Collapsing a
dual-valued cell to a single tier is the specific error this pass exists to prevent.

Capture the note about use cases that may always have high residual risk, verbatim, and
say which cell or column it is printed against. Capture any note about use cases that
fail to meet the minimum threshold.

If any part of the figure is illegible, set `read_successfully` to false and say what you
could not read. Do not reconstruct a cell you cannot see.

For `source.page`, read the PRINTED page number from the figure's page footer."""


# ------------------------------------------------------------------ definitions (1.1)

OVERSIGHT_MODES = ["human_in_the_loop", "human_over_the_loop", "human_out_of_the_loop"]


def _definitions_tool() -> dict[str, Any]:
    example = s.obj(
        {
            "example": s.string("The example as printed."),
            "why": s.nullable_string("Why it falls this side of the line, else null."),
            "source": source_schema(),
        }
    )
    term = s.obj(
        {
            "term": s.string("The term as printed, e.g. 'AI model', 'AI system', 'AI use case'."),
            "definition": s.string("Its definition as printed."),
            "source": source_schema(),
        }
    )
    risk = s.obj(
        {
            "risk": s.string("The risk's name as printed."),
            "description": s.nullable_string("Its description, or null if only named."),
            "source": source_schema(),
        }
    )
    return s.tool(
        "record_definitions",
        "Record Section 1.1's definition of AI in scope and its key distinctions.",
        s.obj(
            {
                "ai_definition": s.obj(
                    {
                        "definition": s.string("The handbook's definition of AI, as printed."),
                        "source": source_schema(),
                    }
                ),
                "in_scope_examples": s.arr(
                    example, description="Systems the handbook says ARE in scope."
                ),
                "out_of_scope_examples": s.arr(
                    example,
                    description=(
                        "Systems the handbook says are NOT in scope, e.g. purely "
                        "rule-based or deterministic automation. Empty if none given."
                    ),
                ),
                "terms": s.arr(
                    term,
                    description=(
                        "The model / system / use case distinction and any other terms "
                        "this section defines."
                    ),
                ),
                "abs_top_risks": s.arr(
                    risk,
                    description=(
                        "The ABS 'top 10' AI risks, if these pages list them. "
                        "Empty array if they are not listed here."
                    ),
                ),
                "scope_notes": s.arr(
                    s.string("A note about what the handbook covers or excludes."),
                    description="Empty array if none.",
                ),
                "unreadable_items": s.arr(
                    s.string("Anything on these pages you could not read."),
                    description="Empty array if everything was legible.",
                ),
            }
        ),
    )


DEFINITIONS_INSTRUCTION = """\
These pages are Section 1.1, on the handbook's scope and application.

Capture the handbook's definition of AI for the purposes of this handbook, and the
examples it gives of what IS and what IS NOT in scope. The out-of-scope examples matter
as much as the in-scope ones -- if the handbook says purely rule-based or deterministic
automation falls outside the definition, record that with its example.

Capture the distinction the handbook draws between an AI model, an AI system and an AI
use case, and any other term these pages define.

If these pages list the ABS 'top 10' AI risks, record them; if they do not, return an
empty array rather than importing them from elsewhere.

For `source.page`, read the PRINTED page number from the page footer. For `source.quote`,
copy 5-25 words verbatim. Return null rather than guessing."""


# --------------------------------------------------- oversight_modes (3.1, 3.4, 3.5)


def _oversight_tool() -> dict[str, Any]:
    mode = s.obj(
        {
            "mode": s.enum(OVERSIGHT_MODES, "Which of the three oversight modes this is."),
            "printed_name": s.string("The mode's name exactly as printed."),
            "definition": s.string("Its definition as printed."),
            "when_appropriate": s.nullable_string(
                "When the handbook says this mode is appropriate, or null."
            ),
            "source": source_schema(),
        }
    )
    return s.tool(
        "record_oversight_modes",
        "Record the human oversight modes the handbook defines.",
        s.obj(
            {
                "modes": s.arr(mode, description="All three oversight modes."),
                "selection_guidance": s.nullable_string(
                    "How the handbook says to choose between the modes, or null."
                ),
                "unreadable_items": s.arr(
                    s.string("Anything you could not read."), description="Empty if none."
                ),
            }
        ),
    )


def _monitoring_tool() -> dict[str, Any]:
    sampling = s.obj(
        {
            "name": s.string("The sampling methodology's name as printed."),
            "description": s.string("What it involves, as printed."),
            "when_to_use": s.nullable_string("When it is appropriate, or null."),
            "source": source_schema(),
        }
    )
    control = s.obj(
        {
            "control": s.string("The control's name as printed."),
            "description": s.string("What it does."),
            "source": source_schema(),
        }
    )
    return s.tool(
        "record_monitoring_controls",
        "Record post-deployment monitoring, sampling and interruption controls.",
        s.obj(
            {
                "sampling_methodologies": s.arr(
                    sampling,
                    description=(
                        "Every row of the sampling methodologies table for "
                        "human-over-the-loop oversight. Empty if absent from these pages."
                    ),
                ),
                "sampling_table_label": s.nullable_string(
                    "The table's label as printed, e.g. 'Table 3.5.1', or null."
                ),
                "monitoring_practices": s.arr(
                    control, description="Post-deployment monitoring practices named here."
                ),
                "interruption_controls": s.arr(
                    control,
                    description=(
                        "Kill switches, fallbacks, rollbacks, timeouts or any other control "
                        "for stopping or interrupting a deployed AI system. Empty if none."
                    ),
                ),
                "total_sampling_rows_counted": s.integer(
                    "Your own count of rows in the sampling methodologies table."
                ),
                "unreadable_items": s.arr(
                    s.string("Anything you could not read."), description="Empty if none."
                ),
            }
        ),
    )


OVERSIGHT_INSTRUCTION = """\
These pages cover use case context and design, deployment, and usage/monitoring.

Find the three modes of human oversight the handbook defines and record each one's
printed name and definition. Map each onto the enum: in-the-loop means a human acts on
every decision, over-the-loop means a human supervises and can intervene, out-of-the-loop
means the system acts without human involvement.

For `source.page`, read the PRINTED page number from the page footer. Return null rather
than guessing."""


MONITORING_INSTRUCTION = """\
These pages cover deployment and post-deployment usage, monitoring and change management.

Capture every row of the table of sampling methodologies for human-over-the-loop
oversight -- work through it row by row and count the rows yourself for
`total_sampling_rows_counted`.

Then capture the post-deployment monitoring practices, and separately any control for
stopping or interrupting a deployed system: kill switches, fallbacks, rollbacks,
timeouts, circuit breakers, or escalation to a human. These interruption controls are
what an agentic use case needs, so be thorough.

If the sampling table is not on these pages, return an empty array and a count of 0
rather than inventing rows.

For `source.page`, read the PRINTED page number from the page footer."""


# -------------------------------------------------------------------- metrics (App F)


def _metrics_tool() -> dict[str, Any]:
    metric = s.obj(
        {
            "name": s.string("The metric's name exactly as printed."),
            "definition": s.string("Its definition or description as printed."),
            "formula": s.nullable_string(
                "Its formula as printed, or null if no formula is given."
            ),
            "ai_types": s.arr(
                s.string("An AI type this metric applies to, as printed."),
                description="Empty array if the library does not say.",
            ),
            "dimension": s.nullable_string(
                "The risk dimension this metric serves, if stated, else null."
            ),
            "source": source_schema(),
        }
    )
    return s.tool(
        "record_metrics",
        "Record the library of AI metrics from the appendix.",
        s.obj(
            {
                "metrics": s.arr(metric, description="Every metric in the library."),
                "table_columns": s.arr(
                    s.string("A column header as printed."),
                    description="The library table's column headers, in order.",
                ),
                "total_metrics_counted": s.integer(
                    "Your own count of metric rows on these pages. Count before transcribing."
                ),
                "unreadable_items": s.arr(
                    s.string("Anything you could not read."), description="Empty if none."
                ),
            }
        ),
    )


METRICS_INSTRUCTION = """\
These pages are the Library of AI Metrics.

Transcribe EVERY metric in the library. Work through the table row by row and do not
summarise, sample or skip rows, including rows that continue onto a following page.

Count the rows yourself first and put that number in `total_metrics_counted`, then
transcribe them -- a mismatch between the two reveals a dropped row.

Where the library gives a formula, record it as printed. Where it does not, return null
rather than deriving one.

For `source.page`, read the PRINTED page number from the page footer. For `source.quote`,
copy 5-25 words verbatim from that page."""


# ----------------------------------------------------------------- guardrails (App G)


def _guardrails_tool() -> dict[str, Any]:
    guardrail = s.obj(
        {
            "name": s.string("The guardrail's name exactly as printed."),
            "description": s.string("Its description as printed."),
            "ai_types": s.arr(
                s.string("An AI type this guardrail applies to, as printed."),
                description="Empty array if the library does not say.",
            ),
            "interpretability_type": s.nullable_string(
                "If the library classifies this guardrail as inherent, constrained or "
                "post-hoc interpretability, record which, as printed. Null otherwise."
            ),
            "dimension": s.nullable_string(
                "The risk dimension this guardrail serves, if stated, else null."
            ),
            "source": source_schema(),
        }
    )
    typology = s.obj(
        {
            "name": s.string("The category name as printed, e.g. 'Inherent interpretability'."),
            "definition": s.string("Its definition as printed."),
            "source": source_schema(),
        }
    )
    return s.tool(
        "record_guardrails",
        "Record the library of AI guardrails from the appendix.",
        s.obj(
            {
                "guardrails": s.arr(guardrail, description="Every guardrail in the library."),
                "interpretability_typology": s.arr(
                    typology,
                    description=(
                        "The interpretability categories the appendix defines "
                        "(inherent / constrained / post-hoc). Empty if not defined here."
                    ),
                ),
                "table_columns": s.arr(
                    s.string("A column header as printed."),
                    description="The library table's column headers, in order.",
                ),
                "total_guardrails_counted": s.integer(
                    "Your own count of guardrail rows. Count before transcribing."
                ),
                "unreadable_items": s.arr(
                    s.string("Anything you could not read."), description="Empty if none."
                ),
            }
        ),
    )


GUARDRAILS_INSTRUCTION = """\
These pages are the Library of AI Guardrails.

Transcribe EVERY guardrail in the library, row by row, including rows that continue onto
a following page. Count the rows yourself first for `total_guardrails_counted`.

The appendix distinguishes kinds of interpretability -- inherent, constrained and
post-hoc. Capture those definitions in `interpretability_typology`, and for each
guardrail record which kind it is if the library says so, or null if it does not.

For `source.page`, read the PRINTED page number from the page footer. For `source.quote`,
copy 5-25 words verbatim from that page."""


# ------------------------------------------------------------- considerations (App H)


def _considerations_tool() -> dict[str, Any]:
    practice = s.obj(
        {
            "reference": s.nullable_string(
                "The practice's number or label as printed, e.g. '1.1', or null."
            ),
            "text": s.string("The implementation practice VERBATIM, as printed."),
            "source": source_schema(),
        }
    )
    consideration = s.obj(
        {
            "number": s.integer("The Consideration's number, 1 to 17."),
            "title": s.string("Its title VERBATIM, as printed."),
            "handbook_section": s.nullable_string(
                "The handbook section it belongs to, e.g. '2.4', or null."
            ),
            "implementation_practices": s.arr(
                practice, description="Every implementation practice under it, verbatim."
            ),
            "source": source_schema(),
        }
    )
    return s.tool(
        "record_considerations",
        "Record the Considerations and their Implementation Practices from the checklist.",
        s.obj(
            {
                "considerations": s.arr(
                    consideration,
                    description="Every Consideration on these pages, in printed order.",
                ),
                "total_considerations_counted": s.integer(
                    "Your own count of Considerations on THESE pages."
                ),
                "total_practices_counted": s.integer(
                    "Your own count of implementation practices on THESE pages."
                ),
                "unreadable_items": s.arr(
                    s.string("Anything you could not read."), description="Empty if none."
                ),
            }
        ),
    )


CONSIDERATIONS_INSTRUCTION = """\
These pages are the handbook's checklist of Considerations and their Implementation
Practices.

Transcribe every Consideration that appears on THESE pages, with its number and its title
verbatim, and every Implementation Practice underneath it verbatim. Do not paraphrase,
shorten or merge practices -- this is a transcription task, and the wording is the point.

A Consideration may continue from the previous page or onto the next. Record whatever
appears on these pages; the parts on other pages are captured separately and merged.

Count the Considerations and the practices on these pages yourself before transcribing,
and put those numbers in the two count fields.

For `source.page`, read the PRINTED page number from the page footer."""


# ------------------------------------------------------- agentic (Future Perspectives)


def _agentic_tool() -> dict[str, Any]:
    factor = s.obj(
        {
            "factor": s.string("The risk factor's name as printed."),
            "description": s.string("What it involves."),
            "source": source_schema(),
        }
    )
    delegate = s.obj(
        {
            "activity": s.string("The activity that should not be fully delegated to AI."),
            "why": s.nullable_string("The reason given, or null."),
            "source": source_schema(),
        }
    )
    control = s.obj(
        {
            "control": s.string("The control's name as printed."),
            "description": s.string("What it does."),
            "source": source_schema(),
        }
    )
    return s.tool(
        "record_agentic_risks",
        "Record the agentic AI risk material from the Future Perspectives section.",
        s.obj(
            {
                "agentic_risk_factors": s.arr(
                    factor, description="Risk factors specific to agentic AI."
                ),
                "accountability_principle": s.nullable_string(
                    "The handbook's statement about accountability following control, "
                    "verbatim, or null if these pages do not state it."
                ),
                "accountability_source": s.obj(
                    {
                        "page": s.nullable_integer("Printed page, or null if not stated."),
                        "quote": s.nullable_string("Verbatim quote, or null."),
                    }
                ),
                "never_delegate_examples": s.arr(
                    delegate,
                    description=(
                        "Activities the handbook says should not be fully delegated to AI, "
                        "e.g. authorising transactions or employment decisions. "
                        "Empty if none are named."
                    ),
                ),
                "interruption_controls": s.arr(
                    control,
                    description=(
                        "Controls for interrupting or constraining an agent: kill switches, "
                        "timeouts, distributed approvals, least privilege. Empty if none."
                    ),
                ),
                "tool_access_risks": s.arr(
                    factor,
                    description=(
                        "Risks arising from the tools or systems an agent can reach, "
                        "including internet access and attack surface. Empty if none."
                    ),
                ),
                "unreadable_items": s.arr(
                    s.string("Anything you could not read."), description="Empty if none."
                ),
            }
        ),
    )


def _agentic_framework_tool() -> dict[str, Any]:
    item = s.obj(
        {
            "name": s.string("The item's name as printed."),
            "description": s.string("Its description as printed."),
            "source": source_schema(),
        }
    )
    comparison = s.obj(
        {
            "aspect": s.string("What is being compared."),
            "gen_ai": s.nullable_string("How it applies to Gen AI, or null."),
            "agentic_ai": s.nullable_string("How it applies to agentic AI, or null."),
            "source": source_schema(),
        }
    )
    return s.tool(
        "record_agentic_framework",
        "Record any external agentic AI framework these pages summarise.",
        s.obj(
            {
                "framework_name": s.nullable_string(
                    "The name of the external agentic framework these pages describe "
                    "(e.g. a regulator's framework), or null if none is described."
                ),
                "risk_sources": s.arr(
                    item, description="The framework's named risk sources. Empty if none."
                ),
                "framework_dimensions": s.arr(
                    item, description="The framework's named dimensions. Empty if none."
                ),
                "gen_ai_vs_agentic": s.arr(
                    comparison,
                    description=(
                        "Points of comparison these pages draw between Gen AI and agentic "
                        "AI architectures. Empty if none."
                    ),
                ),
                "unreadable_items": s.arr(
                    s.string("Anything you could not read."), description="Empty if none."
                ),
            }
        ),
    )


AGENTIC_INSTRUCTION = """\
These pages are the handbook's forward-looking section on where AI risk management is
heading, including agentic AI.

Capture the risk factors that are specific to agentic AI, and in particular anything
about the tools or systems an agent can reach, its autonomy, and the attack surface that
comes with internet or system access.

Look for a statement about accountability tracking control -- that whoever controls or
deploys an agent remains accountable for what it does. Quote it verbatim if present; if
these pages do not state it, return null rather than composing one.

Record any activity the handbook says should not be fully delegated to an AI system, and
every control it names for interrupting or constraining an agent: kill switches, timeouts,
distributed or multi-party approvals, least-privilege access.

For `source.page`, read the PRINTED page number from the page footer."""


AGENTIC_FRAMEWORK_INSTRUCTION = """\
These pages may summarise an external framework for governing agentic AI, published by a
regulator or standards body, with its own named risk sources and dimensions.

If such a framework is described, record its name, each named risk source and each named
dimension. If these pages describe no external framework, return null for the name and
empty arrays -- do not substitute a framework you know from elsewhere.

Also capture any comparison these pages draw between Gen AI and agentic AI architectures.

For `source.page`, read the PRINTED page number from the page footer."""


# ------------------------------------------------------------------- illustrations


def _illustrations_tool() -> dict[str, Any]:
    illustration = s.obj(
        {
            "label": s.string("The illustration's label as printed, e.g. 'Illustration 2.3.1'."),
            "institution": s.string("The financial institution it describes."),
            "title": s.string("Its title as printed."),
            "summary": s.string(
                "What this institution does, in three or four sentences, faithful to "
                "the page."
            ),
            "practices": s.arr(
                s.string("A concrete practice this institution applies."),
                description="The specific practices described, not generalities.",
            ),
            "handbook_topics": s.arr(
                s.string("A handbook topic this illustrates, e.g. 'third party AI risk'."),
                description="What the illustration is an example of.",
            ),
            "source": source_schema(),
        }
    )
    return s.tool(
        "record_illustrations",
        "Record the financial-institution illustrations as structured summaries.",
        s.obj(
            {
                "illustrations": s.arr(
                    illustration, description="Every illustration on these pages."
                ),
                "total_illustrations_counted": s.integer(
                    "Your own count of illustrations on these pages."
                ),
                "unreadable_items": s.arr(
                    s.string("Anything you could not read."), description="Empty if none."
                ),
            }
        ),
    )


ILLUSTRATIONS_INSTRUCTION = """\
These pages carry the handbook's illustrations: short case studies of how named financial
institutions handle AI risk. The pages are drawn from across the handbook, so they are
not continuous.

For each illustration, record the institution, the title, a faithful three-or-four
sentence summary, and the concrete practices it describes. Stay close to what the page
says -- these summaries are used as worked examples, so an embellished one is worse than
a short one.

Some pages here are the page following an illustration, included in case it continues.
If a page carries no illustration, simply ignore it.

For `source.page`, read the PRINTED page number from the page footer."""


def validate_dimensions(
    data: dict[str, Any], page_map: PageMap, pages: list[int]
) -> list[str]:
    problems: list[str] = []
    dimensions = data.get("dimensions") or []
    names = [d.get("dimension") for d in dimensions]
    if len(dimensions) != len(DIMENSIONS):
        problems.append(f"expected {len(DIMENSIONS)} dimensions, got {len(dimensions)}")
    missing = [d for d in DIMENSIONS if d not in names]
    if missing:
        problems.append(f"missing dimensions: {', '.join(missing)}")
    if len(set(names)) != len(names):
        problems.append("duplicate dimensions returned")

    total_risks = 0
    for dimension in dimensions:
        risks = dimension.get("risks") or []
        if not risks:
            problems.append(f"dimension {dimension.get('dimension')!r} has no risks")
        total_risks += len(risks)
        problems.extend(_check_sources(risks, page_map, pages, "risk"))

    legend = data.get("lifecycle_stage_legend") or []
    uses_numeric_stages = any(
        stage.strip().isdigit()
        for dimension in dimensions
        for risk in (dimension.get("risks") or [])
        for stage in (risk.get("lifecycle_stages") or [])
    )
    if uses_numeric_stages and not legend:
        problems.append("risks cite numeric lifecycle stages but no legend was captured")

    counted = data.get("total_risk_rows_counted")
    if not isinstance(counted, int) or counted <= 0:
        problems.append(f"total_risk_rows_counted is {counted!r}")
    elif counted > total_risks:
        problems.append(
            f"model counted {counted} risk rows but returned only {total_risks}"
        )

    problems.extend(_check_sources(dimensions, page_map, pages, "dimension"))
    return problems


def validate_materiality(
    data: dict[str, Any], page_map: PageMap, pages: list[int]
) -> list[str]:
    problems: list[str] = []
    factors = data.get("inherent_risk_factors") or []
    if not factors:
        problems.append("no inherent risk factors returned")
    counted = data.get("total_factors_counted")
    if isinstance(counted, int) and counted != len(factors):
        problems.append(f"model counted {counted} factors but returned {len(factors)}")
    problems.extend(_check_sources(factors, page_map, pages, "factor"))

    tiers = data.get("tiers") or []
    tier_names = sorted(str(t.get("tier")) for t in tiers)
    if tier_names != sorted(RATINGS):
        problems.append(f"expected tiers {sorted(RATINGS)}, got {tier_names}")

    figure = data.get("figure_2_4_3") or {}
    if not figure.get("read_successfully"):
        problems.append("Figure 2.4.3 was not read successfully")
    rows = figure.get("axis_inherent_values") or []
    cols = figure.get("axis_evaluation_values") or []
    cells = figure.get("cells") or []
    if not rows or not cols:
        problems.append("Figure 2.4.3 axes are empty")
    elif len(cells) != len(rows) * len(cols):
        problems.append(
            f"Figure 2.4.3 has {len(rows)}x{len(cols)} axes but {len(cells)} cells"
        )
    seen = {(str(c.get("inherent_tier")), str(c.get("evaluation_result"))) for c in cells}
    if len(seen) != len(cells):
        problems.append("Figure 2.4.3 has duplicate cells")
    for cell in cells:
        tiers = cell.get("residual_tiers") or []
        label = str(cell.get("residual_label") or "")
        if not tiers:
            problems.append(
                f"Figure 2.4.3 cell {cell.get('inherent_tier')}/"
                f"{cell.get('evaluation_result')} has no residual_tiers"
            )
        # A label naming two tiers must not be collapsed to one.
        if label.count("/") >= 1 and len(tiers) < 2:
            problems.append(
                f"Figure 2.4.3 cell labelled {label!r} collapsed to {tiers}"
            )
    return problems


def _counted(data: dict[str, Any], key: str, items: list[Any], label: str) -> list[str]:
    """Flag a SHORTFALL against the model's own count -- that means rows were dropped.

    A surplus is the opposite situation: the model transcribed more rows than it counted,
    so nothing is missing and it simply miscounted. Treating a surplus as a failure just
    burns retries on an extraction that is already complete.
    """
    counted = data.get(key)
    if not isinstance(counted, int):
        return [f"{key} is {counted!r}"]
    if counted > len(items):
        return [f"model counted {counted} {label} but returned only {len(items)}"]
    return []


def validate_definitions(
    data: dict[str, Any], page_map: PageMap, pages: list[int]
) -> list[str]:
    problems: list[str] = []
    definition = (data.get("ai_definition") or {}).get("definition")
    if not definition:
        problems.append("no AI definition returned")
    if not data.get("terms"):
        problems.append("no defined terms returned")
    if not data.get("out_of_scope_examples"):
        # The whole point of `ai_in_scope` is the out-of-scope boundary; a section on
        # scope that yields no exclusions almost certainly means the model skimmed.
        problems.append("no out-of-scope examples returned")
    for key, label in (
        ("in_scope_examples", "in-scope example"),
        ("out_of_scope_examples", "out-of-scope example"),
        ("terms", "term"),
    ):
        problems.extend(_check_sources(data.get(key) or [], page_map, pages, label))
    return problems


def validate_oversight(data: dict[str, Any], page_map: PageMap, pages: list[int]) -> list[str]:
    problems: list[str] = []
    modes = data.get("modes") or []
    names = [m.get("mode") for m in modes]
    missing = [m for m in OVERSIGHT_MODES if m not in names]
    if missing:
        problems.append(f"missing oversight modes: {', '.join(missing)}")
    if len(set(names)) != len(names):
        problems.append("duplicate oversight modes returned")
    problems.extend(_check_sources(modes, page_map, pages, "mode"))

    sampling = data.get("sampling_methodologies") or []
    if not sampling:
        problems.append("no sampling methodologies returned")
    problems.extend(_counted(data, "total_sampling_rows_counted", sampling, "sampling rows"))
    problems.extend(_check_sources(sampling, page_map, pages, "sampling method"))
    if not data.get("interruption_controls"):
        problems.append("no interruption controls returned")
    return problems


def validate_metrics(data: dict[str, Any], page_map: PageMap, pages: list[int]) -> list[str]:
    metrics = data.get("metrics") or []
    problems = [] if metrics else ["no metrics returned"]
    problems.extend(_counted(data, "total_metrics_counted", metrics, "metrics"))
    problems.extend(_check_sources(metrics, page_map, pages, "metric"))
    return problems


def validate_guardrails(data: dict[str, Any], page_map: PageMap, pages: list[int]) -> list[str]:
    guardrails = data.get("guardrails") or []
    problems = [] if guardrails else ["no guardrails returned"]
    problems.extend(_counted(data, "total_guardrails_counted", guardrails, "guardrails"))
    problems.extend(_check_sources(guardrails, page_map, pages, "guardrail"))
    return problems


def validate_considerations(
    data: dict[str, Any], page_map: PageMap, pages: list[int]
) -> list[str]:
    problems: list[str] = []
    considerations = data.get("considerations") or []
    numbers = [c.get("number") for c in considerations]
    if sorted(n for n in numbers if isinstance(n, int)) != list(range(1, 18)):
        problems.append(
            f"expected Considerations 1-17, got {sorted(n for n in numbers if n is not None)}"
        )
    if len(set(numbers)) != len(numbers):
        problems.append("duplicate Consideration numbers returned")
    for consideration in considerations:
        if not consideration.get("implementation_practices"):
            problems.append(f"Consideration {consideration.get('number')} has no practices")

    # The model counts practices separately from transcribing them. A shortfall means
    # practices were dropped -- which is exactly what a chunk boundary running through
    # the middle of a Consideration produces.
    practices = [p for c in considerations for p in c.get("implementation_practices", [])]
    problems.extend(
        _counted(data, "total_practices_counted", practices, "implementation practices")
    )
    problems.extend(
        _counted(data, "total_considerations_counted", considerations, "Considerations")
    )

    # A practice stranded in unreadable_items is a practice that never made it into the
    # output; the extractor is meant to return it, not describe it.
    for note in data.get("unreadable_items") or []:
        if "implementation practice" in str(note).lower():
            problems.append(f"practices reported as unread rather than extracted: {note[:120]}")

    problems.extend(_check_sources(considerations, page_map, pages, "consideration"))
    return problems


def validate_agentic(data: dict[str, Any], page_map: PageMap, pages: list[int]) -> list[str]:
    problems: list[str] = []
    if not data.get("agentic_risk_factors"):
        problems.append("no agentic risk factors returned")
    if not data.get("interruption_controls"):
        problems.append("no interruption controls returned")
    for key, label in (
        ("agentic_risk_factors", "agentic factor"),
        ("never_delegate_examples", "never-delegate example"),
        ("interruption_controls", "interruption control"),
        ("tool_access_risks", "tool access risk"),
    ):
        problems.extend(_check_sources(data.get(key) or [], page_map, pages, label))
    return problems


def validate_illustrations(
    data: dict[str, Any], page_map: PageMap, pages: list[int]
) -> list[str]:
    illustrations = data.get("illustrations") or []
    problems = [] if illustrations else ["no illustrations returned"]
    problems.extend(_check_sources(illustrations, page_map, pages, "illustration"))
    for item in illustrations:
        if not item.get("practices"):
            problems.append(f"{item.get('label')}: no practices captured")
    return problems


def _illustration_pages(page_map: PageMap) -> list[int]:
    """Each illustration's page plus the one after it, in case it runs on."""
    pages: list[int] = []
    for item in page_map.raw.get("illustrations", []):
        printed = item.get("printed_page")
        if not isinstance(printed, int):
            continue
        first = page_map.printed_to_pdf(printed)
        pages.extend([first, first + 1])
    return [p for p in pages if 1 <= p <= page_map.total_pages]


def _oversight_pages(page_map: PageMap) -> list[int]:
    """3.1 defines the oversight modes; 3.4 and 3.5 carry monitoring and kill switches."""
    pages: list[int] = []
    for section in ("3.1", "3.4", "3.5"):
        pages.extend(page_map.range_for(section).pages)
    return pages


# -------------------------------------------------------------------------- registry


EXTRACTORS: dict[str, Extractor] = {
    "dimensions_taxonomy": Extractor(
        name="dimensions_taxonomy",
        description="Appendix B: the 7 risk dimensions and every named risk under each.",
        section_label="Appendix B",
        passes=(
            Pass("taxonomy", _dimensions_tool, DIMENSIONS_INSTRUCTION),
        ),
        list_keys=("dimensions",),
        pages_resolver=lambda pm: pm.range_for("B").pages,
        extra_context="Appendix B of the handbook: the MindForge AI Risk Taxonomy.",
        validator=validate_dimensions,
    ),
    "materiality_factors": Extractor(
        name="materiality_factors",
        description="Section 2.4: inherent-risk factors, tiering, and the Fig 2.4.3 matrix.",
        section_label="2.4",
        passes=(
            Pass("factors", _materiality_factors_tool, MATERIALITY_FACTORS_INSTRUCTION),
            Pass("matrix", _materiality_matrix_tool, MATERIALITY_MATRIX_INSTRUCTION),
        ),
        list_keys=("inherent_risk_factors", "tiers"),
        pages_resolver=lambda pm: pm.range_for("2.4").pages,
        extra_context="Section 2.4 of the handbook, on use case-level AI risk management.",
        validator=validate_materiality,
    ),
    "definitions": Extractor(
        name="definitions",
        description="Section 1.1: what counts as AI in scope, and the key distinctions.",
        section_label="1.1",
        passes=(Pass("definitions", _definitions_tool, DEFINITIONS_INSTRUCTION),),
        list_keys=("terms",),
        pages_resolver=lambda pm: pm.range_for("1.1").pages,
        extra_context="Section 1.1 of the handbook, on scope and application.",
        validator=validate_definitions,
    ),
    "oversight_modes": Extractor(
        name="oversight_modes",
        description="Sections 3.1/3.4/3.5: oversight modes, sampling, kill switches.",
        section_label="3.1, 3.4 and 3.5",
        passes=(
            Pass("modes", _oversight_tool, OVERSIGHT_INSTRUCTION),
            Pass("monitoring", _monitoring_tool, MONITORING_INSTRUCTION),
        ),
        list_keys=("modes",),
        pages_resolver=_oversight_pages,
        extra_context="Sections 3.1, 3.4 and 3.5 of the handbook.",
        validator=validate_oversight,
    ),
    "metrics": Extractor(
        name="metrics",
        description="Appendix F: the library of AI metrics.",
        section_label="Appendix F",
        passes=(Pass("metrics", _metrics_tool, METRICS_INSTRUCTION),),
        list_keys=("metrics",),
        pages_resolver=lambda pm: pm.range_for("F").pages,
        extra_context="Appendix F of the handbook: the Library of AI Metrics.",
        validator=validate_metrics,
    ),
    "guardrails": Extractor(
        name="guardrails",
        description="Appendix G: the library of AI guardrails and interpretability types.",
        section_label="Appendix G",
        passes=(Pass("guardrails", _guardrails_tool, GUARDRAILS_INSTRUCTION),),
        list_keys=("guardrails",),
        pages_resolver=lambda pm: pm.range_for("G").pages,
        extra_context="Appendix G of the handbook: the Library of AI Guardrails.",
        validator=validate_guardrails,
    ),
    "considerations": Extractor(
        name="considerations",
        description="Appendix H: the 17 Considerations and their Implementation Practices.",
        section_label="Appendix H",
        passes=(Pass("considerations", _considerations_tool, CONSIDERATIONS_INSTRUCTION),),
        list_keys=("considerations",),
        pages_resolver=lambda pm: pm.range_for("H").pages,
        extra_context="Appendix H: the MindForge AI Risk Management Checklist.",
        validator=validate_considerations,
        # Appendix H fits in one request (~10k output tokens), and splitting it was
        # actively harmful: a Consideration straddling a boundary lost the practices
        # that fell in the next chunk. If it ever must be split, the overlap and the
        # dedupe key below keep straddling Considerations whole.
        chunk_overlap=1,
        dedupe_keys=(("considerations", "number"),),
    ),
    "agentic": Extractor(
        name="agentic",
        description="Future Perspectives: agentic risks, accountability, interruption.",
        section_label="Future Perspectives",
        passes=(
            Pass("risks", _agentic_tool, AGENTIC_INSTRUCTION),
            Pass("framework", _agentic_framework_tool, AGENTIC_FRAMEWORK_INSTRUCTION),
        ),
        list_keys=("agentic_risk_factors",),
        pages_resolver=lambda pm: pm.range_for_title("Future Perspectives").pages,
        extra_context="The handbook's Future Perspectives section.",
        validator=validate_agentic,
    ),
    "illustrations": Extractor(
        name="illustrations",
        description="The financial-institution illustrations, as few-shot material.",
        section_label="Illustrations",
        passes=(Pass("illustrations", _illustrations_tool, ILLUSTRATIONS_INSTRUCTION),),
        list_keys=("illustrations",),
        pages_resolver=_illustration_pages,
        extra_context="Illustrations drawn from across the handbook.",
        validator=validate_illustrations,
    ),
}
