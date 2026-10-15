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

## Try the VLM backend

```bash
pip install -e ".[local]"          # transformers + torch (CPU) for the local backend
inspection-report describe data/images/photo.jpg
```

With `INSPECTION_BACKEND=api` the same command sends the photo to the OpenAI-compatible endpoint in `INSPECTION_API_BASE_URL` (default: local Ollama) and needs no extra install. The local model is downloaded from Hugging Face on first use. The backend layer is unit-tested with a mocked HTTP transport; the real SmolVLM path is not run in CI.

## Structured reports

```bash
inspection-report inspect data/images/photo.jpg > report.json
```

The model is asked for JSON matching `InspectionReport` (`schema.py`): a list of findings with `component`, `condition` (good, worn, damaged, leaking, cracked, missing, unknown), `severity` (none to critical), `recommended_action` and optional `notes`. Fenced or prose-wrapped JSON is tolerated; invalid or incomplete output is validated with pydantic and the error is sent back to the model for up to `--attempts` tries (default 3) before failing with a clear message. Tested with scripted fake backends.

## Development

```bash
ruff check .
pytest
```

## Roadmap

- [x] Scaffold: package layout, settings, CLI, tests, CI, Docker
- [x] Small VLM on CPU with optional API backend
- [x] Structured output schema with validation and retry on invalid output
- [ ] Report rendering (Markdown/PDF) and Gradio UI
- [ ] Small public-image evaluation set and accuracy table

## Demo

![demo](docs/demo.gif)

_Demo GIF placeholder, to be recorded once the UI exists._

## License

MIT
