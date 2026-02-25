# DevReplicator

> Instantly replicate any GitHub repository as a Docker dev environment.

---

## What It Does

DevReplicator clones a GitHub repository, detects its project type (Python, Node.js, Java), generates a production-ready Dockerfile, builds a Docker image, and runs the container — all with a single command.

---

## Requirements

| Dependency | Version   |
|------------|-----------|
| Python     | 3.8+      |
| Git        | Any       |
| Docker     | Installed & running |

No external Python packages required.

---

## Installation

```bash
git clone https://github.com/yourusername/DevReplicator.git
cd DevReplicator
```

---

## Usage

### CLI Mode

```bash
python replicator.py
```

You will be prompted to select CLI or UI mode, then enter a GitHub URL.

**Example:**
```
? GitHub repository URL: https://github.com/tiangolo/fastapi
```

### UI Mode

```bash
python replicator.py
# Select mode: 2
```

Opens a browser dashboard at `http://localhost:7474`.

---

## Project Structure

```
DevReplicator/
├── replicator.py          # Main entry point (CLI + UI launcher)
├── detectors.py           # Project type detection
├── docker_generator.py    # Dockerfile generation
├── executor.py            # Git clone + Docker build/run
├── utils.py               # Logging and prompt helpers
├── ui/
│   ├── index.html         # Browser dashboard
│   ├── styles.css         # Dark industrial theme
│   └── app.js             # Frontend logic
└── README.md
```

---

## Detection Heuristics

| File Found        | Detected Type     | Base Image         |
|-------------------|-------------------|--------------------|
| `requirements.txt`| Python (pip)      | `python:3.11-slim` |
| `pyproject.toml`  | Python (Poetry)   | `python:3.11-slim` |
| `package.json`    | Node.js           | `node:18-slim`     |
| `*.py` files only | Python (scanned)  | `python:3.11-slim` |
| None of the above | Unknown (prompts) | User-specified     |

---

## Entry Point Detection

**Python projects:** `app.py` → `main.py` → `server.py` → `run.py` → `manage.py` → `cli.py`

**Node projects:** `package.json[main]` → `index.js` → `server.js` → `app.js`

---

## Error Handling

| Scenario                  | Behavior                                     |
|---------------------------|----------------------------------------------|
| Docker not installed       | Clear error + link to install docs           |
| Docker daemon not running  | Clear error + systemctl hint                 |
| No requirements.txt        | Scans `.py` files for third-party imports    |
| No entry point found       | Prompts user to specify manually             |
| Unknown project type       | Prompts for base image + start command       |
| Invalid GitHub URL         | Warning + proceeds anyway                    |
| Existing container name    | Auto-removes conflicting container           |

---

## Generated Dockerfile Examples

### Python (pip)
```dockerfile
FROM python:3.11-slim
RUN apt-get update && apt-get install -y git curl && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["python", "app.py"]
```

### Node.js
```dockerfile
FROM node:18-slim
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm ci
COPY . .
CMD ["npm", "start"]
```

---

## Docker Commands (Post-Run)

```bash
# View container logs
docker logs -f <container-name>

# Open a shell inside the container
docker exec -it <container-name> bash

# Stop the container
docker stop <container-name>

# Remove the container
docker rm -f <container-name>
```

---

## License

MIT
