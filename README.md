# STLC Manager

**Yapay Zeka Destekli Yazılım Test Yaşam Döngüsü Yönetimi**

> Yazılım testinin en zaman alan aşamalarını — senaryo üretiminden optimizasyona kadar — LLM tabanlı otomasyon ile hızlandıran, end-to-end bir test yönetim platformu.
> **Naming and project context:** This system is referred to as **STLC Manager** in the associated master's thesis and as **ESOGU DT TOOL** within [MATISSE](https://matisse-kdt.eu/), a European research project funded under the Horizon Europe programme through the Chips Joint Undertaking (Grant Agreement No. 101140216). MATISSE focuses on model-based engineering and the continuous verification and validation of industrial systems using Digital Twins (DTs).

STLC Manager is an AI-assisted web application designed to manage the Software Testing Life Cycle (STLC) from source code, requirements, and the outputs of earlier testing phases.

The application provides an 11-step workflow that covers code review and requirement analysis, test planning, scenario and test case generation, test code generation, Docker and ROS 2-based execution, reporting, and test closure.

> **Project status:** This project is under active development. Some features require local services, a running Docker daemon, a ROS 2 container, or an external model provider. Additional safety and operator-approval layers are required before running generated tests on physical robots.

## Table of contents

- [Key features](#key-features)
- [STLC pipeline](#stlc-pipeline)
- [Test Case Optimization](#test-case-optimization)
- [Test execution methods](#test-execution-methods)
- [Execution on a remote robot computer](#execution-on-a-remote-robot-computer)
- [Architecture and directory structure](#architecture-and-directory-structure)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Running the services](#running-the-services)
- [Configuration](#configuration)
- [Tests and utility scripts](#tests-and-utility-scripts)
- [API and health checks](#api-and-health-checks)
- [Known limitations](#known-limitations)
- [Security considerations](#security-considerations)

## Key features

- An 11-phase STLC pipeline
- Source code and document-based code review and requirement analysis
- AI-assisted generation of test plans, scenarios, test cases, and executable test code
- Individual, bulk, and parallel test case optimization
- Local models through LM Studio and Google Gemini API models
- MongoDB persistence for sessions, process outputs, and execution results
- Isolated test execution in Docker containers
- Parallel test execution in multiple Docker containers
- Robot arm simulation and ROS 2/Gazebo-oriented execution paths
- Test deployment to a local or network-shared directory and result collection
- Test reporting, quality evaluation, and test closure reports
- Live pipeline progress through Server-Sent Events (SSE) and pipeline cancellation

The quality evaluation layer calculates data-driven dimensions such as completeness, clarity, coverage, and depth. The relevant implementations are located in `backend/services/quality_metrics_calculator.py` and `backend/services/report_quality_evaluator.py`.

## STLC pipeline

Pipeline steps run in the following canonical order:

| Order | Step | Primary output | Dependencies |
|---:|---|---|---|
| 1 | Code Review | Code review report | — |
| 2 | Requirement Analysis | Requirement analysis report | — |
| 3 | Test Planning | Test plan | Code Review, Requirement Analysis |
| 4 | Environment Setup | Environment setup report | — |
| 5 | Test Scenario Generation | Test scenarios | Test Planning |
| 6 | Test Case Generation | Detailed test cases | Test Scenario Generation |
| 7 | Test Case Optimization | Deduplicated and optimized test cases | Test Case Generation |
| 8 | Test Code Generation | Executable test code | Test Case Optimization, Environment Setup |
| 9 | Test Execution | Test output and execution status | Test Code Generation |
| 10 | Test Reporting | Test report and metrics | Test Execution |
| 11 | Test Closure | Test closure report | Test Reporting |

The authoritative dependency graph is defined in `backend/pipeline/pipeline_controller.py`. The current primary frontend pipeline keeps all 11 steps enabled, while the backend still validates dependencies for the submitted step set.

The pipeline supports:

- Per-step model and prompt configuration
- File-to-step mapping
- Passing outputs between dependent steps
- Current status and step-result queries
- Live progress over SSE
- Stopping a running pipeline

## Test Case Optimization

Test Case Optimization is the seventh pipeline step and sits between Test Case Generation and Test Code Generation. Its purpose is to identify semantically overlapping test cases, retain representative cases, and reduce unnecessary downstream test-code generation and execution work.

This module does not simply compare titles or perform exact-text deduplication. It uses the selected language model to evaluate whether test cases exercise the same behavior, conditions, and expected outcome.

### Inputs and selection

The optimization interface supports:

- Loading generated test cases by process title
- Combining test cases from multiple process titles
- Selecting all cases or an explicit subset
- Assigning a name to the optimization run
- Selecting a configured local or API model
- Supplying a custom optimization prompt
- Choosing an optimization strategy

The selected process titles, process name, model, prompt state, and optimization type are retained with the session output.

### Optimization strategies

#### Individual optimization

Individual optimization processes test cases serially. Each candidate is compared with the representative cases already retained in the unique set. When the model determines that a candidate is semantically equivalent to a retained case, the candidate is recorded as a duplicate; otherwise, it becomes a new representative case.

This mode is straightforward and produces pair-level comparison information, but the number of model calls can grow significantly with larger test sets.

#### Bulk optimization

Bulk optimization submits the selected test-case set to the model in a consolidated request. The model is asked to return representative indices and duplicate groups. The service accepts several supported JSON response shapes and converts them into the common optimization result structure.

Bulk mode generally requires fewer model requests than serial pairwise processing, but its effectiveness depends on the selected model's context capacity and its ability to return valid structured output.

#### Parallel optimization

Parallel optimization prepares pairwise comparisons for parallel batch processing, aggregates the comparison results, and derives the final unique and duplicate sets. The service includes batch splitting, cross-batch duplicate handling, rate-limit retry behavior, and validation that a test case is not simultaneously classified as unique and duplicate.

The current router enables parallel optimization only for Gemini models. The frontend reflects this constraint and recommends Bulk Optimization when a selected model cannot use the parallel path.

### Results and persistence

An optimization result can contain:

- The original number of selected test cases
- Representative or unique test cases
- Duplicate/similar test cases and their matched representative
- Unique and duplicate counts
- Reduction statistics
- Comparison logs or batch metadata, depending on the strategy
- The model, prompt, process name, process titles, session ID, and optimization type

Results are stored per process title in the `test_case_optimizations` MongoDB collection. A session-level copy is also written under `session_history.processes.test_case_optimization` for traceability across the STLC pipeline.

Stored results can be queried by process title or process name. The API also supports deleting saved results for a process title.

### Process control and monitoring

The module exposes operations for:

- Starting smart selection with `individual`, `bulk`, or `parallel` mode
- Checking a running process by process ID
- Listing active optimization processes
- Requesting cancellation of an active process
- Exporting a session monitoring report
- Reading aggregated error statistics
- Configuring retry behavior
- Reading or resetting optimization monitoring statistics

The primary API prefix is `/api/test-case-optimization`.

### Interpretation and limitations

- Similarity decisions are model-dependent and may differ between models or prompts.
- Optimization identifies semantic redundancy; it does not prove requirement coverage or test effectiveness.
- A representative test should be reviewed before discarding a test that contains distinct data, preconditions, risk, or traceability information.
- Individual pairwise comparison can approach quadratic growth as the number of test cases increases.
- Bulk mode is constrained by model context size and structured-output reliability.
- Parallel mode requires a supported Gemini model and may still be affected by provider quotas and rate limits.
- Optimization results should remain traceable to their source test cases and requirements, especially in regulated or safety-critical systems.

## Test execution methods

The project contains several execution paths with different semantics and trust levels.

### 1. Standard Execution (MCP and AI provider)

- Generated test code stored in MongoDB can be selected by process or test identifier.
- The backend sends the test content to the local MCP server through JSON-RPC.
- The MCP server uses either LM Studio or Gemini as the provider.
- Terminal-like output and basic pass/fail statistics can be persisted in MongoDB.

The default MCP endpoint is `http://localhost:8001`, and the default LM Studio endpoint is `http://localhost:1234`.

> Standard Execution is an AI/MCP-based execution path. By itself, it is not an operating-system-level remote agent that runs commands on a physical robot computer.

### 2. Docker Process

- Writes test code into a temporary working directory.
- Starts an isolated container using the configured language image.
- Collects `stdout`, `stderr`, the exit code, and container metadata.
- Supports timeouts, additional packages, and environment variables.
- Removes temporary containers, custom images, and working directories after execution.

Current language mappings:

| Language | Default image |
|---|---|
| Python | `python:3.9-slim` |
| JavaScript | `node:18-alpine` |
| Java | `openjdk:11-jre-slim` |
| C# | `mcr.microsoft.com/dotnet/sdk:6.0` |
| Go | `golang:1.19-alpine` |
| Rust | `rust:1.70-slim` |

Docker may need to download the selected image during its first execution.

### 3. Parallel Docker Execution

- Splits selected tests into separate Docker jobs.
- Allows the maximum number of concurrent containers to be configured.
- Exposes session-based progress and result queries.
- Supports cancellation of an active parallel execution.

Parallel execution can consume significant CPU and memory. Configure `max_parallel`, timeout, and additional packages according to the capacity of the execution host.

### 4. Docker Sandbox

The sandbox runs test code entered directly in the user interface inside Docker. It does not require selecting a generated test process from the database.

### 5. Robot Simulation

- Provides a container-based simulation path for `generic`, `industrial`, and `collaborative` robot types.
- Can build a Python environment with NumPy, SciPy, Matplotlib, Robotics Toolbox, and SpatialMath.
- Does not establish a direct connection to a physical robot controller.

### 6. ROS 2 Docker Execution

- Checks whether the expected ROS 2 Docker container is running.
- Copies a test script into the container as `/tmp/stlc_<test-id>.py`.
- Sources the ROS 2 environment and executes the script inside the container.
- Supports single and batch execution.
- Can use X11/GUI configuration for visual tests.
- Collects the exit code, output, errors, and duration.

The ROS 2 image definition and helper scripts are under `docker/`. The compose file in that directory assumes a specific external ROS 2 workspace layout. Review and adjust its build context and volume paths for your own workspace.

### 7. Robot Test Execution (ROS 2 and Gazebo)

The robot test panel can:

- Retrieve generated tests by process name.
- Run selected tests as a batch.
- Query session progress and results.
- Check Gazebo availability through a dedicated endpoint.
- Store execution records in MongoDB.

This execution path requires a Docker, ROS 2, and Gazebo environment that is accessible to the backend host.

## Execution on a remote robot computer

The project contains a **Remote Robot Execution** user interface and backend service. This feature is a shared-directory deployment protocol, not direct SSH/SFTP-based remote command execution.

### Current workflow

1. STLC Manager creates an execution directory under the supplied local or UNC network path.
2. It prepares the following directory and metadata structure:

```text
test_exec_<session>_<timestamp>/
├── source_files/
├── results/
├── logs/
├── deployment_info.json
└── execution_status.json
```

3. Generated test code is written to `source_files/`.
4. An external runner or service on the robot computer reads and executes the tests.
5. The runner writes JSON results to `results/`, writes logs to `logs/`, and updates the status file.
6. STLC Manager reads the results and aggregates total, passed, failed, and skipped tests together with the pass rate.

### Requirements for a computer in another city

- A VPN or corporate network connection between the two computers
- A directory on the remote computer exposed through SMB/UNC, for example `\\robot-pc\stlc-tests`
- Read and write permissions for the operating-system account running the FastAPI backend
- A separate runner or agent on the remote computer that monitors the directory and executes tests
- A runner implementation that writes the expected JSON result format and updates `execution_status.json`

### Operations that are not currently automated

- SSH connection and authentication
- SFTP/SCP file transfer
- Starting or stopping a process on the remote computer
- Remote runner installation or updates
- Durable job queues and retry policies for offline machines
- Operator approval and safety PLC integration for physical robots

The accurate description of the current feature is therefore:

> Shared-directory-based remote test deployment and result collection are implemented. End-to-end remote execution orchestration still requires a runner on the target computer.

## Architecture and directory structure

```text
STLC-Manager/
├── backend/
│   ├── app.py                    # Main FastAPI application (port 8000)
│   ├── mcp_server.py             # MCP test execution service (port 8001)
│   ├── config/                   # Model and optimization configuration
│   ├── core/                     # MongoDB, file, and prompt infrastructure
│   ├── models/                   # Robot and test-criteria data models
│   ├── pipeline/                 # Pipeline order, models, and executor
│   ├── routers/                  # REST API endpoints
│   ├── services/                 # Business logic and execution services
│   ├── stlc/                     # STLC process implementations
│   ├── templates/                # Docker and output templates
│   ├── utils/                    # Model client, text, and validation utilities
│   └── scripts/
│       ├── diagnostics/          # Read-only inspection tools
│       ├── experiments/          # Manual debugging and experiments
│       ├── maintenance/          # Data maintenance and repair tools
│       └── migrations/           # Database migration tools
├── frontend/
│   ├── src/components/           # React components
│   ├── src/store/                # Redux store and slices
│   ├── src/services/             # Backend API calls
│   └── src/hooks/                # Model, API-key, and pipeline hooks
├── docker/                       # ROS 2 Dockerfile, compose file, and helpers
├── test_inputs/                  # Sample test inputs
├── test_results/                 # Experiment and test results
└── tests/
    ├── unit/
    ├── integration/
    ├── performance/
    ├── utils/
    └── results/
```

Some legacy `test_*.py` files remain in the backend root. Several of them are manual or integration tests that depend on live MongoDB, API, Docker, or model services and have not yet been fully classified under `tests/`.

## Prerequisites

Recommended development environment:

- Python 3.10 or later
- Node.js 18 or later
- MongoDB, either local or otherwise made accessible to the application
- An npm-compatible package manager

Optional integrations:

- LM Studio for local LLM execution
- A Google Gemini API key for Gemini models
- Docker Desktop or Docker Engine for container execution
- ROS 2 Humble, a Gazebo/MoveIt workspace, and a suitable Docker image for robot execution
- VcXsrv or an equivalent X server for Windows GUI scenarios

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/cembglm/stlc-man.git
cd STLC-Manager
```

Alternative ESOGU organization remote: <https://github.com/ESOGU-SRLAB/STLC-Manager>

### 2. Install backend dependencies

Windows PowerShell:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Linux or macOS:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Start MongoDB

Ensure that a local MongoDB server is running on `localhost:27017`. The current primary database name is `stlc_database`.

Example Docker command:

```bash
docker run -d --name stlc-mongodb -p 27017:27017 mongo:latest
```

> The current `backend/core/database.py` defines the MongoDB URI directly as `mongodb://localhost:27017`. Changing only `MONGO_URI` in `.env` does not affect that database helper. Centralize the database configuration before using a remote MongoDB deployment.

### 4. Install frontend dependencies

```bash
cd frontend
npm install
```

## Running the services

MongoDB, the FastAPI backend, and the frontend must run during normal development. Start the MCP service as well when using Standard Execution.

### Terminal 1 — Backend API

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python app.py
```

Backend: <http://localhost:8100>

Swagger UI: <http://localhost:8100/docs>

### Terminal 2 — MCP server

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python mcp_server.py
```

MCP health endpoint: <http://localhost:8001/health>

When using a local model with Standard Execution, start the LM Studio OpenAI-compatible server on `http://localhost:1234` and load the selected model.

### Terminal 3 — Frontend

```bash
cd frontend
npm run dev
```

The default Vite URL is <http://localhost:5175>.

### Quick checks

```text
GET http://localhost:8100/
GET http://localhost:8100/api/health/prompts
GET http://localhost:8100/api/docker-execution/status
GET http://localhost:8100/api/ros2-execution/status
GET http://localhost:8100/api/remote-execution/health
GET http://localhost:8001/health
GET http://localhost:8001/providers/status
```

## Configuration

Primary backend configuration values:

| Variable | Default | Purpose |
|---|---|---|
| `MODEL_API_BASE_URL` | `http://localhost:1234` | General local model API endpoint |
| `MODEL_IDENTIFIER` | `llama-3.2-3b-instruct` | General default model |
| `MCP_SERVER_URL` | `http://localhost:8001` | MCP endpoint used by the pipeline |
| `MCP_SERVER_PORT` | `8001` | MCP service port |
| `LM_STUDIO_BASE_URL` | `http://localhost:1234` | LM Studio endpoint used by MCP |
| `DEFAULT_LM_STUDIO_MODEL` | `llama-3.2-3b-instruct` | Default local model used by MCP |

Example `backend/.env`:

```dotenv
MODEL_API_BASE_URL=http://localhost:1234
MODEL_IDENTIFIER=llama-3.2-3b-instruct
MCP_SERVER_URL=http://localhost:8001
MCP_SERVER_PORT=8001
LM_STUDIO_BASE_URL=http://localhost:1234
DEFAULT_LM_STUDIO_MODEL=llama-3.2-3b-instruct
```

API keys can be entered through the API Key settings in the user interface and are sent to the backend with the relevant requests. Never commit API keys to the repository.

During development, frontend API calls use same-origin `/api` paths and Vite proxies them to `VITE_API_PROXY_TARGET` (default: `http://localhost:8100`). Set `VITE_API_BASE_URL` only when the browser must call a separately hosted backend directly.

## Tests and utility scripts

The primary test structure is under `tests/`:

```bash
python -m pytest tests/unit
python -m pytest tests/integration
python -m pytest tests/performance
```

`pytest` is not currently listed in `backend/requirements.txt`. Install the test dependencies separately in your development environment:

```bash
pip install pytest pytest-asyncio
```

Some tests use live MongoDB, LM Studio/Gemini, Docker, or running backend endpoints. Review the requirements of each test file before running the entire suite; not every file is a self-contained unit test.

Backend utility scripts are organized under `backend/scripts/`. Run them as modules from the `backend` directory so imports continue to resolve correctly:

```powershell
cd backend
python -m scripts.diagnostics.check_routes
python -m scripts.diagnostics.check_mongo_connection
```

Utilities under `maintenance/` and `migrations/` can modify or delete data. Review their source code and target database before running them.

## API and health checks

When FastAPI is running, the current endpoint list is available through Swagger:

- Swagger UI: <http://localhost:8000/docs>
- OpenAPI JSON: <http://localhost:8000/openapi.json>

Primary API groups:

| Prefix | Purpose |
|---|---|
| `/api/processes/*` | Run individual STLC steps |
| `/api/prompts/*` | Read or update module prompts |
| `/api/models/*` | List and filter configured models |
| `/api/pipeline/*` | Start, monitor, inspect, or stop a pipeline |
| `/api/test-execution/*` | MCP and AI-based test execution |
| `/api/docker-execution/*` | Docker, simulation, and parallel execution |
| `/api/ros2-execution/*` | ROS 2 container execution |
| `/api/robot-execution/*` | ROS 2/Gazebo robot test sessions |
| `/api/remote-execution/*` | Shared-directory deployment and result collection |
| `/api/test-reporting/*` | Test reporting |
| `/api/test-closure/*` | Test closure reports |

## Known limitations

- Remote execution does not use SSH, SFTP, or WinRM; it requires an accessible filesystem or UNC share.
- The repository does not yet provide a complete target-side runner service for the robot computer.
- The MongoDB connection in `backend/core/database.py` is fixed to the local address.
- Frontend API endpoints are not fully centralized, so multi-host deployment requires additional configuration work.
- `docker/docker-compose.yml` assumes a specific external ROS 2 workspace layout.
- Some tests require live external services and are not suitable for unattended CI execution as currently written.
- Legacy backend test scripts have not been completely moved under `tests/`.
- Python dependency versions are not pinned, so a lock or version-pinning strategy is still needed for reproducible deployments.
- Standard Execution output and tests actually executed in Docker or ROS 2 should not be treated as having the same evidence level.

## Security considerations

- Treat generated test code as untrusted code.
- Docker socket access is highly privileged; do not expose the backend directly to untrusted users.
- Only trusted users should be allowed to request additional package installation.
- Apply least-privilege permissions to Remote Execution network shares.
- Never write API keys to source files, test results, or logs.
- CORS defaults to local frontend origins; set an explicit production allow-list before deployment.
- Physical robot testing requires simulation validation, speed, torque, and workspace limits, an emergency stop, safety PLC integration, and explicit operator approval.

## Contribution and development workflow

When adding a feature:

1. Keep business logic under `backend/services/`.
2. Define the HTTP layer under `backend/routers/`.
3. If the feature joins the pipeline, update `pipeline_controller.py` and `step_adapters.py` together.
4. Route frontend calls through the centralized API helper whenever possible.
5. Add tests to the appropriate `unit`, `integration`, or `performance` category.
6. Document MongoDB schema and session-output changes.
7. Update this README and the relevant Docker or ROS 2 guide.

## License

This project is licensed under the [Apache License 2.0](LICENSE).

## External Integration and Docker Deployment

The FastAPI backend can be used without the React UI. Its OpenAPI contract is
available at `/docs` and `/openapi.json`. The stable integration surface is
under `/api/v1`; existing UI endpoints remain unchanged.

### Running locally

MongoDB is required. Copy `.env.example` to `.env`, adjust the values, then:

```bash
python -m pip install -r backend/requirements.txt
cd backend
uvicorn app:app --host 0.0.0.0 --port 8000
```

`GET /health` only checks that the process is alive. `GET /ready` returns HTTP
200 after MongoDB responds to a ping, or HTTP 503 with machine-readable JSON.
Model providers and the external executor are intentionally not readiness
dependencies because neither is required for the API process to start.

### Running with Docker

The root `Dockerfile` is the complete STLC backend image. The legacy files under
`docker/` are not part of the normal build and are not used by the external
execution API:

```bash
docker build -t stlc-manager-backend .
docker run --rm -p 8000:8000 --env-file .env stlc-manager-backend
```

The database URL in `.env` must be reachable from inside the container. Do not
use `localhost` there for a database running in another container.

### Running with Docker Compose

The root Compose file starts the backend and its required MongoDB dependency:

```bash
cp .env.example .env
# Edit .env before continuing.
docker compose up -d --build
docker compose ps
```

PowerShell equivalent for the first command:

```powershell
Copy-Item .env.example .env
```

For a server deployment, set `API_AUTH_ENABLED=true`, generate a strong
`APP_API_KEY`, replace `CORS_ALLOWED_ORIGINS` with the real browser origins, and
configure `MODEL_API_BASE_URL` plus `MODEL_IDENTIFIER`. `EXECUTION_SERVICE_URL`
and `EXECUTION_SERVICE_TOKEN` remain optional until the external executor is
available. Compose always supplies the internal MongoDB address
`mongodb://mongo:27017`; do not replace it with a host `localhost` address.

Verify and inspect the deployment from the Docker host:

```bash
curl http://localhost:8100/health
curl http://localhost:8100/ready
curl http://localhost:8100/openapi.json
docker compose logs -f backend
```

Stop containers without deleting persistent data:

```bash
docker compose down
```

Do not use `docker compose down -v` casually: `-v` removes the MongoDB and
artifact named volumes.

Compose persists MongoDB data and submitted artifacts in named volumes. It does
not containerize model providers, MCP, or the external execution system. The
default `host.docker.internal` model URL is convenient for Docker Desktop; set
`MODEL_API_BASE_URL` to a server-reachable URL in other deployments.
Compose maps `host.docker.internal` through Docker's host gateway for Linux
engines as well. A host LM Studio instance must listen on an interface reachable
from containers; merely listening on host loopback is insufficient.

### Deployment and Serhat smoke test

The reusable client at `scripts/external_integration_smoke.py` makes only public
HTTP calls and represents Serhat's backend. It exits non-zero on any health,
authentication, submission, job, or result failure.

Run a quick deployment/auth/artifact check:

```bash
STLC_BASE_URL=http://localhost:8100 \
STLC_API_KEY='<same value as APP_API_KEY>' \
python scripts/external_integration_smoke.py --deployment-only
```

Run the complete artifact → environment → scenario → case → code workflow:

```bash
STLC_BASE_URL=http://localhost:8100 \
STLC_API_KEY='<same value as APP_API_KEY>' \
STLC_MODEL=llama-3.2-3b-instruct \
python scripts/external_integration_smoke.py
```

The script first verifies missing and invalid credentials return `401`, then
uses `X-API-Key` for authenticated calls. Override `STLC_ARTIFACT_PATH`,
`STLC_PROCESS_TITLE`, `STLC_JOB_TIMEOUT`, or `STLC_MAX_TEST_CASES` as needed.
Every run generates a unique process title by default.

### Authentication and CORS

Set `API_AUTH_ENABLED=true` and `APP_API_KEY` to a long random secret in a
server deployment. External callers may send either `X-API-Key` or
`Authorization: Bearer <APP_API_KEY>`.

Authentication applies to `/api/v1/*`. It defaults off to preserve the current
local frontend workflow. Configure browser origins as a comma-separated list in
`CORS_ALLOWED_ORIGINS`; authenticated configuration rejects wildcard CORS.

### External API contracts

All submission endpoints accept and return JSON. Generation and execution are
background jobs because LLM and executor calls can exceed normal HTTP request
durations. A submission returns HTTP 202:

```json
{
  "job_id": "job_...",
  "status": "pending",
  "status_url": "/api/v1/jobs/job_...",
  "result_url": "/api/v1/jobs/job_.../result"
}
```

Jobs transition through `pending`, `running`, `completed`, or `failed`. Job
state is process-local and is lost on restart; run one backend worker. A durable
shared queue is the remaining requirement before horizontally scaling workers.

| Method | Endpoint | Purpose / principal request fields |
| --- | --- | --- |
| `POST` | `/api/v1/artifacts` | Store input: `name`, textual `content`, optional `type`, `metadata` |
| `GET` | `/api/v1/artifacts/{artifact_id}` | Read artifact metadata (content is not echoed) |
| `POST` | `/api/v1/generations/environment` | Persist environment setup: `process_title`, `environment_name`, `artifact_ids` |
| `POST` | `/api/v1/generations/scenarios` | `process_title`, `artifact_ids`, optional model/prompt/test type/category |
| `POST` | `/api/v1/generations/test-cases` | `process_title`, plus inline `scenarios` or completed `scenario_job_id` |
| `POST` | `/api/v1/generations/test-code` | `process_title`, persisted `environment_session_id`, `environment_name`, source `artifact_ids` |
| `POST` | `/api/v1/executions` | `test_code`, optional `metadata` and `configuration` |
| `GET` | `/api/v1/jobs/{job_id}` | Poll job metadata/status |
| `GET` | `/api/v1/jobs/{job_id}/result` | Fetch completed result; returns 202 while running |
| `GET` | `/health` | Process liveness (public) |
| `GET` | `/ready` | MongoDB readiness (public) |

Environment, scenario, and case endpoints reuse the existing pipeline adapters. Test code
generation reuses `TestCodeGenerationService`; consequently, the named process
must already have generated/optimized test cases in MongoDB and the supplied
environment session must come from the completed environment job. Existing
`POST /api/pipeline/run`, status, result, and SSE endpoints remain available for
the UI and full STLC orchestration.

The state hand-off is explicit:

- Artifact records are JSON files under `ARTIFACT_DIR`; adapters resolve their
  IDs into the same file objects used by existing services.
- Environment setup persists under
  `session_history.processes.environment_setup`; its submission response exposes
  the generated `session_id` required by code generation.
- Scenario generation reads the prompt collections and persists under
  `session_history.processes.test_scenario_generation`.
- Test-case generation consumes the completed scenario job (or typed inline
  scenarios), then persists under `processes.test_case_generation` with the
  caller-supplied `process_title`.
- Test-code generation uses that same `process_title` to find cases and the
  environment `session_id` to find framework/language setup. Results persist
  under `processes.test_code_generation`.

Use a unique `process_title` for each concurrently active external workflow.
The existing test-code service deliberately resolves persisted cases by title,
so reusing one title for overlapping runs can make the selected case set
ambiguous even though job IDs, session IDs, and artifact filenames are unique.

The frontend previously supplied file-type labels, process titles, model
selection, scenario field conversion, and prompt selection. The external API
now normalizes `requirement` artifacts, returns every generated session ID,
accepts the process title/model explicitly, converts stored scenario fields,
and falls back to the configured server model and database prompt collections.

Validation, authentication, and job failures use this shape (with fields
omitted when not applicable):

```json
{
  "error_code": "GENERATION_FAILED",
  "message": "Test scenario generation failed.",
  "details": "sanitized diagnostic information",
  "job_id": "job_..."
}
```

### Example external request

This example shows the real required external client → STLC → executor sequence. The
environment and scenario jobs are independent and may run in parallel, but both
must be complete before test-code generation. Artifact type `requirement`
is normalized to the existing service's `Requirement Document` type.

```python
import os
import time
import requests

BASE_URL = "https://stlc.example.com"
HEADERS = {
    "Authorization": f"Bearer {os.environ['STLC_API_KEY']}",
    "Content-Type": "application/json",
}

def submit(path, payload):
    response = requests.post(BASE_URL + path, headers=HEADERS, json=payload, timeout=30)
    response.raise_for_status()
    return response.json()

def wait_for(job):
    while True:
        status = requests.get(BASE_URL + job["status_url"], headers=HEADERS, timeout=30)
        status.raise_for_status()
        state = status.json()
        if state["status"] == "completed":
            result = requests.get(BASE_URL + job["result_url"], headers=HEADERS, timeout=30)
            result.raise_for_status()
            return result.json()["result"]
        if state["status"] == "failed":
            raise RuntimeError(state["error"])
        time.sleep(1)

# 1. Persist the input artifact.
artifact = submit("/api/v1/artifacts", {
    "name": "requirements.txt",
    "type": "requirement",
    "content": "The user can reset a password.",
    "metadata": {"external_project_id": "cloud-project-42"},
})

# 2. Persist environment setup. The returned session_id is used by code generation.
environment_job = submit("/api/v1/generations/environment", {
    "process_title": "Password reset",
    "environment_name": "Password reset API tests",
    "artifact_ids": [artifact["artifact_id"]],
})
environment = wait_for(environment_job)

# 3–4. Generate scenarios and poll the job.
scenario_job = submit("/api/v1/generations/scenarios", {
    "process_title": "Password reset",
    "artifact_ids": [artifact["artifact_id"]],
    "test_type": "Functional",
    "test_category": "Positive",
})
scenarios = wait_for(scenario_job)

# 5–6. The scenario job ID carries the actual scenario output into case generation.
case_job = submit("/api/v1/generations/test-cases", {
    "process_title": "Password reset",
    "scenario_job_id": scenario_job["job_id"],
    "artifact_ids": [artifact["artifact_id"]],
})
test_cases = wait_for(case_job)

# 7–8. process_title locates persisted cases; environment_session_id locates setup.
code_job = submit("/api/v1/generations/test-code", {
    "process_title": "Password reset",
    "environment_session_id": environment_job["session_id"],
    "environment_name": "Password reset generated code",
    "artifact_ids": [artifact["artifact_id"]],
    "max_test_cases": 1,
})
code_result = wait_for(code_job)
generated = code_result["generated_tests"][0]

# 9–10. Submit to the configured remote executor and retrieve its result.
execution_job = submit("/api/v1/executions", {
    "test_code": generated["code"],
    "language": generated.get("language"),
    "framework": generated.get("framework"),
    "test_case_id": generated.get("test_case_id"),
    "session_id": code_job["session_id"],
    "artifact_ids": [artifact["artifact_id"]],
    "metadata": {"external_project_id": "cloud-project-42"},
    "configuration": {"timeout_seconds": 300},
})
execution_result = wait_for(execution_job)
```

### Configuration reference

- `APP_HOST`, `APP_PORT`, `APP_RELOAD`, `LOG_LEVEL`
- `INITIALIZE_PROMPTS_ON_STARTUP`
- `MONGO_URI`, `DATABASE_NAME`
- `CORS_ALLOWED_ORIGINS`
- `API_AUTH_ENABLED`, `APP_API_KEY`
- `MODEL_API_BASE_URL`, `MODEL_IDENTIFIER`, `MODEL_API_KEY`
- `MCP_SERVER_URL`
- `EXECUTION_ADAPTER`, `EXECUTION_SERVICE_URL`, `EXECUTION_SERVICE_TOKEN`, `EXECUTION_TIMEOUT_SECONDS`
- `SSH_EXECUTION_HOST`, `SSH_EXECUTION_REMOTE_DIR`, `SSH_EXECUTION_IMAGE`, `SSH_EXECUTION_IDENTITY_FILE`, `SSH_EXECUTION_PASSWORD`
- `ARTIFACT_DIR`, `UPLOAD_DIR`

### Repository and responsibility boundary

STLC Manager generates scenarios, cases, and test code, submits generated code
to a configured remote service, and consumes its standardized result. The
external executor receives that code, runs it in its independently managed
HIL/robot environment, and returns the result.

> The HIL/docker harness implementation is not part of the STLC Manager
> repository and is deployed independently.

For an independently deployed HTTP executor, the STLC repository neither
imports nor builds the executor implementation. Configure that boundary with:

```dotenv
EXECUTION_SERVICE_URL=http://executor-host:8090
EXECUTION_SERVICE_TOKEN=change-me
EXECUTION_TIMEOUT_SECONDS=1900
```

`ExecutionAdapter` defines this boundary. The included
`HttpExecutionClient` sends `POST {EXECUTION_SERVICE_URL}/executions` and parses
the standardized fields `execution_id`, `status`, timestamps, pass/fail counts,
logs, error, and artifacts. If no URL is configured, STLC startup, readiness,
and every generation function remain available; only `POST /api/v1/executions`
returns structured HTTP 503 `EXECUTION_SERVICE_NOT_CONFIGURED`.

The verified ASRLAB -> IFARLAB ROS 2 harness can also be selected directly:

```dotenv
EXECUTION_ADAPTER=ssh_docker
SSH_EXECUTION_HOST=ifarlab
SSH_EXECUTION_REMOTE_DIR=~/stlc_runs
SSH_EXECUTION_IMAGE=ros2-exec-harness:0.3.2
SSH_EXECUTION_IDENTITY_FILE=C:\\Users\\matisse\\.ssh\\id_ed25519_ifarlab
# Optional fallback when unattended key authentication is unavailable.
SSH_EXECUTION_PASSWORD=
EXECUTION_TIMEOUT_SECONDS=300
```

This adapter performs a read-only target preflight, transfers each generated
Python test with SCP, and invokes the harness over SSH using `--network host`,
`--ipc=host`, and `FASTDDS_BUILTIN_TRANSPORTS=UDPv4`. The uploaded script is
mounted read-only and remote execution is bounded by the harness itself. OpenSSH host
keys must already be trusted. When the backend itself runs in Docker, mount the
SSH config, private key, and `known_hosts` read-only into the `stlc` user's home
and set `SSH_EXECUTION_IDENTITY_FILE` to that in-container key path.
If a password is required, keep `SSH_EXECUTION_PASSWORD` only in the untracked
server `.env`; it is never returned to the frontend or monitoring events.

Remote tests follow a single-file contract: newly generated code may import
public APIs from installed packages, but may not import package `examples/`
scripts, relative sibling files, or `sim_robot_goal`. Required helper/controller
classes must be included in the generated test file. Test-code generation
validates this contract, attempts one automatic correction, and rejects
remaining violations before uploading code to IFARLAB.

For previously generated records, `ros2-exec-harness:0.2.0` and newer retain a
compatibility export for `sim_robot_goal`; the SSH execution adapter permits
that import only for those compatible image versions. Files submitted from the
Test Execution remote panel are passed to the harness as `python3 <file>.py`.
The 0.3.x entrypoint detects test functions and runs pytest itself, ensuring its
timeout and post-test robot reset always remain active.
The current IFARLAB runner image is `ros2-exec-harness:0.3.2`. It owns the
per-test runtime limit and returns pytest-compatible exit codes: 0 passed, 1
failed, 2 collection/import error, 5 no tests collected, and 124 harness timeout.
STLC does not wrap the remote `docker run` call in another timeout. Result data
also exposes the final `[harness] reset: status=...` value when present.

Robot-focused generation can also receive a separate `robot_capabilities.json`
from the Test Code Generation form. The contract must contain `schema_version`,
`api.classes`, `api.allowed_imports`, and `limits`. Before use, an engineer must
set `meta.approval.approved` to `true` and fill `approved_by` and `approved_at`;
draft contracts are rejected before any model call. When supplied, the contract
is treated as a closed world: undeclared controller methods, forbidden mocks,
invalid joint-vector lengths, literal joint positions outside declared limits,
and unsafe velocity/acceleration scaling values fail generation validation.
All source files selected for Test Code Generation are sent and included as
bounded implementation context; the form no longer submits only the first file.
The form also provides a per-test input budget from 4,096 to 64,000 tokens and
an estimator for source code, the custom prompt, one test case, and the optional
robot capability contract. Each test case and its oracle-repair request is sent
to the model atomically. If the selected context exceeds the configured budget,
generation stops with an explicit error instead of splitting executable Python
into independent responses and concatenating them.

## Monitoring Integration

STLC publishes consumer-neutral lifecycle telemetry from the existing pipeline
and asynchronous job paths. Monitoring is optional and never calls a dashboard
directly. Events are retained in MongoDB's `monitoring_events` collection and
fanned out to live subscribers inside the backend process.

- History: `GET /api/v1/monitoring/events` (bounded to 500; default 100)
- Single event: `GET /api/v1/monitoring/events/{event_id}`
- Live SSE: `GET /api/v1/monitoring/events/stream`
- Authentication: the same `X-API-Key` or Bearer token used by `/api/v1`
- Filters: `process_id`, `process_title`, `session_id`, `job_id`,
  `execution_id`, `module`, `event_type`, `status`, and `since`

The event taxonomy is `pipeline.started|completed|failed`,
`module.started|progress|completed|failed`, and
`execution.submitted|started|completed|failed`. Module values are
`artifact_ingestion`, `environment_setup`, `scenario_generation`,
`test_case_generation`, `test_code_generation`, and `test_execution`.
Events contain correlation IDs, status/progress, duration, small metrics and
sanitized metadata; generated code, prompts, artifacts, and credentials are
excluded.

```bash
curl -H "X-API-Key: $APP_API_KEY" \
  "http://localhost:8100/api/v1/monitoring/events?session_id=session-123&limit=100"

curl -N -H "Authorization: Bearer $APP_API_KEY" \
  -H "Last-Event-ID: evt_previous" \
  "http://localhost:8100/api/v1/monitoring/events/stream?session_id=session-123"
```

`MONITORING_ENABLED` controls emission and
`MONITORING_EVENT_RETENTION_DAYS` controls the MongoDB TTL (30 by default, 0
disables expiry). SSE fan-out and asynchronous jobs are process-local: use one
worker for ordered live delivery, and reconstruct state from REST history after
a restart or reconnect. MongoDB history remains authoritative across restarts.
Any monitoring consumer is deployed independently; none is required to build,
start, or operate STLC Manager.
