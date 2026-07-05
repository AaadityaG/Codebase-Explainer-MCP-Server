# Tools Reference

## `analyze_structure`
Get a high-level overview of a codebase: languages, file count, entry points, and directory tree.

```
analyze_structure(path="C:\\MyProject")

  MyProject
  Path: C:\MyProject
  Type: FastAPI
  Framework: FastAPI
  Files: 47  |  Lines: 8521

  ## Languages
  - Python: 23 files
  - TypeScript: 18 files
  - CSS: 3 files
  - HTML: 3 files

  ## Entry Points
  - backend/main.py
  - desk-app/electron/main.ts
  - desk-app/src/main.tsx

  ## Features (34 found)
  Use `find_features` for full details.
```

**Parameters:**
- `path` — Path to the project or file
- `depth` (optional, default 3) — Directory tree depth

---

## `find_features`
Detect API routes, controllers, components, services, tests, and other patterns. Optionally filter by type.

```
find_features(path="C:\\MyProject")

  # Features Found (34)

  ## API Route (15)
  - `health_check` -> backend/main.py:34
  - `get_activity_history` -> backend/routers/activity.py:55
  - `send_message` -> backend/routers/chat.py:108

  ## Interface (9)
  - `ActivityDay` -> desk-app/src/store/activitySlice.ts:6
  - `ChatMessage` -> desk-app/src/store/chatSlice.ts:6
  - `TimerSetting` -> desk-app/electron/preload.ts:15

  ## Component (6)
  - `BreakTimer` -> desk-app/src/components/BreakTimer.tsx:8
  - `ChatOverlay` -> desk-app/src/components/ChatOverlay.tsx:12
```

Filtered:
```
find_features(path="C:\\MyProject", type_filter="API Route")

  # Features Found (15)
  Filtered by: `API Route`

  ## API Route (15)
  - `get_activity_history` -> backend/routers/activity.py:55
  - `get_today_activity` -> backend/routers/activity.py:74
  ...
```

**Parameters:**
- `path` — Path to the project or file
- `type_filter` (optional) — Filter by feature type (e.g. `"API Route"`, `"Component"`, `"Test"`)

---

## `get_feature_detail`
Show code context around a detected feature by name. Auto-locates the file and line — no need to know where it lives.
To disambiguate when names collide, append `@filepath:line` to the name (e.g. `"get_user_settings@settings.py"` or `"health_check@main.py:34"`).

```
get_feature_detail(path="C:\\MyProject", name="get_activity_history")

  # Context: `backend/routers/activity.py` at line 55 - `get_activity_history` (API Route)

    45: from datetime import datetime
    46: from typing import Optional
    47: 
    48: router = APIRouter()
    49: 
    50: @router.get("/activity")
    51: async def get_activity_history(
    52:     db: Session = Depends(get_db),
    53:     page: int = Query(1, ge=1),
    54:     limit: int = Query(20, ge=1, le=100),
  -> 55: ) -> ActivityResponse:
    56:     total = await db.count("activity_log")
    57:     items = await db.find("activity_log",
    58:         sort=[("timestamp", -1)],
    59:         skip=(page - 1) * limit,
    60:         limit=limit,
    61:     )
    62:     return ActivityResponse(items=items, total=total, page=page, limit=limit)
```

On multiple matches, shows a numbered list to help narrow down:
```
get_feature_detail(path="C:\\MyProject", name="chat")

  # Multiple matches for 'chat' (3 found)

  1. `ChatMessage` -> desk-app/src/store/chatSlice.ts:6  (Interface)
  2. `ChatSession` -> desk-app/src/store/chatSlice.ts:14  (Interface)
  3. `save_chat_message` -> backend/routers/chat.py:42  (API Route)

  To narrow down, use a more specific name from `find_features` output.
```

**Parameters:**
- `path` — Path to the project
- `name` — Feature name or partial match

---

## `generate_architecture`
Generate a layered architecture diagram as Mermaid. Shows entry points, API routes, services, data models, and import connections between files.

```
generate_architecture(path="C:\\MyProject")

  # Architecture Diagram: MyProject
  **Framework:** FastAPI
  **Type:** None
  **Files:** 47  |  **Features:** 34

  graph TD
      subgraph Entry[Entry Points]
          main_py["main.py"]
          electron_main_ts["main.ts"]
          src_main_tsx["main.tsx"]
      end
      subgraph API[API / Routes]
          subgraph G_routers[routers]
              activity_py["activity.py"]
              chat_py["chat.py"]
              agent_py["agent.py"]
          end
      end
      subgraph Logic[Services / Logic]
          database_py["database.py"]
          auth_py["auth.py"]
      end
      subgraph Data[Data / Models]
          models_py["models.py"]
          schemas_py["schemas.py"]
      end
      subgraph UI[UI / Components]
          subgraph G_components[components]
              BreakTimer_tsx["BreakTimer.tsx"]
              ChatOverlay_tsx["ChatOverlay.tsx"]
          end
          subgraph G_store[store]
              chatSlice_ts["chatSlice.ts"]
              authSlice_ts["authSlice.ts"]
          end
      end

      main_py --> activity_py
      main_py --> database_py
      src_main_tsx --> BreakTimer_tsx
      src_main_tsx --> ChatOverlay_tsx
      ...

  ### Layer Summary
  | Layer | Files | Types |
  |---|---|---|
  | Entry Points | 3 | Entry Point |
  | API / Routes | 5 | API Route, Controller |
  | Services / Logic | 4 | Service, Repository |
  | Data / Models | 2 | Schema, Model |
  | UI / Components | 8 | Component, Redux Slice |
```

**Parameters:**
- `path` — Path to the project

---

## `analyze_dead_code`
Find potentially unused code — functions, classes, and exports that are defined but never referenced by any other file.

```
analyze_dead_code(path="C:\\MyProject")

  # Dead Code Analysis: MyProject

  **Total definitions found:** 139  |  **Potentially unused:** 16
  **Files with dead code:** 8

  ## Unused Definitions

  ### `backend/routers/activity.py` (4)
  - Line 8: `SessionRecord`
  - Line 20: `ActivityResponse`
  - Line 55: `get_activity_history`
  - Line 74: `get_today_activity`

  ### `backend/routers/agent.py` (2)
  - Line 23: `SystemMetrics`
  - Line 244: `execute_recommendation`
  ...

  ---
  > **Note:** This is a heuristic analysis based on cross-referencing definitions
  > across files. Decorator-registered routes (FastAPI, Flask) may appear as false
  > positives. Verify before removing.
```

**How it works (one pass):**
1. Extract all module-level definitions (functions, classes, exports) per language
2. Extract all imported names across the project
3. For each definition, check if it appears in any other file — as an import or any code reference
4. Self-referenced names (>1 occurrence in their own file) are excluded
5. Returns files grouped with line numbers

**Supported languages:** Python, JavaScript, TypeScript, Go, Java, Ruby

**Parameters:**
- `path` — Path to the project

---

## `get_git_info`
Get git intelligence about a repository: branch, remote, commit history, contributors, hot files, and uncommitted changes.

```
get_git_info(path="C:\\MyProject")

  # Git Intelligence: MyProject

  **Branch:** `main`
  **Remote:** `https://github.com/user/MyProject.git`
  **Total commits:** `142`
  **Created:** `2025-11-03 10:15:22 +0530`  |  **Last commit:** `2026-07-05 16:42:18 +0530`
  **Uncommitted changes:** 3

  ## Recent Commits (25)
  - `a1b2c3d4` Alice (2026-07-05)  fix: resolve timeout in data fetch
  - `e5f6g7h8` Bob (2026-07-04)  feat: add user preferences panel
  - `i9j0k1l2` Alice (2026-07-03)  refactor: extract query builder
  ...

  ## Contributors (3)
  - Alice  87 commits
  - Bob    42 commits
  - Carol  13 commits

  ## Hot Files (most frequently changed)
  - `src/api/routes.py`  34 changes
  - `src/components/Chart.tsx`  28 changes
  - `src/store/index.ts`  22 changes

  ## Uncommitted Changes (3)
  - [Modified] `src/api/routes.py`
  - [Staged] `src/components/Chart.tsx`
  - [Untracked] `notes.md`
```

**Parameters:**
- `path` — Path to the git repository

---

## `find_secrets`
Scan the codebase for hardcoded secrets — API keys, tokens, passwords, private keys, and database credentials.

```
find_secrets(path="C:\\MyProject")

  # Secret Scan: MyProject

  **Total findings:** 4  |  **Files with secrets:** 2

  ### Breakdown by Type
  - **OpenAI API Key:** 2
  - **Password in Code:** 1
  - **Database URL with Credentials:** 1

  ## Locations

  ### `backend/.env` (2)
  - Line 3: **OpenAI API Key** - `sk-or-v1-22c646516c30d33341d74...62b3624cb50b5c9ba595159b951`
  - Line 7: **Database URL with Credentials** - `postgres://admin:s3cret@localhost:5432/mydb`

  ### `backend/config.py` (2)
  - Line 12: **Password in Code** - `password = "hunter2"`
  - Line 15: **OpenAI API Key** - `sk-proj-5f8a2e6c3d1b9a4f7e0c...`

  ---
  > **Warning:** Results are heuristic. Verify each finding before acting.
  > Rotate any exposed real credentials immediately. Some findings may be
  > placeholder, example, or test data.
```

**Detectable patterns:**

| Pattern | Example |
|---|---|
| OpenAI API Key | `sk-...` (164 chars) |
| GitHub Token | `ghp_...` · `ghs_...` · `ghu_...` |
| AWS Access Key ID | `AKIA...` · `ASIA...` |
| AWS Secret Key | `aws_secret_access_key = ...` |
| Google API Key | `AIza...` |
| Stripe Live Key | `sk_live_...` · `pk_live_...` |
| Slack Bot Token | `xoxb-...` · `xoxp-...` |
| Discord Bot Token | `24chars.6chars.27chars` |
| JWT Token | `eyJ...` |
| SSH Private Key | `-----BEGIN RSA PRIVATE KEY-----` |
| Password in Code | `password = "..."` |
| API Key / Secret | `api_key = "..."` |
| Database URL | `postgres://user:pass@host/db` |
| Heroku API Key | `heroku...` |
| GitLab Token | `glpat-...` |
| npm Token | `npm_...` |

Skips files containing `example`, `placeholder`, `your_key`, `changeme`, `TODO`, `FIXME`, `dummy`, `test_key`, or `fake` to reduce false positives.

**Parameters:**
- `path` — Path to the project

---

## `search_symbols`
Search across all source files using regex. Optionally filter by file extension.

```
search_symbols(path="C:\\MyProject", pattern="async def")

  # Search Results for `async def` (12 matches)

  - `backend/main.py:14`  async def health_check():
  - `backend/routers/chat.py:42`  async def send_message():
  - `backend/routers/activity.py:55`  async def get_activity_history():
  - `backend/database.py:66`  async def query():
  ...

search_symbols(path="C:\\MyProject", pattern="todo:", file_ext="py,ts")

  # Search Results for `todo:` (5 matches)

  - `backend/routers/agent.py:102`  # TODO: add validation
  - `backend/database.py:201`  # TODO: implement caching
  - `desk-app/src/store/chatSlice.ts:44`  // TODO: add error handling
  ...
```

**Parameters:**
- `path` — Path to the project
- `pattern` — Regex pattern
- `file_ext` (optional) — Comma-separated extensions (e.g. `"py,js,ts"`)


