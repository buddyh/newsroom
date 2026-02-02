"""Brave Search API integration for topic research."""

import os
from pathlib import Path

import httpx


BRAVE_SEARCH_URL = "https://api.search.brave.com/res/v1/web/search"


async def search_brave(
    topic: str, count: int = 10, freshness: str | None = None,
) -> list[dict]:
    """Fetch web search results from Brave Search API.

    Args:
        freshness: Filter by recency. Predefined: pd (past day), pw (past week),
            pm (past month), py (past year). Custom: YYYY-MM-DDtoYYYY-MM-DD.
    """
    api_key = os.environ.get("BRAVE_API_KEY")
    if not api_key:
        return []

    params: dict[str, str | int] = {"q": f"{topic} news", "count": count}
    if freshness:
        params["freshness"] = freshness

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(
            BRAVE_SEARCH_URL,
            params=params,
            headers={
                "X-Subscription-Token": api_key,
                "Accept": "application/json",
            },
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("web", {}).get("results", [])


def results_to_markdown(topic: str, results: list[dict]) -> str:
    """Convert Brave search results to a markdown research summary."""
    if not results:
        lines = [
            f"# Research: {topic}",
            "",
            "No live research available. Use internal knowledge.",
        ]
        return "\n".join(lines)

    lines = [f"# Research: {topic}", ""]
    for item in results:
        title = item.get("title", "No Title")
        url = item.get("url", "")
        desc = item.get("description", "")
        age = item.get("age", "")
        lines.extend([
            f"## {title}",
            f"Date: {age}",
            f"Source: {url}",
            f"Summary: {desc}",
            "",
        ])
    return "\n".join(lines)


async def gather_research(
    topic: str, run_dir: Path, freshness: str | None = None,
) -> Path:
    """Run research and save markdown summary. Returns path to summary."""
    research_dir = run_dir / "research"
    research_dir.mkdir(parents=True, exist_ok=True)
    summary_path = research_dir / "summary.md"

    try:
        results = await search_brave(topic, freshness=freshness)
    except (httpx.HTTPError, Exception) as exc:
        print(f"  Research failed ({exc}), continuing without.")
        results = []

    md = results_to_markdown(topic, results)
    summary_path.write_text(md)
    print(f"  Research saved: {summary_path}")
    return summary_path
