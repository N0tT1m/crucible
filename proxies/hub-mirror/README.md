# hub-mirror (L5)

Local Hugging Face-shaped mirror that serves typosquatted model names with
poisoned weights and tampered model cards. Targets the *download
pipeline*, not the model itself — tests whether tooling that resolves
model names has any trust assumptions worth attacking.

## Run

```bash
go build -o hub-mirror .
./hub-mirror -addr :7900 -models ./fake-models
```

Where `fake-models/` looks like:

```
fake-models/
└── meta-llama-3.2-3B/                # canonical name
    ├── README.md                     # tampered model card
    ├── config.json
    └── model.safetensors             # poisoned weights
```

## Endpoints (HF-API-shaped)

| Path                                       | Description                        |
|--------------------------------------------|------------------------------------|
| `/api/models/<name>`                       | model metadata (HF JSON shape)     |
| `/<name>/resolve/main/<file>`              | raw file fetch                     |
| `/<name>/resolve/main/README.md`           | tampered model card                |
| `/index.json`                              | list of names served (incl. squats)|

The squat list is generated from the canonical name with common typos:
`meta-llama-3.2-3B` → `meta-Ilama-3.2-3B`, `meta-llama-3.2-3b`,
`meta-llama-3-2-3B`, etc.

Every request is logged as one JSONL line on stdout.
