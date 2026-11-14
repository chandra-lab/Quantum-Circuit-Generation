# LLM-Based Quantum Circuit Generation

A research framework that turns a natural-language description of a quantum problem into an executable circuit. A language model returns a structured JSON specification. The backend validates that specification, builds a Qiskit circuit through a fixed gate map, simulates it with Qiskit Aer, and returns the diagram, counts, and probabilities. The React UI shows each of those artifacts.

The framework is meant to be extended. This repository is an MVP of that path. It does not report circuit-generation results, and it does not claim that a language model has been evaluated, fine-tuned, or compared against a baseline. The only measured numbers are from the offline classifier on synthetic data in [PyTorch experimentation workflow](#pytorch-experimentation-workflow).

## Research motivation

Natural language is a convenient way to sketch a quantum algorithm, but a generated Python string is a poor interface: it is hard to validate, easy to execute unsafely, and awkward to reuse in later experiments. This project separates three concerns:

1. The model proposes a **circuit specification**, not code.
2. A schema and an allowlist decide whether that specification is executable.
3. A simulator and a diagram are produced from the circuit the backend actually built.

Later work can swap the language-model provider, persist experiment history, or add learning-based circuit optimization. Those pieces have an interface or a noted dependency here. They are not implemented.

## Architecture

```mermaid
flowchart LR
  user[Researcher]
  ui[React UI]
  nginx[nginx /api proxy]
  api[FastAPI]
  llm[LLM provider interface]
  groq[Groq JSON output]
  validate[Pydantic validation]
  gates[Restricted gate map]
  qiskit[Qiskit QuantumCircuit]
  aer[Qiskit Aer]
  svg[Circuit SVG]
  history[(Optional SQLite history)]

  user --> ui
  ui -->|relative /api| nginx
  nginx --> api
  api --> llm
  llm --> groq
  api --> validate
  validate --> gates
  gates --> qiskit
  qiskit --> aer
  qiskit --> svg
  api -.-> history
```

The browser talks only to the frontend origin. nginx proxies `/api` to the backend service, so the UI uses relative URLs and does not embed `localhost`. Swagger remains available on the published backend port.

Generation does not wait on the database. If SQLite cannot be opened or a write fails, the request still returns the circuit result.

## Stack

| Layer | Choice |
| --- | --- |
| UI | React, Vite, TypeScript, Tailwind CSS |
| API | Python 3.11, FastAPI, Pydantic v2 |
| Language model | Groq via `GROQ_API_KEY` and `GROQ_MODEL`. Structured JSON when the model supports it. `GROQ_VISION_MODEL` reads images |
| File prompts | `pypdf` for PDF text, `pypdfium2` and Pillow to render scanned pages |
| Quantum | Qiskit and Qiskit Aer. No `eval` or `exec`. No model-authored Python |
| Machine learning | CPU PyTorch in the backend image. The API imports it only for a version check. The offline `backend/research` classifier uses it |
| History | Optional SQLite behind a repository interface |
| Runtime | Docker Compose. The host does not need Python or Node |

## Features

- Natural-language generation returns a circuit spec, validation status, and model metadata.
- The prompt box also takes an image or a PDF as the question. See [File prompts](#file-prompts).
- A missing Groq key is a configuration error. The service does not invent a template circuit in its place.
- Validation rejects unsupported gates, bad qubit or clbit indexes, colliding measurement bits, identical control and target, and non-finite rotation angles.
- Supported gates, stored in lowercase: `i`, `x`, `y`, `z`, `h`, `s`, `t`, `rx`, `ry`, `rz`, `cx`, `cz`, `swap`.
- Simulation uses Qiskit Aer with a configurable shot count. Counts and probabilities (`count / shots`) come back with an SVG of the circuit that was built.
- Four predefined reference circuits (Bell, superposition, bit flip, GHZ) can be simulated with no API key. The UI labels them as reference circuits, not model output.
- Request body size, qubit count, shot count, and language-model attempts are bounded by environment variables.
- Malformed JSON, provider errors, and rate limits surface as structured HTTP errors. Attempts back off and stop at `LLM_MAX_RETRIES`.

## Learner and Pro modes

A **Learner / Pro** toggle sits at the top right of the page header. It is a two-option radio group, so arrow keys, Home, and End move the selection. The choice is stored in `localStorage` under `qcg.viewMode`, so a reload keeps it.

- **Pro** is the default. It is the full technical view: stats, gate list, circuit diagram, counts, probabilities, and the raw spec JSON.
- **Learner** explains the same result in plain language for someone new to quantum computing: what the circuit is meant to do (from its name and description), what each gate does in the order applied, what the measurements store and how to read Qiskit bitstrings (the rightmost character is classical bit 0), the outcome percentages for the actual shot count and why small deviations are shot noise, a "Key idea" line for recognisable patterns (superposition, Bell, GHZ, deterministic bit flip), and the validation status. The circuit diagram and histogram stay visible. The stats, gate list, and spec JSON move behind **Show technical details**.

Explanations come from the backend and are built from the validated spec and the simulator counts by fixed rules in `backend/app/services/explanation.py`. No language model is called, so they work without a Groq key and for the reference circuits. They describe this simulation only and do not report experimental results.

- Successful `POST /api/circuits/simulate` and `POST /api/circuits/generate-and-simulate` responses add a `learner_explanation` object with `pattern`, `overview`, `steps`, `measurements`, `bit_order`, `outcome`, `key_idea`, `validation`, and `errors`. Every existing field is unchanged.
- `validation_error` (422) and `measurements_required` (400) error bodies add a top-level `learner_explanation` whose `errors` list explains each validation detail in plain words. The `error` object keeps its shape.

## Circuit specification

```json
{
  "circuit_name": "Bell State",
  "num_qubits": 2,
  "num_clbits": 2,
  "gates": [
    {"gate": "h", "qubits": [0]},
    {"gate": "cx", "qubits": [0, 1]}
  ],
  "measurements": [
    {"qubit": 0, "clbit": 0},
    {"qubit": 1, "clbit": 1}
  ],
  "description": "Creates an entangled Bell state."
}
```

`rx`, `ry`, and `rz` add a finite numeric `parameter` in radians. Other gates must not include one. Gate names are accepted in any letter case and stored in lowercase. `cx` and `cz` qubits are `[control, target]` and must differ. `swap` qubits must differ. Measurement clbits cannot collide. `num_qubits` and `num_clbits` must cover every index and stay within `MAX_QUBITS`.

Product simulations require at least one measurement. Bitstrings follow Qiskit order: the rightmost bit is classical bit 0.

## Groq setup

1. Create an API key in the [Groq console](https://console.groq.com/).
2. Copy `.env.example` to `.env`.
3. Set `GROQ_API_KEY`.
4. Leave `GROQ_MODEL` as `openai/gpt-oss-20b`, or set another current Groq model that supports JSON output. The default model supports strict JSON schema mode. If a configured model rejects schema mode, the client retries once with JSON object mode inside the same attempt budget.

The key is read only on the server. It is not sent to the browser, not included in `/api/health`, and redacted if it would appear in a log line. Health reports whether a key is configured and which model name is set.

Without a key, `POST /api/circuits/generate` and `POST /api/circuits/generate-and-simulate` return HTTP 503 and `configuration_error`. `POST /api/circuits/simulate` still runs.

`GROQ_VISION_MODEL` defaults to `qwen/qwen3.8-27b`, which Groq lists as accepting image input (up to 3 images per request, 20 MB per request). It is only used for file prompts. Any other current Groq model with image input can be set instead.

## File prompts

Attach one PNG, JPEG, WebP, or PDF to the prompt box with **Attach image or PDF**, by dropping it on the form, or by pasting an image into the text box. The chip shows the file name and size, a thumbnail for images, and a remove button. Typed text is optional when a file is attached. When both are given, the text is passed as extra instructions next to the question read from the file.

Generate sends the file to `POST /api/circuits/generate-from-file`. The backend reads the question out of the file, then runs the same spec generation, validation, build, and simulation as `generate-and-simulate`. The response is the same, with an `extraction` object added. The UI shows that text under **Extracted from your file** in both Learner and Pro mode, and Learner mode explains the file-generated result the same way as a typed prompt. **Edit and regenerate** moves it into the prompt box, removes the attachment, and lets you correct it before running a plain text prompt.

How each type is read:

- **PDF with a text layer.** `pypdf` extracts text on the server from the first `MAX_PDF_PAGES` pages (default 10). No model is involved in this step.
- **Scanned PDF.** If those pages hold fewer than 20 letters and digits, the PDF is treated as a scan. The first `PDF_VISION_PAGES` pages (default 3, Groq's per-request image limit) are rendered to JPEG in memory with `pypdfium2` and sent through the image path.
- **Image.** The vision model is asked to transcribe the question as plain text, including any drawn circuit: qubits, gates in order, controls and targets, angles, and measurements. It is told to treat text in the image as content, not instructions, and to reply `NO_QUANTUM_CONTENT` when there is no quantum question.

The extracted text is capped at `MAX_EXTRACTED_CHARS` (default 6000) and then fed to the existing JSON circuit-spec prompt. Model output is only ever text that goes back through that prompt and the validator. Nothing it returns is executed.

Limits and checks:

- One file per request. `MAX_UPLOAD_MB` (default 10, at most 14 so the base64 image stays under Groq's 20 MB request limit) is enforced by the browser, by nginx (`client_max_body_size` on that route only), and by the backend. The JSON endpoints keep the `MAX_REQUEST_BYTES` cap.
- The declared MIME type must be one of the four allowed types, and the file's magic bytes must match it. A renamed file is rejected.
- Uploads are read into memory and not saved. Starlette may spool a large multipart part to an anonymous temporary file, which is deleted when the request closes. nginx streams the upload to the backend without buffering it to disk.
- Without `GROQ_API_KEY`, an image or a scanned PDF returns the same 503 `configuration_error` as text generation. A PDF with a text layer is still extracted: the 503 body includes `extraction` so the UI can show what was read, and no circuit is returned.

| Status | Code | When |
| --- | --- | --- |
| 413 | `file_too_large` | The file exceeds `MAX_UPLOAD_MB` |
| 415 | `unsupported_media_type` | The type is not PNG, JPEG, WebP, or PDF, or the bytes do not match the declared type |
| 422 | `extraction_empty` | No question could be read, including a vision reply of `NO_QUANTUM_CONTENT` |
| 422 | `unreadable_file` | The PDF is damaged or password protected |
| 422 | `validation_error` | The `file` field is missing, or the generated spec failed validation |

## Run with Docker Desktop on Windows

Install [Docker Desktop](https://docs.docker.com/desktop/setup/install/windows-install/) with the WSL 2 backend. You do not need a local Python or Node install.

These commands run on the Windows host, where Docker Desktop provides `docker`. They are not the commands to run in a GitHub Codespace terminal. Use the Codespaces section for that shell.

In PowerShell, from the repository root:

```powershell
Copy-Item .env.example .env
notepad .env
docker compose up --build
```

In Command Prompt:

```bat
copy .env.example .env
docker compose up --build
```

Then open:

- Frontend: http://localhost:8080
- API docs: http://localhost:8000/docs

Stop the stack:

```powershell
docker compose down
```

The first build downloads CPU PyTorch, Qiskit, and Aer. It is large and can take several minutes. Later builds reuse layers.

If ports 8080 or 8000 are already taken, stop the other process or change the left-hand side of the `ports` entries in `docker-compose.yml`.

Keeping the clone inside the WSL filesystem is faster, but the same commands work from a Windows checkout that Docker Desktop can mount.

## GitHub Codespaces

The Codespace terminal is inside the dev container. The Docker Desktop commands in the previous section run on the Windows host. In the Codespace, rebuild the container, then run `docker compose up --build` from `/workspace`.

`.devcontainer/devcontainer.json` attaches VS Code to the `workspace` service in `.devcontainer/compose.workspace.yml`. That service is the attach target only. It is not one of the app containers. `docker compose up` from the repository root reads `docker-compose.yml` and starts the frontend and the backend. It does not start `workspace`, on a Windows host or inside the Codespace.

The repository is bind-mounted at `/workspace`. Compose resolves paths in the override relative to `docker-compose.yml` (the first file in `dockerComposeFile`). The mount source is `.`, the repository root. A mount of `..` would attach the parent of the clone. In Codespaces that parent is outside the workspace mount, so Explorer shows an empty folder named `workspace` and VS Code reports that the workspace does not exist.

The workspace image does not install Docker itself. The dev container feature `ghcr.io/devcontainers/features/docker-in-docker` installs the Docker CLI, Compose v2, and a daemon inside this container. A host socket is not available here, so Docker outside of Docker is not used. Rebuild the container before `docker` is on `PATH`. The feature needs a privileged container, which `compose.workspace.yml` sets. Codespaces forwards ports that listen in this container, so the app stack is started here rather than as a sibling service.

On creation the dev container copies `.env.example` to `.env` when `.env` is absent. A Groq key is optional. Put one in a Codespaces secret named `GROQ_API_KEY`, or edit `.env` after the environment is up. Do not commit `.env`. Reference circuits simulate without a key.

After the container is up, the Explorer root (`/workspace`) should list `frontend/`, `backend/`, `README.md`, and `docker-compose.yml`.

1. Open the repository in a Codespace. If this Codespace was created before the Docker feature was added, open the Command Palette and run **Codespaces: Rebuild Container**, or create a new codespace. Reloading the window keeps the previous image and the previous mount.
2. Wait until the rebuild finishes. The integrated terminal starts in `/workspace`.
3. From `/workspace`, build and start the frontend and the backend:

   ```bash
   docker compose up --build
   ```

   The first build downloads CPU PyTorch, Qiskit, and Aer. It is large and can take several minutes. The frontend listens on port **8080**. The backend listens on port **8000**.

4. Open the forwarded **Frontend** port **8080**. The port is marked public so a preview link can be shared for a demo.
5. Open forwarded port **8000** and visit `/docs` for Swagger.
6. Generate a circuit, or simulate a predefined reference circuit if no key is set.

Stop the app with `docker compose down` from `/workspace`. After a change to the dev container definition or this mount, run **Codespaces: Rebuild Container** again, then run `docker compose up --build` from `/workspace`. Day-to-day UI or API edits on a machine with Docker Desktop still use `docker compose up --build` in a host shell at the repository root.

## API

All JSON errors use this shape:

```json
{
  "error": {
    "code": "validation_error",
    "message": "Human-readable summary.",
    "details": ["field level messages"]
  }
}
```

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/health` | API status, service status, Aer availability, PyTorch availability and version, whether Groq is configured |
| `GET` | `/api/circuits/examples` | Example prompts and the predefined reference specs |
| `POST` | `/api/circuits/generate` | Body `{"prompt": "..."}`. Returns the spec, validation status, and model metadata |
| `POST` | `/api/circuits/validate` | Body is a circuit spec, or `{"spec": {...}}`. Returns `valid`, `errors`, and the normalized spec |
| `POST` | `/api/circuits/simulate` | Body `{"spec": {...}, "shots": 1000}`. Counts, probabilities, metadata, SVG, and `learner_explanation`. No Groq key required |
| `POST` | `/api/circuits/generate-and-simulate` | Body `{"prompt": "...", "shots": 1000}`. Spec, validation, diagram, counts, probabilities, and `learner_explanation` |
| `POST` | `/api/circuits/generate-from-file` | Multipart fields `file`, optional `prompt`, optional `shots`. The generate-and-simulate response plus `extraction` |

`shots` defaults to `SHOTS` (1000) and must be between 1 and `MAX_SHOTS`. Oversized bodies return HTTP 413. Invalid specs on simulate return HTTP 422. Provider rate limits return HTTP 429. Provider failures return HTTP 502. A timed-out model call returns HTTP 504.

Direct browser calls to port 8000 are limited by `CORS_ORIGINS`. The Compose UI does not need that, because nginx makes `/api` same-origin.

## Example prompts

The UI can drop these into the prompt box:

1. Generate a Bell State using two qubits.
2. Create a quantum superposition using a Hadamard gate.
3. Create a quantum circuit with three qubits that prepares a GHZ state: Hadamard on qubit 0, CNOT from 0 to 1, CNOT from 0 to 2, and measure all three qubits.
4. Apply X, H, and CNOT gates to a quantum circuit.
5. Create a quantum measurement circuit.
6. Quantum bit flip: prepare one qubit in the zero state, apply a single X gate, and measure that qubit.

Prompts 1, 2, 3, and 6 have predefined reference circuits. Prompt 3 is the GHZ case: three qubits, H on qubit 0, CNOT 0→1, CNOT 0→2, measure all. Prompts 4 and 5 are open-ended and only run through the language model.

Reference outcomes on an ideal simulator, with a few percent of sampling noise at a few thousand shots:

| Circuit | Dominant outcomes |
| --- | --- |
| Bell | about half `00` and half `11` |
| Superposition | about half `0` and half `1` |
| Bit flip | about all `1` |
| GHZ | about half `000` and half `111` |

## Testing

Backend tests use deterministic specs and never call Groq. File prompt tests build their PDFs in memory and use a fake provider for vision and spec generation.

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pytest
```

On Windows, activate with `.venv\Scripts\activate`.

Frontend tests and the typecheck:

```bash
cd frontend
npm ci
npm test
npm run typecheck
npm run build
```

`ResultsPanel.pro.test.tsx` snapshots the Pro results markup, so an accidental change to the Pro view fails the suite.

Check the Compose file without building images:

```bash
docker compose config
```

`requirements.txt` does not install PyTorch. Local health checks report PyTorch as unavailable unless you install a CPU wheel yourself. The backend image installs it and fails the build if `import torch` or Aer does not succeed.

## PyTorch

CPU PyTorch is installed in `backend/Dockerfile` from the official CPU index (`https://download.pytorch.org/whl/cpu`). The image build imports it and prints the version. `/api/health` reports that version and nothing else about the library.

Simulation and the API do not import PyTorch. The only trained model is the offline classifier described in [PyTorch experimentation workflow](#pytorch-experimentation-workflow), and no weights are downloaded.

Possible later uses, none of which are implemented and none of which have results in this repository:

- Fine-tuning a model on circuit-specification pairs.
- Quantum reasoning experiments that score generated specs.
- Offline evaluation of language-model circuit proposals.
- Learned circuit optimization, with Aer still used as the executor.

## PyTorch experimentation workflow

`backend/research/` is an offline experiment harness. It trains a small **circuit-category classifier on synthetic, rule-labelled circuit specs**. It does not generate circuits, it is not compared with the Groq model, and nothing in the web app calls it. It is a reproducible baseline for future research: a fixed dataset, documented features, a model, splits, metrics, and saved runs that later experiments can replace one piece at a time.

The FastAPI process never imports `research`, and `app` imports no torch at startup (a test checks this). Only `research/model.py`, `train.py` and `evaluate.py` import torch. Dataset generation and feature extraction need just the app's own dependencies.

### Dataset

`python -m research generate-dataset` writes `backend/research/data/circuits.jsonl` (one `{"id", "category", "spec"}` object per line) and a `circuits.meta.json` with class counts, the generator config and a SHA-256 of the records. The default config produces 300 specs for each of 7 categories (2,100 in total), with a fixed seed. Every spec is passed through the app's `normalize_spec` with `MAX_QUBITS=8` and `max_gates=128`, so it is a valid `CircuitSpec`.

| Category | Construction |
| --- | --- |
| `superposition` | H on a random non-empty subset of qubits, sometimes followed by one z, s or t on one of those qubits |
| `bell` | H on a control and one CX to a target, with optional X on the target first and Z on the control after (the four Bell states) |
| `ghz` | H on a root, then CX gates in a star or a chain over 3 or more qubits |
| `basis_state` | X on a random non-empty subset (bit flips), sometimes one Z |
| `rotation` | 3 to 12 rx/ry/rz gates with \|angle\| ≥ 0.1 on random qubits, at most one extra h/s/t, no two-qubit gates |
| `swap_permutation` | X on a non-empty subset, then 1 to 4 SWAPs |
| `random_mixed` | 6 to 16 gates from the full allowlist, always including a CX or CZ, a rotation, and one of h/y/s/t |

Qubit counts are drawn up to 8 (at least 2 for two-qubit categories and 3 for GHZ), qubits and angles are random, and up to 4 padding operations are inserted that do not change the prepared state: an identity gate anywhere, or an adjacent `x x` or `z z` pair on one qubit. Every qubit is measured. The label is the recipe that built the spec, so it is correct by construction.

### Features

`research/features.py` turns a spec into 28 numbers, in a fixed order. Each run saves the descriptions to `features.json`.

| Feature | Definition |
| --- | --- |
| `num_qubits`, `num_clbits` | Register sizes |
| `total_gates` | Entries in `gates`, identity included. Measurements are not counted |
| `count_<gate>` | One count for each supported gate: `cx cz h i rx ry rz s swap t x y z` |
| `single_qubit_gates`, `two_qubit_gates` | Gates acting on one qubit, and on two (cx, cz, swap) |
| `parametric_gates` | rx + ry + rz |
| `depth` | `QuantumCircuit.depth()` of the circuit from the app's `build_circuit`, measurements included |
| `num_measurements` | Entries in `measurements` |
| `entangling_gates` | cx + cz (SWAP is excluded because it does not entangle) |
| `entangling_pairs` | Distinct unordered qubit pairs joined by cx or cz |
| `largest_entangling_component` | Qubits in the largest connected component of the cx/cz graph. An isolated qubit counts as 1 |
| `interaction_pairs`, `largest_interaction_component` | The same two features, over a graph that also includes SWAP edges |
| `active_qubits` | Qubits touched by any non-identity gate |
| `h_before_cx_control` | 1 if some cx's control qubit had an h earlier in the gate list |

### Model and training

The model is an MLP (28 → 64 → 64 → 7, ReLU, dropout 0.1) trained with cross-entropy and Adam (learning rate 1e-3, weight decay 1e-4, batch size 64). The data gets a stratified 70/15/15 train/validation/test split. A standard scaler is fitted on the training split only. Validation runs after every epoch. The best checkpoint is chosen by validation macro F1, with ties going to the lower validation loss. Early stopping waits 10 epochs without improvement, up to a maximum of 60 epochs. The test split is scored once, with the best checkpoint.

Metrics are computed in NumPy (no scikit-learn): accuracy, macro and per-class precision, recall and F1, and a confusion matrix for validation and test. Every hyperparameter is in `research/configs/default.json`, and `research/configs/smoke.json` is a seconds-long sanity run.

Determinism: the Python, NumPy and torch seeds come from the config. The run calls `torch.use_deterministic_algorithms(True)`, uses one CPU thread and draws batches from a seeded generator. Only the CPU device is accepted.

### Commands

With Docker, the `research` service is in a Compose profile, so `docker compose up` neither builds nor starts it. It reuses the backend image's build cache, bind-mounts `backend/research/{runs,data}` so outputs land on the host, and mounts `backend/research/configs` read-only:

```bash
docker compose run --rm --build research generate-dataset
docker compose run --rm research train
docker compose run --rm research train --config research/configs/smoke.json
docker compose run --rm research evaluate --run-dir research/runs/<run-name>
docker compose run --rm research evaluate --run-dir research/runs/<run-name> --checkpoint last
```

The container writes files as uid:gid `1000:1000` by default. On Linux, if your user has another id, set `RESEARCH_UID=$(id -u) RESEARCH_GID=$(id -g)`. Pass `--build` again after changing code under `backend/research/`. The plain backend service can run the same commands, but its outputs stay inside the container: `docker compose run --rm backend python -m research train`.

Locally, from `backend/` with the backend venv active:

```bash
pip install "torch==2.6.0+cpu" --index-url https://download.pytorch.org/whl/cpu
python -m research generate-dataset
python -m research train --config research/configs/default.json   # or: python -m research.train
python -m research evaluate --run-dir research/runs/<run-name>
```

Useful flags are `--seed` (overrides the dataset, split and training seeds together), `--samples-per-class`, `--epochs`, `--name`, `--run-dir` and `--dataset`. `evaluate --dataset <file.jsonl>` scores every sample in another dataset instead of the run's test split. Relative paths are resolved against `backend/`.

Tests: `pytest` in `backend/` runs the research tests too. The feature, dataset and import tests need no torch. The training and reproducibility tests are skipped when torch is not installed, and they run in a few seconds when it is.

### Outputs

Each run is written to `backend/research/runs/<name>-<UTC timestamp>/` (git-ignored apart from its README) and contains:

- `checkpoints/best.pt` and `checkpoints/last.pt`
- `config.json`, `label_map.json`, `scaler.json` (train-split means and scales), `features.json`
- `history.csv` and `loss_curve.png`, with per-epoch train and validation loss, validation accuracy and validation macro F1
- `metrics.json`, `confusion_matrix_{val,test}.csv` and `per_class_{val,test}.csv`
- `evaluation_<checkpoint>.json`, written by `evaluate`

### Reproducing a run

Use the same config and seed. If the dataset file is missing, or its metadata does not match the config, it is regenerated. The default dataset's SHA-256 is `68f97ff8c79781b7f16035e9767326caf7cda69aee1abdba8a80a013fad477f6`. A test trains twice with one seed and requires identical per-epoch history and validation and test metrics. `run_training` with the default config produced the same `metrics.json` and `history.csv` in the Docker image and in a local Python 3.11 venv with torch 2.6.0+cpu. Other torch versions or CPUs may differ in the last digits.

### Measured results

These come from **a single run on synthetic data**: the default config with seed 1234 and torch 2.6.0+cpu. The run used 1,470 training, 315 validation and 315 test specs (45 per class in each evaluation split) and trained for all 60 epochs. The best checkpoint was epoch 60.

| Split | Accuracy | Macro precision | Macro recall | Macro F1 | Loss |
| --- | --- | --- | --- | --- | --- |
| Validation | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.0009 |
| Test | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.0019 |

Every class scored precision, recall and F1 of 1.0 on test, and the test confusion matrix is diagonal (45 per class). The 5-epoch `smoke.json` run, with 30 specs per class, a 32-unit hidden layer and seed 7, scored 0.8810 test accuracy and 0.8818 macro F1 on 42 test specs.

A perfect score is the expected result, not evidence of a strong model. The labels come from structural rules, and the features expose that structure almost directly: for example, "no H, only X gates" is a basis state, and "rotations with no two-qubit gates" is a rotation circuit.

### Limitations

- The data is synthetic and the labels are rule-derived. The classifier says nothing about language-model output, real algorithms, hardware or noise, and it is not a circuit generator.
- The categories are separable from hand-made features, so accuracy near 1.0 is the ceiling to expect rather than a finding. Harder tasks need new labels: for example, simulated properties such as entanglement entropy, or near-miss specs that break a category's rule.
- The features ignore gate order, apart from `depth` and `h_before_cx_control`, and ignore angles. Two specs with the same gate multiset look almost identical to the model.
- There is one run per config. No variance across seeds, no hyperparameter search and no baseline model are reported.
- There is no second head. A binary "is entangling" target was left out because, defined from the construction, it would just restate the category, and defined from the gates, it would just restate a feature.
- Only the CPU device is supported, and no GPU dependencies are added.

## Project layout

```
backend/app/api          HTTP routes
backend/app/core         settings and error types
backend/app/schemas      circuit spec
backend/app/services     Groq provider, retries, history, workflows, file extraction
backend/app/quantum      gate map, builder, Aer, SVG, reference specs
backend/app/utils        redaction and shot limits
backend/research         offline PyTorch circuit-category classifier (not imported by the API)
backend/tests            pytest
frontend/src/components  UI pieces
frontend/src/pages       home page
frontend/src/services    API client
frontend/src/hooks       request state
frontend/src/types       shared response types
```

Another language-model provider can implement `CircuitLLM` in `backend/app/services/llm/base.py`: `complete` for spec generation and `transcribe_images` for file prompts. Only the Groq adapter is wired up.

## Troubleshooting

- **503 configuration_error.** `GROQ_API_KEY` is empty. Reference circuits still simulate. Restart the backend container after editing `.env`, because Compose reads the file when the container is created.
- **429 rate_limit.** Groq asked the client to slow down. The service already retries with backoff. Wait and send the prompt again.
- **502 llm_malformed_json or llm_error.** The model reply was not a usable JSON spec, or the HTTP call failed. Rephrase the prompt, confirm the key, and confirm `GROQ_MODEL` supports JSON output.
- **422 validation_error.** The spec used an unknown gate, an index outside the register, a bad angle, or too many qubits. The `details` array names the problem.
- **400 invalid_shots.** `shots` is below 1 or above `MAX_SHOTS`.
- **413 payload_too_large.** The body exceeded `MAX_REQUEST_BYTES`.
- **413 file_too_large.** The attached file exceeded `MAX_UPLOAD_MB`. A file within a few KB of the limit can also be stopped by nginx, because its limit covers the whole multipart body. Restart both containers after changing `MAX_UPLOAD_MB`.
- **415 unsupported_media_type.** Attach a PNG, JPEG, WebP, or PDF. A file renamed to one of those extensions is rejected when its bytes do not match.
- **422 extraction_empty.** Nothing readable was found. For a photo, crop to the question and retake it in good light, or type the question instead.
- **Frontend cannot reach the API in Compose.** Use http://localhost:8080 so the browser stays on the nginx origin. Do not point the built UI at `localhost:8000`.
- **Codespace says the workspace does not exist, or Explorer shows an empty `workspace` folder.** The dev container attaches to the `workspace` service, which bind-mounts the repository root at `/workspace`. Rebuild the container (**Codespaces: Rebuild Container**) or create a new codespace after pulling the fix. Reloading the window does not remount the folder.
- **`docker: command not found` in the Codespace terminal.** That shell is inside the dev container. The Windows Docker Desktop commands are for a host shell. Rebuild the container (**Codespaces: Rebuild Container**) so the Docker-in-Docker feature is installed, then from `/workspace` run `docker compose up --build`.
- **Codespace preview is blank after `docker compose up`.** The backend health check waits until Aer imports. The frontend container starts after that check passes. Forwarded ports 8080 and 8000 appear once those containers are listening.
- **Diagram text looks sparse.** The backend image installs DejaVu so Matplotlib can label gates. A local venv also needs Matplotlib, which `requirements.txt` installs.
- **Port already allocated.** Change `8080` or `8000` on the host side of `docker-compose.yml`, and add the new frontend origin to `CORS_ORIGINS` if you call the API from the browser on that origin.

## Limitations

- No fine-tuning of the language model. The only trained checkpoint is the offline synthetic-data classifier in `backend/research`, which is not used by the app.
- No circuit optimizer and no compiler beyond the gates Aer can run directly.
- One live language-model adapter. The provider interface is there so another adapter can be added later.
- `MAX_QUBITS` defaults to 8 and cannot be configured above 16. This is a statevector-sized simulator, not a device.
- The simulator is Qiskit Aer, not quantum hardware. Noise models and backends are not exposed.
- History is a small optional table. It is not an experiment tracker, and a database failure does not change the circuit result.
- The model can still propose a spec that is valid and not what you meant. Validation checks structure, not intent.
- File prompts take one file at a time. PDF text extraction reads `MAX_PDF_PAGES` pages, and scanned PDFs only have their first 3 pages read by the vision model.
- A scan is detected per document, not per page: a PDF that mixes text pages and scanned pages is read from its text layer only.
- Vision transcription of hand-drawn or dense circuit diagrams can miss or misplace gates. Check the extracted text before trusting the circuit.
- PDF text from multi-column layouts, equations, or circuit figures drawn as vector graphics may come out out of order or not at all.
