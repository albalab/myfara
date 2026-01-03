# MyFara - FARA Agent with External Ollama

This repository contains a Docker setup to run Microsoft's FARA (Fast Agent for Research Automation) with external Ollama LLM integration.

## Prerequisites

- Docker
- Docker Compose
- An external Ollama container running and connected to the `fara-ollama` network

## External Ollama Setup

This project uses an external Ollama container that must be running in the `fara-ollama` Docker network. 

### Creating the External Network (if not exists)
```bash
docker network create fara-ollama
```

### Running External Ollama Container
If you don't have an Ollama container running yet, you can start one:
```bash
docker run -d \
  --name ollama \
  --network fara-ollama \
  -p 11434:11434 \
  -v ollama_data:/root/.ollama \
  ollama/ollama:latest
```

Then pull the required model:
```bash
docker exec ollama ollama pull llama3.2:3b
```

## Quick Start

1. Clone the repository:
```bash
git clone https://github.com/albalab/myfara.git
cd myfara
```

2. Make sure the external Ollama container is running and connected to `fara-ollama` network

3. Build and run the Fara container:
```bash
docker compose up --build
```

This will:
- Build the Fara agent container
- Connect to the external Ollama service via the `fara-ollama` network
- Execute the browser automation task

## Architecture

The setup consists of two separate components:

### 1. External Ollama Service (managed separately)
- Runs the Ollama LLM server in a separate container
- Connected to the `fara-ollama` Docker network
- Must be running before starting the Fara service
- Accessible at `http://ollama:11434` within the network

### 2. Fara Service (this project)
- Runs the FARA agent with Playwright browser automation
- Connects to the external Ollama service via the `fara-ollama` network
- Executes browser automation tasks with LLM reasoning

## Configuration

### Changing the LLM Model

Update the external Ollama container to pull a different model:
```bash
docker exec ollama ollama pull <your-model-name>
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

The containers communicate using the external `fara-ollama` Docker network:
- Fara connects to Ollama at `http://ollama:11434/v1`
- Both containers must be on the same `fara-ollama` network
- This works on all platforms (Linux, macOS, Windows)

## Troubleshooting

### Ollama Not Ready
If you see connection errors, ensure the external Ollama service is running:
```bash
# Check if Ollama container is running
docker ps | grep ollama

# Check Ollama container logs
docker logs ollama

# Test Ollama API
curl http://localhost:11434/api/tags
```

### Network Issues
Verify the `fara-ollama` network exists and Ollama is connected:
```bash
# List networks
docker network ls

# Inspect the network
docker network inspect fara-ollama
```

### Download Directory
Results are saved to `./results/` and downloads to `./downloads/` on the host machine.

### Viewing Logs
```bash
# View all logs
docker compose logs

# View fara service logs
docker compose logs fara

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
