"""Decisioning: scoring, selection, and reporting with agent support.

This module filters analyzed items, scores them with heuristics, and optionally
uses an agent to produce a plain-text report when there are strong candidates.
"""

from textwrap import dedent
from typing import List, Optional

from shared.llm import get_agent_model
from shared.logging import get_logger
from .models import AnalysisResult, DecisionReport, PipelineTask, ScoredAnalysis
from .utils import retry_async


logger = get_logger(__name__)


def score_result(task: PipelineTask, result: AnalysisResult) -> float:
    """Compute overall score in ``[0, 100]`` using relevance and simple boosts.

    :param task: The pipeline task providing thresholds.
    :param result: A single analysis result to score.
    :returns: Score in the range ``[0, 100]``.
    """

    score = float(max(0.0, min(100.0, result.relevance)))
    # Tiny boost if summary mentions code/dataset/benchmark
    text = (result.summary or "").lower()
    if any(k in text for k in ("code", "github", "dataset", "benchmark")):
        score = min(100.0, score + 5.0)
    return score


def select_top(
    task: PipelineTask, analyzed: List[AnalysisResult]
) -> List[ScoredAnalysis]:
    """Score and keep items above ``min_relevance`` in descending order.

    The output is trimmed to at most three items to keep reports concise.

    :param task: Pipeline task with ``min_relevance``.
    :param analyzed: Analysis results to select from.
    :returns: Compact, sorted selection of :class:`ScoredAnalysis`.
    """

    items: List[ScoredAnalysis] = []
    for r in analyzed:
        s = score_result(task, r)
        if s >= task.min_relevance:
            items.append(ScoredAnalysis(result=r, overall_score=s))
    items.sort(key=lambda x: x.overall_score, reverse=True)
    # Keep report concise: at most top 3
    return items[: max(1, min(len(items), 3))]


def _get_reporter():
    """Lazy initialization of the reporter agent."""
    from agents import Agent

    return Agent(
        name="Decision Reporter",
        model=get_agent_model(),
        instructions=dedent(
            """
            You are a friendly research assistant who helps people understand new scientific findings.
            
            When given research papers and a user's task, create a warm, conversational message explaining what was found.
            
            Goals:
            - Write like you're texting a friend about exciting discoveries
            - Explain what was found and why it matters in simple words
            - Be enthusiastic but not overwhelming
            - Avoid technical jargon and formal academic language
            
            Format (plain text, no HTML/markdown):
            🔬 Great news! I found some interesting research on [topic]
            
            [2-3 sentences explaining the most important findings in simple terms]
            
            Here are the papers I think you'll find most helpful:
            • [Paper title in simpler words] - [why this is useful for their goal]
            • [Second paper if relevant]
            
            [One encouraging closing line about how this research could help them]
            
            Rules:
            - Use everyday language, short sentences
            - Max 500 characters total
            - Be encouraging and helpful
            - Focus on practical value, not technical details
            
            Return JSON: {"should_notify": boolean, "report_text": string|null}
            - If nothing truly helpful: should_notify=false, report_text=null
            - Otherwise: should_notify=true with the friendly message
"""
        ),
        output_type=DecisionReport,
    )


async def make_decision_and_report(
    task: PipelineTask, selected: List[ScoredAnalysis]
) -> DecisionReport:
    """Generate a plain-text report or decide to skip notifying the user.

    Uses an LLM-based reporter when available, falling back to a local
    template otherwise.

    :param task: The source task that describes user intent.
    :param selected: A compact list of scored analyses.
    :returns: Decision and optional report text.
    """

    if not selected:
        return DecisionReport(should_notify=False, report_text=None)

    try:
        import json

        payload = json.dumps(
            {
                "task": task.query,
                "items": [
                    {
                        "title": s.result.candidate.title,
                        "summary": s.result.summary,
                        "score": s.overall_score,
                        "link": s.result.candidate.abs_url
                        or s.result.candidate.pdf_url,
                    }
                    for s in selected
                ],
            }
        )
        from agents import Runner

        logger.info("Making request to decision reporter...")
        result = await retry_async(lambda: Runner.run(_get_reporter(), payload))

        # Append the "Links" block to the result
        result.final_output.report_text += "\n\nLinks:\n"
        for s in selected:
            result.final_output.report_text += f'• <a href="{s.result.candidate.abs_url}">{s.result.candidate.title}</a>\n'

        return result.final_output
    except Exception as error:
        logger.warning(f"Decision reporter failed, fallback to template: {error}")

    # Improved fallback template - more human-friendly
    lines: List[str] = []
    lines.append(f"🔬 Great news! I found some research on {task.query}")
    lines.append("")

    if len(selected) == 1:
        lines.append("Here's an interesting paper that might help:")
    else:
        lines.append(f"Here are {len(selected)} papers that look promising:")
    lines.append("")

    for i, s in enumerate(selected[:3], 1):
        title = s.result.candidate.title
        link = s.result.candidate.abs_url or s.result.candidate.pdf_url or ""

        # Simplify technical titles
        simple_title = _simplify_title(title)
        lines.append(f"{i}. {simple_title}")
        lines.append(
            f"   This could help with {_human_why_for_task(task.query, s.result.summary or '')}"
        )
        # Always include the link if available
        if link:
            lines.append(f"   📎 {link}")
        else:
            logger.warning(f"No link available for paper: {title}")
        lines.append("")

    lines.append("Hope this helps with your research! 🚀")
    text = "\n".join(lines).strip()
    return DecisionReport(should_notify=True, report_text=_compact_report_text(text))


def _compact_report_text(text: Optional[str], max_chars: int = 3000) -> Optional[str]:
    """Compact and normalize report text to a maximum number of characters.

    :param text: The raw report text or ``None``.
    :param max_chars: Maximum characters allowed (default 3000).
    :returns: The normalized, possibly truncated text, or ``None``.
    """
    if not text:
        return text
    t = str(text)
    # Normalize whitespace and limit lines
    t = "\n".join([ln.strip() for ln in t.splitlines() if ln.strip()])
    if len(t) > max_chars:
        t = t[: max_chars - 3].rstrip() + "..."
    return t


def _simplify_title(title: str) -> str:
    """Simplify technical paper titles for better readability.

    :param title: Original paper title
    :returns: Simplified title
    """
    # Remove common technical prefixes/suffixes
    simplified = title

    # Replace complex terms with simpler ones
    replacements = {
        "A Novel": "New",
        "An Efficient": "Better",
        "Robust": "Strong",
        "State-of-the-Art": "Advanced",
        "Deep Learning": "AI",
        "Machine Learning": "AI",
        "Neural Network": "AI System",
        "Algorithm": "Method",
        "Framework": "System",
        "Methodology": "Method",
        "Optimization": "Improvement",
    }

    for old, new in replacements.items():
        simplified = simplified.replace(old, new)

    # Truncate if too long
    if len(simplified) > 80:
        simplified = simplified[:77] + "..."

    return simplified


def _human_why_for_task(task_query: str, summary: str, max_len: int = 150) -> str:
    """Generate a human-friendly explanation of why a paper is useful.

    :param task_query: The user task description.
    :param summary: Candidate summary to inspect.
    :param max_len: Maximum length of the explanation.
    :returns: A friendly explanation string.
    """
    import re

    def toks(s: str) -> List[str]:
        return re.findall(r"[a-zA-Z0-9\-]+", s.lower())

    task_terms = set(toks(task_query)) - {
        "the",
        "and",
        "or",
        "of",
        "to",
        "for",
        "a",
        "in",
        "your",
        "this",
        "that",
    }

    sent = (summary or "").strip().split(". ")[0]
    overlaps = [w for w in toks(sent) if w in task_terms]

    if overlaps and len(overlaps) >= 2:
        # Multiple relevant terms found
        key_terms = overlaps[:2]
        text = f"understanding {' and '.join(key_terms)}"
    elif overlaps:
        # Single relevant term
        text = f"research on {overlaps[0]}"
    elif summary and len(summary.strip()) > 10:
        # Use part of summary
        first_sentence = sent[:100]
        if first_sentence.lower().startswith(("this", "the", "we", "our")):
            text = "exploring relevant methods and findings"
        else:
            text = f"exploring {first_sentence.lower()}"
    else:
        # Generic fallback
        text = "related research methods"

    # Add variety to avoid repetition
    prefixes = ["exploring", "understanding", "learning about", "diving into"]
    if not any(text.startswith(p) for p in prefixes):
        text = f"exploring {text}"

    if len(text) > max_len:
        text = text[: max_len - 3].rstrip() + "..."

    return text


def _why_for_task(task_query: str, summary: str, max_len: int = 220) -> str:
    """Heuristic one-liner explaining usefulness for the task.

    Prefers overlap of task terms with summary; falls back to the first sentence.

    :param task_query: The user task description.
    :param summary: Candidate summary to inspect.
    :param max_len: Maximum length of the produced sentence (default 220).
    :returns: A concise explanation string.
    """
    import re

    def toks(s: str) -> List[str]:
        return re.findall(r"[a-zA-Z0-9\-]+", s.lower())

    task_terms = set(toks(task_query)) - {
        "the",
        "and",
        "or",
        "of",
        "to",
        "for",
        "a",
        "in",
    }
    sent = (summary or "").strip().split(". ")[0]
    overlaps = [w for w in toks(sent) if w in task_terms]
    if overlaps:
        unique = []
        for w in overlaps:
            if w not in unique:
                unique.append(w)
        phrase = ", ".join(unique[:3])
        text = f"addresses {phrase} relevant to your task"
    else:
        text = sent or "directly related methods and findings"
    if len(text) > max_len:
        text = text[: max_len - 3].rstrip() + "..."
    return text
