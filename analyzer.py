from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

IGNORE_DIRS = {
    "node_modules", ".git", "__pycache__", "venv", ".venv",
    ".tox", ".eggs", "dist", "build", ".next", ".nuxt",
    "target", "bin", "obj", "vendor", ".bundle", ".svn",
    ".hg", ".idea", ".vscode", "coverage", ".pytest_cache",
    "mypy_cache", ".ruff_cache", ".yarn", ".turbo",
    "lib", "Lib", "site-packages",
}

IGNORE_EXTENSIONS = {
    ".pyc", ".pyo", ".so", ".dll", ".dylib", ".class",
    ".o", ".a", ".lib", ".obj", ".ilk", ".pdb",
    ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".ico",
    ".svg", ".woff", ".woff2", ".ttf", ".eot",
    ".zip", ".tar", ".gz", ".bz2", ".7z", ".rar",
    ".exe", ".msi", ".deb", ".rpm",
    ".pdf", ".doc", ".docx", ".xls", ".xlsx",
    ".mp3", ".mp4", ".avi", ".mov",
    ".min.js", ".min.css",
    ".map", ".lock",
}

MAX_FILE_SIZE = 1024 * 512  # 512KB


@dataclass
class ProjectInfo:
    name: str
    root: str
    languages: dict[str, int] = field(default_factory=dict)
    framework: str | None = None
    entry_points: list[dict[str, str]] = field(default_factory=list)
    file_count: int = 0
    dir_count: int = 0
    structure: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class Feature:
    name: str
    type: str
    location: str
    line: int
    description: str
    related_files: list[str] = field(default_factory=list)


FRAMEWORK_PATTERNS: list[tuple[str, list[str]]] = [
    ("FastAPI", ["fastapi"]),
    ("Flask", ["flask"]),
    ("Django", ["django"]),
    ("Express.js", ["express"]),
    ("Next.js", ["next"]),
    ("React", ["react", "react-dom"]),
    ("Vue", ["vue"]),
    ("Angular", ["@angular/core"]),
    ("Spring Boot", ["spring-boot-starter-web"]),
    ("Rails", ["rails"]),
    ("Laravel", ["laravel/framework"]),
    ("ASP.NET Core", ["microsoft.aspnetcore"]),
    ("Gin", ["gin-gonic/gin"]),
]

FEATURE_PATTERNS: dict[str, list[tuple[str, str, str]]] = {
    "py": [
        (r"@(?:app|router|api)\.(?:get|post|put|delete|patch)\(", "API Route", "fastapi/flask route"),
        (r"@route\(", "API Route", "flask route"),
        (r"def\s+(get|post|put|delete|patch)_?\w*\(self", "API Endpoint", "ViewSet endpoint"),
        (r"class\s+\w+\(.*APIView.*\)", "API View", "Django REST view"),
        (r"class\s+\w+\(.*ViewSet.*\)", "ViewSet", "Django ViewSet"),
        (r"class\s+\w+\(.*ModelViewSet.*\)", "Model ViewSet", "Django ModelViewSet"),
        (r"class\s+\w+\(.*GenericViewSet.*\)", "Generic ViewSet", "Django GenericViewSet"),
        (r"class\s+\w+\(.*Serializer.*\)", "Serializer", "serializer definition"),
        (r"class\s+\w+\(.*ModelSerializer.*\)", "Model Serializer", "model serializer"),
        (r"class\s+\w+\(.*Admin.*\)", "Admin", "Django admin config"),
        (r"@\w+\.task\(", "Celery Task", "async task"),
        (r"def\s+\w+\(.*BackgroundTasks.*\)", "Background Task", "FastAPI background task"),
        (r"router\.include_router\(", "Router Include", "route mounting"),
        (r"\.add_url_rule\(", "URL Rule", "flask route"),
        (r"@pytest\.", "Test", "pytest test"),
        (r"class\s+\w+\(.*TestCase.*\)", "Test Case", "unittest test case"),
        (r"class\s+\w+\(.*unittest\.TestCase.*\)", "Test Case", "unittest test case"),
    ],
    "js": [
        (r"router\.(get|post|put|delete|patch|all)\(", "API Route", "express route"),
        (r"app\.(get|post|put|delete|patch|all)\(", "API Route", "express route"),
        (r"export\s+(default\s+)?function\s+\w+", "Exported Function", "module export"),
        (r"export\s+(default\s+)?class\s+\w+", "Exported Class", "module export"),
        (r"function\s+\w+\(req,\s*res", "Request Handler", "express handler"),
        (r"@(?:Get|Post|Put|Delete|Patch)\(['\"]", "API Endpoint", "NestJS/TS route"),
        (r"class\s+\w+Controller", "Controller", "controller class"),
        (r"class\s+\w+Service", "Service", "service class"),
        (r"class\s+\w+Repository", "Repository", "repository class"),
        (r"describe\(['\"]", "Test Suite", "test suite"),
        (r"it\(['\"]", "Test", "test case"),
        (r"test\(['\"]", "Test", "test case"),
        (r"useEffect\(", "React Effect", "react hook"),
        (r"useState\(", "React State", "react hook"),
        (r"useContext\(", "React Context", "react hook"),
        (r"createContext\(", "React Context", "react context definition"),
        (r"createSlice\(", "Redux Slice", "redux slice"),
        (r"createApi\(", "RTK Query API", "redux toolkit query"),
        (r"export\s+default\s+function\s+\w+", "Component", "react component"),
        (r"export\s+default\s+class\s+\w+", "Component", "react class component"),
    ],
    "ts": [
        (r"@(?:Get|Post|Put|Delete|Patch)\(['\"]", "API Endpoint", "decorated route"),
        (r"class\s+\w+Controller", "Controller", "controller class"),
        (r"class\s+\w+Service", "Service", "service class"),
        (r"class\s+\w+Repository", "Repository", "repository class"),
        (r"class\s+\w+Component", "Component", "angular component"),
        (r"@Component\(", "Angular Component", "angular component decorator"),
        (r"@Injectable\(", "Injectable", "angular service"),
        (r"@NgModule\(", "NgModule", "angular module"),
        (r"interface\s+\w+", "Interface", "type interface"),
        (r"type\s+\w+\s*=", "Type Alias", "type definition"),
        (r"describe\(['\"]", "Test Suite", "test suite"),
        (r"it\(['\"]", "Test", "test case"),
        (r"test\(['\"]", "Test", "test case"),
        (r"export\s+default\s+(function|const)\s+\w+", "Component", "react component"),
        (r"PrismaClient", "Database Client", "prisma usage"),
        (r"z\.object\(", "Zod Schema", "validation schema"),
        (r"app\.(get|post|put|delete|patch)\(", "API Route", "express route"),
        (r"router\.(get|post|put|delete|patch)\(", "API Route", "express route"),
    ],
    "java": [
        (r"@(GetMapping|PostMapping|PutMapping|DeleteMapping|RequestMapping)\(", "API Endpoint", "spring route"),
        (r"@RestController", "REST Controller", "spring rest controller"),
        (r"@Controller", "Controller", "spring controller"),
        (r"@Service", "Service", "spring service"),
        (r"@Repository", "Repository", "spring repository"),
        (r"@Component", "Component", "spring component"),
        (r"@Entity", "Entity", "JPA entity"),
        (r"class\s+\w+Controller", "Controller", "controller class"),
        (r"class\s+\w+Service", "Service", "service class"),
        (r"class\s+\w+Repository", "Repository", "repository class"),
        (r"@Test", "Test", "junit test"),
    ],
    "go": [
        (r"func\s+\w+\(.*\)\s*error\s*\{", "Error Return Function", "go function"),
        (r"func\s+\w+Handler", "Handler", "http handler"),
        (r"router\.(GET|POST|PUT|DELETE|PATCH)\(", "API Route", "gin route"),
        (r"r\.(GET|POST|PUT|DELETE|PATCH)\(", "API Route", "gin route"),
        (r"mux\.NewRouter\(\)", "Router", "gorilla mux"),
        (r"http\.Handle(Func)?\(", "HTTP Handler", "net/http handler"),
        (r"type\s+\w+Server\s+struct", "Server Struct", "server definition"),
        (r"type\s+\w+Service\s+struct", "Service Struct", "service definition"),
        (r"type\s+\w+Repository\s+struct", "Repository Struct", "repository definition"),
        (r"func\s+Test\w+\(.*testing\.\*T", "Test", "go test"),
    ],
    "rb": [
        (r"class\s+\w+Controller", "Controller", "rails controller"),
        (r"class\s+\w+Service", "Service", "rails service"),
        (r"class\s+\w+Model", "Model", "rails model"),
        (r"get\s+['\"]\w+['\"]", "Route", "rails route"),
        (r"post\s+['\"]\w+['\"]", "Route", "rails route"),
        (r"put\s+['\"]\w+['\"]", "Route", "rails route"),
        (r"delete\s+['\"]\w+['\"]", "Route", "rails route"),
        (r"resources\s+:\w+", "Resource", "rails resource"),
        (r"namespace\s+:\w+", "Namespace", "rails namespace"),
        (r"RSpec\.describe\s+", "Test", "rspec test"),
        (r"describe\s+['\"]", "Test", "rspec test"),
    ],
    "cs": [
        (r"\[ApiController\]", "API Controller", "ASP.NET controller"),
        (r"\[Route\(", "Route", "ASP.NET route"),
        (r"\[HttpGet\(", "API Endpoint", "ASP.NET GET"),
        (r"\[HttpPost\(", "API Endpoint", "ASP.NET POST"),
        (r"\[HttpPut\(", "API Endpoint", "ASP.NET PUT"),
        (r"\[HttpDelete\(", "API Endpoint", "ASP.NET DELETE"),
        (r"class\s+\w+Controller\s*:", "Controller", "controller class"),
        (r"class\s+\w+Service\s*:", "Service", "service class"),
        (r"interface\s+I\w+Service", "Service Interface", "service interface"),
        (r"interface\s+I\w+Repository", "Repository Interface", "repository interface"),
    ],
}

LANGUAGE_EXTENSIONS = {
    ".py": "Python",
    ".js": "JavaScript",
    ".jsx": "JavaScript (React)",
    ".ts": "TypeScript",
    ".tsx": "TypeScript (React)",
    ".java": "Java",
    ".go": "Go",
    ".rb": "Ruby",
    ".cs": "C#",
    ".php": "PHP",
    ".swift": "Swift",
    ".kt": "Kotlin",
    ".rs": "Rust",
    ".cpp": "C++",
    ".c": "C",
    ".h": "C/C++ Header",
    ".hpp": "C++ Header",
    ".scala": "Scala",
    ".vue": "Vue",
    ".svelte": "Svelte",
    ".html": "HTML",
    ".css": "CSS",
    ".scss": "SCSS",
    ".sql": "SQL",
    ".yaml": "YAML",
    ".yml": "YAML",
    ".json": "JSON",
    ".xml": "XML",
    ".md": "Markdown",
    ".toml": "TOML",
}


def should_ignore(entry: Path, root: Path) -> bool:
    relative = entry.relative_to(root).as_posix()
    parts = relative.split("/")
    for part in parts:
        if part in IGNORE_DIRS:
            return True
        if part.startswith("."):
            return True
    if entry.is_file():
        ext = entry.suffix.lower()
        if ext in IGNORE_EXTENSIONS:
            return True
        if entry.stat().st_size > MAX_FILE_SIZE:
            return True
    return False


def detect_project_type(root: Path) -> str | None:
    files = {f.name for f in root.iterdir() if f.is_file()}
    if "manage.py" in files:
        return "Django"
    if "app.py" in files or "application.py" in files:
        _check = list(root.glob("**/app.py")) + list(root.glob("**/application.py"))
        for f in _check:
            try:
                content = f.read_text(encoding="utf-8", errors="ignore")
                if "Flask" in content:
                    return "Flask"
                if "FastAPI" in content:
                    return "FastAPI"
            except Exception:
                pass
    if "next.config.js" in files or "next.config.ts" in files:
        return "Next.js"
    if "package.json" in files:
        return "Node.js (generic)"
    if "pom.xml" in files:
        return "Maven"
    if "build.gradle" in files or "build.gradle.kts" in files:
        return "Gradle"
    if "Cargo.toml" in files:
        return "Rust"
    if "go.mod" in files:
        return "Go"
    if "Gemfile" in files:
        return "Ruby"
    if "composer.json" in files:
        return "PHP"
    try:
        for f in root.iterdir():
            if f.suffix == ".sln" or f.suffix == ".csproj":
                return ".NET"
    except Exception:
        pass
    return None


def detect_framework(root: Path) -> str | None:
    files: list[Path] = []
    try:
        if (root / "pyproject.toml").exists():
            files.append(root / "pyproject.toml")
        if (root / "requirements.txt").exists():
            files.append(root / "requirements.txt")
        if (root / "Pipfile").exists():
            files.append(root / "Pipfile")
        if (root / "package.json").exists():
            files.append(root / "package.json")
        if (root / "Cargo.toml").exists():
            files.append(root / "Cargo.toml")
        if (root / "go.mod").exists():
            files.append(root / "go.mod")
        if (root / "Gemfile").exists():
            files.append(root / "Gemfile")
        if (root / "pom.xml").exists():
            files.append(root / "pom.xml")
        if (root / "build.gradle").exists():
            files.append(root / "build.gradle")
    except Exception:
        pass

    for f in files:
        try:
            content = f.read_text(encoding="utf-8", errors="ignore").lower()
            for name, patterns in FRAMEWORK_PATTERNS:
                for pat in patterns:
                    if pat.lower() in content:
                        return name
        except Exception:
            continue
    return None


def map_structure(root: Path, max_depth: int = 4) -> list[dict[str, Any]]:
    """Map directory tree up to max_depth."""

    def _walk(dirpath: Path, depth: int) -> list[dict[str, Any]]:
        if depth > max_depth:
            return [{"name": "...", "type": "truncated"}]
        entries: list[dict[str, Any]] = []
        try:
            children = sorted(dirpath.iterdir(), key=lambda x: (x.is_file(), x.name.lower()))
        except PermissionError:
            return [{"name": "(no permission)", "type": "error"}]

        for child in children:
            if should_ignore(child, root):
                continue
            if child.is_dir():
                sub = _walk(child, depth + 1)
                entries.append({
                    "name": child.name,
                    "type": "directory",
                    "children": sub,
                })
            else:
                entries.append({
                    "name": child.name,
                    "type": "file",
                    "ext": child.suffix.lower(),
                    "size": child.stat().st_size,
                })
        return entries

    return _walk(root, 0)


def collect_source_files(root: Path) -> list[Path]:
    result: list[Path] = []
    try:
        for entry in root.rglob("*"):
            if entry.is_file() and not should_ignore(entry, root):
                ext = entry.suffix.lower()
                if ext in LANGUAGE_EXTENSIONS and ext not in IGNORE_EXTENSIONS:
                    result.append(entry)
    except PermissionError:
        pass
    return result


def detect_languages(files: list[Path]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for f in files:
        ext = f.suffix.lower()
        lang = LANGUAGE_EXTENSIONS.get(ext, ext)
        counts[lang] = counts.get(lang, 0) + 1
    return dict(sorted(counts.items(), key=lambda x: -x[1]))


def find_entry_points(root: Path) -> list[dict[str, str]]:
    entry_points: list[dict[str, str]] = []
    common_entry_names = {
        "main.py", "app.py", "application.py", "manage.py", "wsgi.py",
        "asgi.py", "index.js", "index.ts", "server.js", "server.ts",
        "app.js", "app.ts", "main.js", "main.ts", "main.go",
        "main.rs", "main.java", "Program.cs", "index.html",
    }
    for f in root.rglob("*"):
        if f.is_file() and f.name in common_entry_names and not should_ignore(f, root):
            relative = f.relative_to(root).as_posix()
            entry_points.append({
                "file": relative,
                "type": "entry point",
            })
    return entry_points


async def find_features(root: Path, source_files: list[Path]) -> list[Feature]:
    features: list[Feature] = []
    for filepath in source_files:
        ext = filepath.suffix.lower().lstrip(".")
        patterns = FEATURE_PATTERNS.get(ext) or FEATURE_PATTERNS.get(
            filepath.suffix.lower().lstrip(".").replace("x", "").replace("c", "s")
        )
        if ext == "jsx":
            patterns = FEATURE_PATTERNS.get("js")
        elif ext == "tsx":
            patterns = FEATURE_PATTERNS.get("ts")

        if not patterns:
            continue

        try:
            content = filepath.read_text(encoding="utf-8", errors="ignore")
            lines = content.split("\n")
        except Exception:
            continue

        relative = filepath.relative_to(root).as_posix()

        for pattern, feature_type, description in patterns:
            for match in re.finditer(pattern, content, re.MULTILINE):
                line_num = content[: match.start()].count("\n") + 1
                features.append(Feature(
                    name=match.group(0).strip()[:80],
                    type=feature_type,
                    location=relative,
                    line=line_num,
                    description=description,
                ))
    return features


async def search_codebase(
    root: Path,
    pattern: str,
    include_ext: list[str] | None = None,
    max_results: int = 50,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    source_files = collect_source_files(root)
    try:
        regex = re.compile(pattern, re.IGNORECASE)
    except re.error:
        return [{"error": f"Invalid regex: {pattern}"}]

    for filepath in source_files:
        if include_ext:
            if filepath.suffix.lower() not in include_ext and f".{include_ext}" not in str(filepath.suffix):
                continue
        try:
            content = filepath.read_text(encoding="utf-8", errors="ignore")
            lines = content.split("\n")
            for i, line in enumerate(lines, 1):
                if regex.search(line):
                    results.append({
                        "file": filepath.relative_to(root).as_posix(),
                        "line": i,
                        "content": line.strip()[:200],
                    })
                    if len(results) >= max_results:
                        return results
        except Exception:
            continue

    return results


async def analyze_codebase(root_path: str, max_depth: int = 4) -> dict[str, Any]:
    root = Path(root_path).resolve()
    if not root.is_dir():
        return {"error": f"Directory not found: {root_path}"}

    source_files = collect_source_files(root)
    project_type = detect_project_type(root)
    framework = detect_framework(root)
    languages = detect_languages(source_files)
    entry_points = find_entry_points(root)
    structure = map_structure(root, max_depth)
    features = await find_features(root, source_files)

    total_lines = 0
    for f in source_files:
        try:
            total_lines += sum(1 for _ in f.open("rb"))
        except Exception:
            pass

    return {
        "projectName": root.name,
        "projectPath": str(root),
        "projectType": project_type,
        "framework": framework,
        "languages": languages,
        "fileCount": len(source_files),
        "totalLines": total_lines,
        "entryPoints": entry_points,
        "features": [
            {
                "name": f.name,
                "type": f.type,
                "location": f.location,
                "line": f.line,
                "description": f.description,
            }
            for f in features
        ],
        "structure": structure,
    }


LAYER_MAP = {
    "API Route": "API", "API Endpoint": "API", "API View": "API",
    "ViewSet": "API", "Model ViewSet": "API", "Generic ViewSet": "API",
    "Controller": "API", "REST Controller": "API",
    "Router": "API", "Router Include": "API",
    "URL Rule": "API",
    "Service": "Logic", "Celery Task": "Logic", "Background Task": "Logic",
    "Handler": "Logic", "Request Handler": "Logic",
    "Injectable": "Logic",
    "Repository": "Data", "Serializer": "Data", "Model Serializer": "Data",
    "Entity": "Data", "Database Client": "Data",
    "Component": "UI", "Angular Component": "UI", "React Component": "UI",
    "React State": "UI", "React Effect": "UI", "React Context": "UI",
    "NgModule": "Config",
}

CODE_EXTENSIONS = {".py", ".js", ".jsx", ".ts", ".tsx", ".go", ".rs", ".java", ".rb", ".cs", ".php", ".swift", ".kt"}

LAYER_COLORS = {
    "Entry": "#e1f5fe",
    "API": "#e8f5e9",
    "Logic": "#fff3e0",
    "Data": "#fce4ec",
    "UI": "#f3e5f5",
    "Config": "#f5f5f5",
}

IMPORT_PATTERNS = re.compile(
    r'(?:from\s+([.\w]+)\s+import|import\s+[\'"]([^"\']+)[\'"]|require\([\'"]([^"\']+)[\'"]\)|from\s+[\'"]([^"\']+)[\'"]\s+import)',
    re.MULTILINE,
)


def _match_import(imported: str, source_files: list[Path], root: Path) -> str | None:
    normalized = imported.replace(".", "/")
    for sf in source_files:
        sf_rel = sf.relative_to(root).as_posix()
        sf_stem = sf_rel.rsplit(".", 1)[0] if "." in sf_rel else sf_rel
        if normalized == sf_stem or normalized == sf_rel or sf_stem.endswith("/" + normalized):
            return sf_rel
        if normalized + "/__init__" in sf_stem:
            return sf_rel
    return None


async def generate_architecture_diagram(root_path: str) -> dict[str, Any]:
    root = Path(root_path).resolve()
    if not root.is_dir():
        return {"error": f"Directory not found: {root_path}"}

    info = await analyze_codebase(root_path)
    if "error" in info:
        return info

    features: list[dict] = info["features"]
    entry_points: list[dict] = info["entryPoints"]

    layers: dict[str, dict] = {
        "Entry": {"label": "Entry Points", "nodes": {}, "color": LAYER_COLORS["Entry"]},
        "API": {"label": "API / Routes", "nodes": {}, "color": LAYER_COLORS["API"]},
        "Logic": {"label": "Services / Logic", "nodes": {}, "color": LAYER_COLORS["Logic"]},
        "Data": {"label": "Data / Models", "nodes": {}, "color": LAYER_COLORS["Data"]},
        "UI": {"label": "UI / Components", "nodes": {}, "color": LAYER_COLORS["UI"]},
        "Config": {"label": "Config", "nodes": {}, "color": LAYER_COLORS["Config"]},
    }

    def node_id(file: str) -> str:
        return file.replace("/", "_").replace(".", "_").replace("-", "_")

    PATH_LAYER_OVERRIDES = {
        "database": "Data", "models": "Data", "model": "Data",
        "repository": "Data", "repositories": "Data",
        "entity": "Data", "schema": "Data", "schemas": "Data",
        "migration": "Data", "migrations": "Data",
        "auth": "Logic", "middleware": "Logic", "middlewares": "Logic",
        "service": "Logic", "services": "Logic", "utils": "Logic", "util": "Logic",
        "helper": "Logic", "helpers": "Logic", "lib": "Logic",
        "component": "UI", "components": "UI",
        "page": "UI", "pages": "UI", "screen": "UI", "screens": "UI",
        "layout": "UI", "layouts": "UI", "widget": "UI", "widgets": "UI",
        "config": "Config", "configuration": "Config",
        "constant": "Config", "constants": "Config",
    }

    def path_to_layer(filepath: str) -> str | None:
        parts = filepath.replace("\\", "/").lower().split("/")
        for part in parts:
            stem = part.split(".")[0]
            if stem in PATH_LAYER_OVERRIDES:
                return PATH_LAYER_OVERRIDES[stem]
        return None

    all_nodes: dict[str, dict] = {}
    ep_files = {ep["file"] for ep in entry_points}

    for ep in entry_points:
        nid = node_id(ep["file"])
        all_nodes[nid] = {
            "label": ep["file"].split("/")[-1],
            "file": ep["file"],
            "types": ["Entry Point"],
            "layer": "Entry",
        }

    for f in features:
        nid = node_id(f["location"])
        if nid in all_nodes:
            if f["type"] not in all_nodes[nid]["types"]:
                all_nodes[nid]["types"].append(f["type"])
            continue
        path_layer = path_to_layer(f["location"])
        layer = path_layer or LAYER_MAP.get(f["type"], "Logic")
        all_nodes[nid] = {
            "label": f["location"].split("/")[-1],
            "file": f["location"],
            "types": [f["type"]],
            "layer": layer,
        }

    source_files = collect_source_files(root)

    connections: list[tuple[str, str]] = []
    for filepath in source_files:
        try:
            content = filepath.read_text(encoding="utf-8", errors="ignore")
            relative = filepath.relative_to(root).as_posix()
        except Exception:
            continue
        for match in IMPORT_PATTERNS.finditer(content):
            imported = next(g for g in match.groups() if g)
            if not imported:
                continue
            target = _match_import(imported, source_files, root)
            if target and target != relative:
                connections.append((relative, target))

    for nid, node in all_nodes.items():
        layers[node["layer"]]["nodes"][nid] = node

    connected_files = set()
    for f, t in connections:
        connected_files.add(f)
        connected_files.add(t)

    for sf in source_files:
        relative = sf.relative_to(root).as_posix()
        nid = node_id(relative)
        if nid in all_nodes:
            continue
        if relative not in connected_files:
            continue
        if sf.suffix.lower() not in CODE_EXTENSIONS:
            continue
        path_layer = path_to_layer(relative) or "Logic"
        layers[path_layer]["nodes"][nid] = {
            "label": relative.split("/")[-1],
            "file": relative,
            "types": [],
        }

    seen_conns: set[tuple[str, str]] = set()
    unique_conns: list[tuple[str, str]] = []
    for f, t in connections:
        key = (f, t)
        if key not in seen_conns:
            seen_conns.add(key)
            unique_conns.append(key)

    def dir_group(entries: dict) -> dict[str, list]:
        groups: dict[str, list] = {}
        for nid, node in entries.items():
            parts = node["file"].split("/")
            group = "/".join(parts[:-1]) if len(parts) > 1 else "/"
            groups.setdefault(group, []).append((nid, node))
        return groups

    def escape_mermaid(text: str) -> str:
        return text.replace('"', "#quot;").replace("[", "(").replace("]", ")")

    md_lines = []
    md_lines.append(f"# Architecture Diagram: {info['projectName']}")
    md_lines.append("")
    if info["framework"]:
        md_lines.append(f"**Framework:** {info['framework']}")
    if info["projectType"]:
        md_lines.append(f"**Type:** {info['projectType']}")
    md_lines.append(f"**Files:** {info['fileCount']}  |  **Features:** {len(features)}")
    md_lines.append("")
    md_lines.append("```mermaid")
    md_lines.append("graph TD")

    for layer_key, layer in layers.items():
        nodes = layer["nodes"]
        if not nodes:
            continue
        md_lines.append(f"    subgraph {layer_key}[{layer['label']}]")
        groups = dir_group(nodes)
        for group_name, group_nodes in sorted(groups.items()):
            if len(group_nodes) > 1 and group_name != "/":
                md_lines.append(f"        subgraph G_{node_id(group_name)}[{escape_mermaid(group_name)}]")
                for nid, node in sorted(group_nodes, key=lambda x: x[1]["label"]):
                    label = escape_mermaid(node["label"])
                    md_lines.append(f"            {nid}[\"{label}\"]")
                md_lines.append("        end")
            else:
                for nid, node in sorted(group_nodes, key=lambda x: x[1]["label"]):
                    label = escape_mermaid(node["label"])
                    md_lines.append(f"        {nid}[\"{label}\"]")
        md_lines.append("    end")

    if unique_conns:
        for f, t in unique_conns[:40]:
            f_id = node_id(f)
            t_id = node_id(t)
            md_lines.append(f"    {f_id} --> {t_id}")

    md_lines.append("```")
    md_lines.append("")
    md_lines.append("### Layer Summary")
    md_lines.append("")
    md_lines.append("| Layer | Files | Types |")
    md_lines.append("|---|---|---|")
    for layer_key in ["Entry", "API", "Logic", "Data", "UI", "Config"]:
        layer = layers[layer_key]
        if layer["nodes"]:
            all_types = sorted(set(t for n in layer["nodes"].values() for t in n["types"]))
            md_lines.append(f"| {layer['label']} | {len(layer['nodes'])} | {', '.join(all_types[:5])} |")

    return {
        "projectName": info["projectName"],
        "projectPath": str(info.get("projectPath", str(root))),
        "projectType": info["projectType"],
        "framework": info["framework"],
        "layers": {k: len(v["nodes"]) for k, v in layers.items() if v["nodes"]},
        "connections": len(unique_conns),
        "diagram": "\n".join(md_lines),
    }
