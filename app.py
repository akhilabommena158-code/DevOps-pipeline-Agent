from flask import Flask, render_template, request, jsonify
from pathlib import Path
import yaml

app = Flask(__name__)
BASE_DIR = Path(__file__).resolve().parent.parent


def detect_project(project_path: str):
    """Analyze a local project folder and return simple DevOps findings."""
    requested = (project_path or "").strip()

    if requested:
        path = Path(requested).expanduser().resolve()
    else:
        path = BASE_DIR

    if not path.exists() or not path.is_dir():
        return {"error": f"Project folder not found: {path}"}

    # Avoid scanning virtual environments and other generated directories.
    ignored = {".git", "venv", ".venv", "node_modules", "__pycache__", ".idea", ".vscode"}
    files = []
    for p in path.rglob("*"):
        if p.is_file() and not any(part in ignored for part in p.parts):
            files.append(p)

    names = {p.name.lower() for p in files}
    suffixes = {p.suffix.lower() for p in files}

    language = "Unknown"
    framework = "Not detected"
    dependency_file = "None"
    test_detected = False
    docker_detected = "dockerfile" in names
    package_manager = "Not detected"

    if "requirements.txt" in names or "pyproject.toml" in names or ".py" in suffixes:
        language = "Python"
        if "requirements.txt" in names:
            dependency_file = "requirements.txt"
            package_manager = "pip"
        elif "pyproject.toml" in names:
            dependency_file = "pyproject.toml"
            package_manager = "pip/pyproject"
        if any(p.name.endswith(".py") and ("test" in p.name.lower()) for p in files) or any(
            part.lower() in {"test", "tests"} for p in files for part in p.parts
        ):
            test_detected = True
        # Lightweight framework detection from common dependency/source names.
        text_names = " ".join(p.name.lower() for p in files)
        if "manage.py" in names:
            framework = "Django"
        elif "app.py" in names or "flask" in text_names:
            framework = "Flask"

    elif "package.json" in names:
        language = "JavaScript / Node.js"
        dependency_file = "package.json"
        package_manager = "npm"
        test_detected = any(
            ("test" in p.name.lower() or "spec" in p.name.lower())
            for p in files
        )
        text_names = " ".join(p.name.lower() for p in files)
        if "vite.config.js" in names or "vite.config.ts" in names:
            framework = "Vite"
        elif "next.config.js" in names or "next.config.mjs" in names:
            framework = "Next.js"
        elif "react" in text_names:
            framework = "React"

    elif "pom.xml" in names or ".java" in suffixes:
        language = "Java"
        if "pom.xml" in names:
            dependency_file = "pom.xml"
            package_manager = "Maven"
        elif "build.gradle" in names or "build.gradle.kts" in names:
            dependency_file = "build.gradle / build.gradle.kts"
            package_manager = "Gradle"
        test_detected = any("test" in p.name.lower() for p in files)
        framework = "Spring Boot" if "application.properties" in names or "application.yml" in names else "Java"

    elif ".js" in suffixes or ".ts" in suffixes:
        language = "JavaScript / TypeScript"
        package_manager = "npm" if "package-lock.json" in names else "Not detected"

    if language == "Python":
        test_command = "pytest" if test_detected else "python -m compileall ."
        build_command = "python -m compileall ."
    elif language.startswith("JavaScript"):
        test_command = "npm test" if test_detected else "npm test"
        build_command = "npm run build"
    elif language == "Java":
        test_command = "mvn test" if package_manager == "Maven" else "gradle test"
        build_command = "mvn package -DskipTests" if package_manager == "Maven" else "gradle build -x test"
    else:
        test_command = "Add a test command"
        build_command = "Add a build command"

    recommendations = []
    if dependency_file == "None":
        recommendations.append("Add a dependency/lock file so builds are reproducible.")
    else:
        recommendations.append(f"Dependency file detected: {dependency_file}.")
    if test_detected:
        recommendations.append("Tests appear to be present; run them in CI before deployment.")
    else:
        recommendations.append("No obvious test files were detected; add automated tests.")
    if docker_detected:
        recommendations.append("Dockerfile detected; container build can be added to the pipeline.")
    else:
        recommendations.append("No Dockerfile detected; add one if containerized deployment is required.")

    return {
        "project_path": str(path),
        "file_count": len(files),
        "language": language,
        "framework": framework,
        "dependency_file": dependency_file,
        "package_manager": package_manager,
        "tests_detected": test_detected,
        "docker_detected": docker_detected,
        "recommended_test_command": test_command,
        "recommended_build_command": build_command,
        "recommendations": recommendations,
        "sample_files": [str(p.relative_to(path)) for p in files[:30]],
    }


@app.route("/")
def index():
    return render_template("index.html")


@app.post("/api/analyze")
def analyze():
    data = request.get_json(silent=True) or {}
    result = detect_project(data.get("project_path", ""))
    if "error" in result:
        return jsonify({"success": False, "error": result["error"]}), 400
    return jsonify({"success": True, "analysis": result})


@app.post("/api/generate")
def generate_pipeline():
    data = request.get_json(silent=True) or {}

    project_name = (data.get("project_name") or "my-project").strip()
    language = (data.get("language") or "python").lower()
    test_command = (data.get("test_command") or "").strip()
    build_command = (data.get("build_command") or "").strip()
    deploy_target = (data.get("deploy_target") or "none").lower()

    if not test_command:
        test_command = {
            "python": "pytest",
            "javascript": "npm test",
            "java": "mvn test",
            "node": "npm test",
        }.get(language, "echo \"No test command configured\"")

    if not build_command:
        build_command = {
            "python": "python -m compileall .",
            "javascript": "npm run build",
            "java": "mvn package -DskipTests",
            "node": "npm run build",
        }.get(language, "echo \"No build command configured\"")

    steps = [{"name": "Checkout", "uses": "actions/checkout@v4"}]

    if language == "python":
        steps += [
            {"name": "Set up Python", "uses": "actions/setup-python@v5",
             "with": {"python-version": "3.12"}},
            {"name": "Install dependencies",
             "run": "python -m pip install --upgrade pip && if [ -f requirements.txt ]; then pip install -r requirements.txt; fi"},
        ]
    elif language in ("javascript", "node"):
        steps += [
            {"name": "Set up Node.js", "uses": "actions/setup-node@v4",
             "with": {"node-version": "20"}},
            {"name": "Install dependencies", "run": "npm ci"},
        ]
    elif language == "java":
        steps += [
            {"name": "Set up Java", "uses": "actions/setup-java@v4",
             "with": {"distribution": "temurin", "java-version": "21", "cache": "maven"}},
        ]

    steps += [
        {"name": "Run tests", "run": test_command},
        {"name": "Build", "run": build_command},
    ]

    if deploy_target == "docker":
        safe_name = "".join(c if c.isalnum() or c in "-_" else "-" for c in project_name).lower()
        steps.append({"name": "Build Docker image", "run": f"docker build -t {safe_name}:latest ."})

    workflow = {
        "name": f"{project_name} CI/CD",
        "on": {"push": {"branches": ["main"]}, "pull_request": {"branches": ["main"]}},
        "jobs": {"build-test": {"runs-on": "ubuntu-latest", "steps": steps}},
    }

    return jsonify({
        "success": True,
        "workflow": yaml.safe_dump(workflow, sort_keys=False, default_flow_style=False),
        "analysis": {
            "project_name": project_name,
            "language": language,
            "test_command": test_command,
            "build_command": build_command,
            "deploy_target": deploy_target,
        },
    })


@app.get("/api/health")
def health():
    return jsonify({"status": "ok", "service": "DevOps Pipeline Agent"})


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
