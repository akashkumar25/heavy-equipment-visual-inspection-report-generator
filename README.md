# heavy-equipment-visual-inspection-report-generator

Turn photos of heavy equipment into structured inspection reports with a vision-language model. Runs on CPU.

> **Status: scaffold.** Project structure, configuration, CLI and CI are in place. The VLM backend, report schema and UI are on the roadmap below.

## Goal

Upload photos of a machine (tyres, tracks, hoses, buckets, cracks, leaks) and get a structured report per finding:

| Field | Meaning |
|---|---|
| component | the part that was inspected |
| condition | observed condition |
| severity | how serious the finding is |
| recommended action | what to do next |

Output as JSON and PDF.

## Design

- **CPU first.** The default backend is a small open VLM (SmolVLM-256M) run locally with `transformers`. No GPU needed.
- **Optional API.** Set `INSPECTION_BACKEND=api` to use any OpenAI-compatible endpoint (a local Ollama server or a hosted API).
- **Public data only.** Sample images and evaluation data come from public datasets.

## Install

```bash
pip install -e ".[dev]"
inspection-report status
```

Or with Docker:

```bash
docker compose up --build
```

Copy `.env.example` to `.env` to change the backend or model. Put photos in `data/images/`.

## Development

```bash
ruff check .
pytest
```

## Roadmap

- [x] Scaffold: package layout, settings, CLI, tests, CI, Docker
- [ ] Small VLM on CPU with optional API backend
- [ ] Structured output schema with validation and retry on invalid output
- [ ] Report rendering (Markdown/PDF) and Gradio UI
- [ ] Small public-image evaluation set and accuracy table

## Demo

![demo](docs/demo.gif)

_Demo GIF placeholder, to be recorded once the UI exists._

## License

MIT
