# Evaluation set

`manifest.json` lists photos with expected findings. Only publicly licensed images
(e.g. Wikimedia Commons, CC BY / CC0) may be added, each with `source` and `license`.
Image files are not committed to keep the repo small; download them next to the manifest
using the `source` URLs. Format and metrics: `src/inspection_report/evaluate.py`.

```json
{"images": [{"image": "tyre1.jpg", "source": "https://commons.wikimedia.org/...", "license": "CC BY-SA 4.0",
             "findings": [{"component": "tyre", "condition": "worn", "severity": "medium"}]}]}
```

Run: `inspection-report eval data/eval/manifest.json`
