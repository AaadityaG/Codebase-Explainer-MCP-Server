from mcp.server.fastmcp import FastMCP

from analyzer import (
    analyze_codebase,
    find_features as find_features_in_files,
    search_codebase,
    generate_architecture_diagram,
    find_dead_code,
    find_git_info,
    scan_secrets,
)

mcp = FastMCP("codebase-explorer")


@mcp.tool()
async def analyze_structure(path: str, depth: int = 3) -> str:
    """Get a high-level overview of a codebase: languages, file count, entry points, and directory tree."""
    result = await analyze_codebase(path, max_depth=depth)
    if "error" in result:
        return f"Error: {result['error']}"

    lines = [
        f"# {result['projectName']}",
        f"**Path:** {result['projectPath']}",
        f"**Type:** {result['projectType'] or 'Unknown'}",
        f"**Framework:** {result['framework'] or 'None detected'}",
        f"**Files:** {result['fileCount']}  |  **Lines:** {result['totalLines']}",
    ]
    if result["languages"]:
        lines.append("\n## Languages")
        for lang, count in result["languages"].items():
            lines.append(f"- {lang}: {count} files")
    if result["entryPoints"]:
        lines.append("\n## Entry Points")
        for ep in result["entryPoints"]:
            lines.append(f"- `{ep['file']}`")
    if result["features"]:
        lines.append(f"\n## Features ({len(result['features'])} found)")
        lines.append("_Use `find_features` for full details._")

    return "\n".join(lines)


@mcp.tool()
async def find_features(path: str, type_filter: str = "") -> str:
    """Detect features, API routes, controllers, components, and patterns in the codebase.
    Optionally filter by type (e.g. 'API Route', 'Controller', 'Component', 'Test')."""
    from pathlib import Path
    from analyzer import Feature, collect_source_files

    root = Path(path).resolve()

    if root.is_file():
        source_files = [root]
        root = root.parent
    elif root.is_dir():
        source_files = collect_source_files(root)
    else:
        return f"Error: Path not found: {path}"

    features: list[Feature] = await find_features_in_files(root, source_files)

    if type_filter:
        features = [f for f in features if type_filter.lower() in f.type.lower()]

    if not features:
        return f"No features found{' matching "' + type_filter + '"' if type_filter else ''}."

    lines = [f"# Features Found ({len(features)})"]
    if type_filter:
        lines.append(f"Filtered by: `{type_filter}`")

    by_type: dict[str, list[Feature]] = {}
    for feat in features:
        by_type.setdefault(feat.type, []).append(feat)

    for ftype, feats in sorted(by_type.items()):
        lines.append(f"\n## {ftype} ({len(feats)})")
        for feat in feats[:20]:
            lines.append(f"- `{feat.name}` -> {feat.location}:{feat.line}")
        if len(feats) > 20:
            lines.append(f"  _...and {len(feats) - 20} more_")

    return "\n".join(lines)


@mcp.tool()
async def search_symbols(path: str, pattern: str, file_ext: str = "") -> str:
    """Search for symbols/patterns across the codebase using regex. Optionally filter by file extension (e.g. 'py', 'js', 'ts')."""
    from pathlib import Path
    root = Path(path).resolve()
    if not root.is_dir():
        return f"Error: Directory not found: {path}"
    ext_list = [f".{e.strip()}" for e in file_ext.split(",") if e.strip()] if file_ext else None
    results = await search_codebase(root, pattern, include_ext=ext_list)

    if not results or (isinstance(results, list) and len(results) > 0 and "error" in results[0]):
        return results[0]["error"] if results else "No results found."

    lines = [f"# Search Results for `{pattern}` ({len(results)} matches)"]
    for r in results[:50]:
        lines.append(f"- `{r['file']}:{r['line']}`  {r['content']}")
    if len(results) > 50:
        lines.append(f"\n_...and {len(results) - 50} more matches_")

    return "\n".join(lines)


@mcp.tool()
async def get_feature_detail(path: str, name: str) -> str:
    """Get detailed code context around a feature by name.
    To disambiguate when names collide, append @filepath:line to the name
    (e.g. \"get_user_settings@settings.py\" or \"health_check@main.py:34\").
    The feature name is matched against detected routes, controllers, services, etc."""
    from pathlib import Path
    from analyzer import collect_source_files, find_features as find_features_in_files

    root = Path(path).resolve()
    if not root.is_dir():
        return f"Error: Directory not found: {path}"

    target_file = None
    target_line = None
    if "@" in name:
        name_part, _, hint = name.partition("@")
        if ":" in hint:
            hint_file, _, hint_line = hint.partition(":")
            try:
                target_line = int(hint_line)
            except ValueError:
                pass
        else:
            hint_file = hint
        target_file = hint_file.replace("\\", "/")
        name = name_part

    source_files = collect_source_files(root)
    features = await find_features_in_files(root, source_files)

    matches = [f for f in features if name.lower() in f.name.lower()]
    if target_file:
        matches = [f for f in matches if target_file.lower() in f.location.lower().replace("\\", "/")]
    if target_line is not None:
        exact = [f for f in matches if f.line == target_line]
        if exact:
            matches = exact

    if not matches:
        types = sorted({f.type for f in features})
        hint = ""
        if target_file:
            hint = f" in file matching '{target_file}'"
        return f"No feature matching '{name}'{hint} found.\n\nAvailable types: {', '.join(types)}\nHint: use `find_features` to list features first."

    if len(matches) > 1:
        lines = [f"# Multiple matches for '{name}' ({len(matches)} found)\n"]
        for i, m in enumerate(matches, 1):
            lines.append(f"{i}. `{m.name}` -> {m.location}:{m.line}  ({m.type})")
        lines.append(f"\nTo narrow down, append @filepath to the name (e.g. \"{name}@{matches[0].location}\").")
        return "\n".join(lines)

    feat = matches[0]
    full_path = root / feat.location
    if not full_path.exists():
        return f"File not found: {feat.location}"

    try:
        content = full_path.read_text(encoding="utf-8", errors="ignore")
        content_lines = content.split("\n")
    except Exception as e:
        return f"Error reading file: {e}"

    line = feat.line
    start = max(0, line - 10)
    end = min(len(content_lines), line + 10)

    result = [f"# Context: `{feat.location}` at line {line} - `{feat.name}` ({feat.type})\n"]
    for i in range(start, end):
        marker = " ->" if i + 1 == line else "  "
        result.append(f"{marker} {i+1}: {content_lines[i]}")

    return "\n".join(result)


@mcp.tool()
async def generate_architecture(path: str) -> str:
    """Generate a layered architecture diagram (Mermaid) for the codebase — shows entry points, API routes, services, data models, and how they connect."""
    result = await generate_architecture_diagram(path)
    if "error" in result:
        return f"Error: {result['error']}"
    return result["diagram"]


@mcp.tool()
async def analyze_dead_code(path: str) -> str:
    """Find potentially dead (unused) code — functions, classes, exports defined but never referenced elsewhere."""
    result = await find_dead_code(path)
    if "error" in result:
        return f"Error: {result['error']}"
    return result["report"]


@mcp.tool()
async def get_git_info(path: str) -> str:
    """Get git intelligence for a repository — branch, recent commits, contributors, hot files, and uncommitted changes."""
    result = await find_git_info(path)
    if "error" in result:
        return f"Error: {result['error']}"
    return result["report"]


@mcp.tool()
async def find_secrets(path: str) -> str:
    """Scan the codebase for hardcoded secrets — API keys, tokens, passwords, private keys, and database credentials."""
    result = await scan_secrets(path)
    if "error" in result:
        return f"Error: {result['error']}"
    return result["report"]


def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
