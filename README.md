# codebase-explorer-mcp

An MCP server that analyzes any codebase — detects project type, languages, framework, entry points, API routes, controllers, services, components, tests, and more.

## Quick start

### 1. Install `uv`

```powershell
# Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Verify: `uv --version`

> **Why `uv`?** `uv.lock` pins exact dependency versions (like `package-lock.json`), so everyone gets identical environments. `mcp dev` also uses `uvx` under the hood.

### 2. Setup the project

```bash
cd /path/to/codebase-explorer-mcp
uv sync
```

This reads `uv.lock`, creates `.venv`, and installs all dependencies.

### 3a. Use with Claude Desktop

Find your venv Python path:
```powershell
# From the project folder:
.venv\Scripts\python.exe --version
```

Add to `claude_desktop_config.json` (`%APPDATA%\Claude\claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "codebase-explorer": {
      "command": "C:\\full\\path\\to\\codebase-explorer-mcp\\.venv\\Scripts\\python.exe",
      "args": ["server.py"],
      "cwd": "C:\\full\\path\\to\\codebase-explorer-mcp"
    }
  }
}
```

Restart Claude Desktop.

### 3b. Test with MCP Inspector (development)

```bash
cd /path/to/codebase-explorer-mcp
mcp dev server.py
```

Opens `http://localhost:6274` — test all tools live in a web UI.

---

## How to use

**You only need to provide the repo path** — the server auto-discovers everything else.

| Tool | What you give it | What it returns |
|---|---|---|
| `analyze_structure` | `path` | Languages, file count, entry points, directory tree |
| `find_features` | `path` | Routes, controllers, components, tests, interfaces |
| `get_feature_detail` | `path`, `name` | Code context around a feature (auto-locates file + line) |
| `generate_architecture` | `path` | Layered Mermaid diagram — entry points, API, services, data, UI with import connections |
| `search_symbols` | `path`, `pattern` | Regex search results across all source files |
| `list_project_types` | _(none)_ | List of project types and frameworks the server can detect |

### Example flow

1. Get an overview: `analyze_structure(path="C:\\MyProject")`
2. See the big picture: `generate_architecture(path="C:\\MyProject")`
   → Renders a Mermaid diagram with layers: Entry → API → Logic → Data → UI, plus import graph edges
3. Find specific features: `find_features(path="C:\\MyProject")`
   → See all API routes, controllers, tests listed with their file locations
4. Inspect one: `get_feature_detail(path="C:\\MyProject", name="get_users")`
   → Shows code context around that feature, no need to know the file or line number
5. Search: `search_symbols(path="C:\\MyProject", pattern="async def")`
   → Find all async functions in the codebase

### Alternative setup (without `uv`)

```bash
python -m venv venv
venv\Scripts\activate     # Windows
# source venv/bin/activate  # macOS / Linux
pip install "mcp[cli]>=1.6.0"
python server.py
```

## Supported Languages

Python, JavaScript/TypeScript, Java, Go, Ruby, C#, Rust, PHP, Kotlin, Swift, and more.
