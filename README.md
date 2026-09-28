# DevOps Pipeline Agent - Agent Version

This version extends the working Flask app with local project analysis.

## Run

If your existing venv is already created, from the project root:

```powershell
.\venv\Scripts\python.exe -m pip install -r backend\requirements.txt
.\venv\Scripts\python.exe backend\app.py
```

Open:

http://127.0.0.1:5000

## New functionality

1. Enter a local project folder path, or leave it empty.
2. Click Analyze Project.
3. The agent scans the project and detects:
   - language
   - common framework
   - dependency file
   - package manager
   - tests
   - Dockerfile
4. It gives basic DevOps recommendations.
5. It fills recommended test/build commands.
6. Generate Pipeline creates the YAML workflow.

No GitHub connection is required for this version.
