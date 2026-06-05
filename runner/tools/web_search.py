import urllib.request
import urllib.parse
import json
from .registry import register

def _duckduckgo(query: str, max_results: int = 5) -> list[dict]:
    url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        return [{"error": str(e)}]

    results = []
    import re
    for m in re.finditer(
        r'<a[^>]+class="result__a"[^>]*href="(.*?)"[^>]*>(.*?)</a>',
        html,
        re.DOTALL,
    ):
        link = m.group(1)
        title = re.sub(r"<.*?>", "", m.group(2)).strip()
        snippet_match = re.search(
            r'<a[^>]+class="result__snippet"[^>]*>(.*?)</a>',
            html[m.end():],
            re.DOTALL,
        )
        snippet = ""
        if snippet_match:
            snippet = re.sub(r"<.*?>", "", snippet_match.group(1)).strip()
        results.append({"title": title, "link": link, "snippet": snippet})
        if len(results) >= max_results:
            break
    return results if results else [{"info": "no results found"}]


def web_search_tool(args: dict) -> dict:
    query = args.get("query", "")
    if not query:
        return {"success": False, "error": "query is required"}
    max_results = args.get("max_results", 5)
    try:
        results = _duckduckgo(query, max_results)
        return {"success": True, "query": query, "results": results, "count": len(results)}
    except Exception as e:
        return {"success": False, "error": str(e)}


register("web_search", web_search_tool)
