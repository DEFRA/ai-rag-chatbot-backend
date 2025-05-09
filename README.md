# ai-rag-chatbot-backend

This is work-in-progress. See [To Do List](./TODO.md)

- [ai-rag-chatbot-backend](#ai-rag-chatbot-backend)
  - [Requirements](#requirements)
    - [Python](#python)
    - [Linting and Formatting](#linting-and-formatting)
    - [Docker](#docker)
  - [Local development](#local-development)
    - [Setup & Configuration](#setup--configuration)
    - [Development](#development)
    - [Testing](#testing)
    - [Production Mode](#production-mode)
  - [API endpoints](#api-endpoints)
  - [Custom Cloudwatch Metrics](#custom-cloudwatch-metrics)
  - [Pipelines](#pipelines)
    - [Dependabot](#dependabot)
    - [SonarCloud](#sonarcloud)
  - [Licence](#licence)
    - [About the licence](#about-the-licence)

## Requirements

### Python

Please install python `>= 3.12` and [configure your python virtual environment](https://fastapi.tiangolo.com/virtual-environments/#create-a-virtual-environment):

```python
# create the virtual environment
python -m venv .venv

# activate the the virtual environment in the command line
source .venv/bin/activate

# update pip
python -m pip install --upgrade pip

# install the dependencies
pip install -r requirements-dev.txt

# install the pre-commit hooks
pre-commit install
```

This opinionated template uses the [`Fast API`](https://fastapi.tiangolo.com/) Python API framework.

This and all other runtime python libraries must reside in `requirements.txt`

Other non-runtime dependencies used for dev & test must reside in `requirements-dev.txt`

### Linting and Formatting

This project uses [Ruff](https://github.com/astral-sh/ruff) for linting and formatting Python code.

#### Running Ruff

To run Ruff from the command line:

```bash
# Run linting with auto-fix
ruff check . --fix

# Run formatting
ruff format .
```

#### Pre-commit Hooks

This project uses [pre-commit](https://pre-commit.com/) to run linting and formatting checks automatically before each commit.

The pre-commit configuration is defined in `.pre-commit-config.yaml`

To set up pre-commit hooks:

```bash
# Set up the git hooks
pre-commit install
```

To run the hooks manually on all files:

```bash
pre-commit run --all-files
```

#### VS Code Configuration

For the best development experience, configure VS Code to use Ruff:

1. Install the [Ruff extension](https://marketplace.visualstudio.com/items?itemName=charliermarsh.ruff) for VS Code
2. Configure your VS Code settings (`.vscode/settings.json`):

```json
{
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
        "source.fixAll.ruff": "explicit",
        "source.organizeImports.ruff": "explicit"
    },
    "ruff.lint.run": "onSave",
    "[python]": {
        "editor.defaultFormatter": "charliermarsh.ruff",
        "editor.formatOnSave": true,
        "editor.codeActionsOnSave": {
            "source.fixAll.ruff": "explicit",
            "source.organizeImports.ruff": "explicit"
        }
    }
}
```

This configuration will:

- Format your code with Ruff when you save a file
- Fix linting issues automatically when possible
- Organize imports according to isort rules

#### Ruff Configuration

Ruff is configured in the `.ruff.toml` file

### Docker

This repository uses Docker throughput its lifecycle i.e. both for local development and the environments. A benefit of this is that environment variables & secrets are managed consistently throughout the lifecycle

See the `Dockerfile` and `compose.yml` for details

## Local development

### Setup & Configuration

Follow the convention below for local environment variables and secrets in local development. Note that it does not use .env or python-dotenv as this is not the convention in the CDP environment.

**Environment variables:** `compose/aws.env`.

**Secrets:** `compose/secrets.env`. You need to create this, as it's excluded from version control.

**Libraries:** Ensure the python virtual environment is configured and libraries are installed using `requirements-dev.txt`, [as above](#python)

**Pre-Commit Hooks:** Ensure you install the pre-commit hooks, as above

### Development

The app can be run locally using Docker compose.  This template contains a local environment with:

- Localstack
- MongoDB
- This service

To run the application in development mode:

```bash
docker compose watch
```

The service will then run on `http://localhost:8085`

*****
Once the service is running if you want to run a specif file, just use this format: docker compose exec backend-service python -m app.core.agents.agentic_graph
*****

### Running the RAG (Retrieval Augmented Generation) Pipeline

To enable the chatbot to answer questions based on specific documents (e.g., farming grants), you need to populate its knowledge base (vector store). This involves two main steps:

1.  **Download Grant Documents:**
    This step fetches the latest grant information from the GOV.UK API, processes it into a structured JSON format.
    Run the following command in your terminal:
    ```bash
    docker compose exec backend-service python -m app.core.rag.download_farming_grants
    ```
    This will create a `farming_grants_processed.json` file inside the `/app` directory of your `backend-service` container.

2.  **Ingest Documents into Vector Store:**
    This step takes the JSON file generated above, chunks the documents, and loads them into the Chroma vector store, making them searchable by the agent.
    Run the following command:
    ```bash
    docker compose exec backend-service python -m app.core.rag.ingest_markdown_docs
    ```
    This will populate the vector store located at `/app/chroma_db_grants` inside the container, which is mapped to `./persistent_chroma_db` on your host machine (as per your `compose.yml`).

    **Note:** If you encounter issues with the vector store not being recognized after ingestion, try restarting the `backend-service` to ensure it loads the newly populated store:
    ```bash
    docker compose restart backend-service
    ```

3.  **Testing the RAG Functionality:**
    Once the ingestion is complete and the `backend-service` is running, you can test the RAG capabilities by sending a POST request to the `/query` endpoint.
    Example using `curl` (or any API client like Postman):
    ```bash
    curl -X POST http://localhost:8085/query \
    -H "Content-Type: application/json" \
    -d '{
        "query": "could you tell me more about the eligibility criteria please, for the herbal leys"
    }'
    ```

### Testing

Ensure the python virtual environment is configured and libraries are installed using `requirements-dev.txt`, [as above](#python)

Testing follows the [FastApi documented approach](https://fastapi.tiangolo.com/tutorial/testing/); using pytest & starlette.

To test the application run:

```bash
pytest
```

### Production Mode

To mimic the application running in `production mode locally run:

```bash
docker compose up --build -d
```

The service will then run on `http://localhost:8085`

Stop the application with

```bash
docker compose down
```

## API endpoints

| Endpoint             | Description                    |
| :------------------- | :----------------------------- |
| `GET: /docs`         | Automatic API Swagger docs     |
| `GET: /example`      | Simple example                 |

## Custom Cloudwatch Metrics

Uses the [aws embedded metrics library](https://github.com/awslabs/aws-embedded-metrics-python). An example can be found in `metrics.py`

In order to make this library work in the environments, the environment variable `AWS_EMF_ENVIRONMENT=local` is set in the app config. This tells the library to use the local cloudwatch agent that has been configured in CDP, and uses the environment variables set up in CDP `AWS_EMF_AGENT_ENDPOINT`, `AWS_EMF_LOG_GROUP_NAME`, `AWS_EMF_LOG_STREAM_NAME`, `AWS_EMF_NAMESPACE`, `AWS_EMF_SERVICE_NAME`

## Pipelines

### Dependabot

We have added an example dependabot configuration file to the repository. You can enable it by renaming
the [.github/example.dependabot.yml](.github/example.dependabot.yml) to `.github/dependabot.yml`

### SonarCloud

Instructions for setting up SonarCloud can be found in [sonar-project.properties](./sonar-project.properties)

## Licence

THIS INFORMATION IS LICENSED UNDER THE CONDITIONS OF THE OPEN GOVERNMENT LICENCE found at:

<http://www.nationalarchives.gov.uk/doc/open-government-licence/version/3>

The following attribution statement MUST be cited in your products and applications when using this information.

> Contains public sector information licensed under the Open Government license v3

### About the licence

The Open Government Licence (OGL) was developed by the Controller of Her Majesty's Stationery Office (HMSO) to enable
information providers in the public sector to license the use and re-use of their information under a common open
licence.

It is designed to encourage use and re-use of information freely and flexibly, with only a few conditions.

# AI RAG Chatbot Backend

## Persistent Memory Feature

This backend now supports **persistent conversational memory** using LangGraph's `MemorySaver`.
The agent can recall previous user messages and context across multiple turns and sessions.

### How It Works

- Each user/session is assigned a unique memory stream (by `user_id`).
- The agent loads conversation history from memory before processing a new query.
- After responding, the updated state is saved back to memory.
- This enables multi-turn, context-aware conversations.

### Usage

- By default, the API uses `"default_user"` as the session key.
- For real applications, pass a unique user/session ID to enable per-user memory.

### Relevant Code

- `app/core/agents/agentic_graph.py`:
  Integrates `MemorySaver` and provides `run_graph_with_memory`.
- `app/chat/router.py`:
  API layer updated to use persistent memory for each user/session.

---

**To enable per-user memory:**
Update the API to extract and pass a real user/session ID instead of `"default_user"`.

---
