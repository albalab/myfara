# MyFara - FARA Agent with Ollama

This repository contains a Docker setup to run Microsoft's FARA (Fast Agent for Research Automation) with Ollama LLM integration.

## Prerequisites

- Docker
- Docker Compose

## Quick Start

1. Clone the repository:
```bash
git clone https://github.com/albalab/myfara.git
cd myfara
```

2. Build and run the containers:
```bash
docker compose up --build
```

This will:
- Start the Ollama service and download the `llama3.2:3b` model
- Wait for Ollama to be healthy
- Start the Fara agent container

## Architecture

The setup consists of two Docker services:

### 1. Ollama Service
- Runs the Ollama LLM server
- Automatically downloads the `llama3.2:3b` model on first start
- Exposes port 11434 for API access
- Includes healthcheck to ensure service is ready before starting Fara

### 2. Fara Service
- Runs the FARA agent with Playwright browser automation
- Connects to Ollama using Docker Compose service name (`ollama`)
- Executes browser automation tasks with LLM reasoning

## Configuration

### Changing the LLM Model

Edit `docker-compose.yml` to use a different Ollama model:
```yaml
command: >
  sh -c "
  ollama serve &
  sleep 5 &&
  ollama pull <your-model-name> &&
  wait
  "
```

And update `fara_script.py`:
```python
client_config = {
    "model": "<your-model-name>",
    "base_url": "http://ollama:11434/v1",
    "api_key": "ollama",
    "timeout": 30.0
}
```

### Running Without LLM

To run FARA without LLM (browser-only mode), edit `fara_script.py`:
```python
# Comment out the LLM config
# client_config = { ... }

# Set to None
client_config = None
```

### Customizing the Task

Edit the task in `fara_script.py`:
```python
task = "Your browser automation task here"
```

## Networking

The containers communicate using Docker Compose's default bridge network:
- Fara connects to Ollama at `http://ollama:11434/v1`
- This works on all platforms (Linux, macOS, Windows)
- No need for `host.docker.internal` or special host networking

## Troubleshooting

### Ollama Not Ready
If you see connection errors, the ollama service might not be fully initialized. The healthcheck should prevent this, but you can manually check:
```bash
docker compose logs ollama
```

### Download Directory
Results are saved to `./results/` and downloads to `./downloads/` on the host machine.

### Viewing Logs
```bash
# View all logs
docker compose logs

# View specific service logs
docker compose logs fara
docker compose logs ollama

# Follow logs in real-time
docker compose logs -f
```

## Development

To modify the Fara script:
1. Edit `fara_script.py`
2. Rebuild the container:
```bash
docker compose up --build fara
```

## License

This project uses Microsoft's FARA framework. Please refer to the [FARA repository](https://github.com/microsoft/fara) for license information.
