# MATLAB validation module

This folder checks that MATLAB's quantum simulator gives the same results as the Qiskit backend for the predefined reference circuits. It is an offline cross-check. The web app, the Docker images, and the Python tests do not use MATLAB and do not need it.

The flow has three steps:

1. A Python CLI in the backend exports each circuit's spec and its Qiskit results to JSON in `data/qiskit_results/`.
2. `run_validation.m` rebuilds each circuit in MATLAB, simulates it, and compares the probabilities with the Qiskit results.
3. The comparison is written to `results/` as CSV, JSON, and a text summary, with PNG plots in `results/plots/`.

> **Status.** The MATLAB code here was written against the MathWorks documentation but has not been run in this repository's development environment or CI, because neither has MATLAB. It has been syntax-checked with the MISS_HIT MATLAB parser. The Python export, the Python twin of the comparison logic, and their pytest suites run without MATLAB. No MATLAB results are committed. Run `run_tests` and `run_validation` on a licensed MATLAB install before relying on them.

## Layout

```
matlab/
  README.md                     this file
  run_validation.m              entry point: export -> MATLAB -> comparison -> report and plots
  run_tests.m                   runs the matlab.unittest suite in tests/
  +qcg/                         MATLAB package (call as qcg.<name>)
    loadQiskitExport.m          read one exported JSON file
    circuitFromSpec.m           generic loader: spec -> quantumCircuit
    gateFromSpec.m              gate map for i x y z h s t rx ry rz cx cz swap
    referenceCircuit.m          hand-built Bell, superposition, GHZ, bit flip
    stateProbabilities.m        abs(Amplitudes).^2 for every basis state
    sampleState.m               randsample on a quantumState
    matlabToQiskitLabel.m       bit-order mapping (and qiskitToMatlabLabel.m)
    matlabLabelToClbits.m       MATLAB qubit label -> Qiskit clbit string via the measurement map
    compareDistributions.m      per-state diff, max error, TVD, Hellinger, KL
    chiSquareGoodnessOfFit.m    sampled counts vs exact probabilities
    chiSquareHomogeneity.m      MATLAB counts vs Aer counts
    validateCircuit.m           all checks for one circuit
    plotComparison.m            grouped bar and difference plots
    writeReport.m               CSV, JSON, and text report
  examples/reference_circuits_demo.m   build, simulate, and sample the hand-built circuits
  tests/                        matlab.unittest classes and the shared fixture
  tools/compare.py              Python twin of the comparison logic (standard library only)
  tools/tests/                  pytest for compare.py
  data/qiskit_results/          committed Qiskit export (regenerate with the command below)
  results/                      written by run_validation.m, not committed
```

## Prerequisites and licensing

- **MATLAB R2023a or later.** The MATLAB Support Package for Quantum Computing first shipped in March 2023 for R2023a, and `quantumCircuit`, `simulate`, `randsample`, and the gate functions are all documented as "Since R2023a". MathWorks only offers the newest support package version for installation, and the File Exchange page lists compatibility from R2023a to R2026b. Use a recent release if an older one cannot install the current package.
- **MATLAB Support Package for Quantum Computing.** A free add-on from MathWorks, but it needs a licensed copy of MATLAB. It is proprietary, not open source, and is not included in or redistributed by this repository. Installing and using it means following the MathWorks license terms.
- No other toolbox is needed. The chi-square p-values use base MATLAB `gammainc`, not the Statistics and Machine Learning Toolbox.

Install the support package from the Add-On Explorer:

1. In MATLAB, open **Home > Environment > Add-Ons > Get Add-Ons**.
2. Search for **MATLAB Support Package for Quantum Computing**.
3. Click **Install** and sign in with your MathWorks account when asked.

It is also listed on [File Exchange](https://www.mathworks.com/matlabcentral/fileexchange/125425-matlab-support-package-for-quantum-computing). Check the install with `which quantumCircuit` or `matlabshared.supportpkg.getInstalled`.

MATLAB is not installed in the Docker images, the dev container, or Codespaces, and none of them should have it added. Run the MATLAB part on a desktop or server install that has its own license.

## Step 1: export the Qiskit results

A copy of the export is committed in `data/qiskit_results/`, so you can skip this step and go straight to MATLAB. Regenerate it after changing a reference circuit, Qiskit, or Aer.

The export runs in the backend container. From the repository root, in a Linux, macOS, WSL, or Codespaces shell:

```bash
mkdir -p matlab/data/qiskit_results
docker compose run --rm --no-deps --user "$(id -u):$(id -g)" \
  -v "$(pwd)/matlab/data/qiskit_results:/export" \
  backend python -m app.tools.export_for_matlab --output-dir /export
```

`-v` bind-mounts the host folder at `/export` in the container, so the files land in `matlab/data/qiskit_results/` on the host. `--user` makes them owned by you rather than the image's `appuser`.

In PowerShell on Windows with Docker Desktop (Docker Desktop handles file ownership, so `--user` is not needed):

```powershell
docker compose run --rm --no-deps -v "${PWD}/matlab/data/qiskit_results:/export" backend python -m app.tools.export_for_matlab --output-dir /export
```

If bind mounts are not available, copy the files out with `docker cp`:

```bash
docker compose run --name qcg-matlab-export --no-deps backend \
  python -m app.tools.export_for_matlab --output-dir /tmp/qiskit_results
docker cp qcg-matlab-export:/tmp/qiskit_results/. matlab/data/qiskit_results/
docker rm qcg-matlab-export
```

Without Docker, from `backend/` with the backend requirements installed:

```bash
python -m app.tools.export_for_matlab            # defaults to ../matlab/data/qiskit_results
```

Options: `--shots N` (default 4096), `--seed N` (Aer `seed_simulator`, default 1234), `--circuits bell ghz ...`, `--output-dir DIR`. The files have no timestamps, so a rerun with the same versions, shots, and seed is byte-identical. `backend/tests/test_export_for_matlab.py` fails if the committed copy is out of date.

### Exported circuits

| id | Source | Qubits | Gates | Qiskit exact outcome |
| --- | --- | --- | --- | --- |
| `bell` | `examples.py` | 2 | h, cx | `00` 0.5, `11` 0.5 |
| `superposition` | `examples.py` | 1 | h | `0` 0.5, `1` 0.5 |
| `ghz` | `examples.py` | 3 | h, cx, cx | `000` 0.5, `111` 0.5 |
| `bit_flip` | `examples.py` | 1 | x | `1` 1.0 |
| `bit_order_probe` | validation only | 3 | x, ry, cx | `001` 0.75, `111` 0.25 |
| `gate_coverage` | validation only | 3 | all 13 supported gates | six outcomes, none symmetric |

Bell, GHZ, and the one-qubit circuits read the same with either bit order, so on their own they cannot catch a reversed mapping. The two validation-only circuits are defined in the export CLI, not in the app. They are asymmetric, and `gate_coverage` uses every gate in the allowlist with interference, so a wrong gate, angle, control, or phase changes its probabilities.

### File format (`schema_version` 1)

Each `<id>.json` holds:

- `spec`: the validated circuit spec as the backend stores it (0-based indices), plus `gate_sequence` and `measurements`.
- `bit_ordering`: the Qiskit convention, written out.
- `exact`: from `qiskit.quantum_info.Statevector` on the circuit with measurements removed. `bitstrings` and `probabilities` list all 2^n basis states in Qiskit order; `amplitudes_real` and `amplitudes_imag` are the statevector. `measured_bitstrings` and `measured_probabilities` are the same distribution mapped through the measurement map to the clbit register, which is what Aer counts.
- `sampled`: Aer counts with `shots`, `seed_simulator`, `bitstrings`, `counts`, and `probabilities`.
- `versions`: `qiskit`, `qiskit_aer`, and `python`.

Distributions are stored as parallel arrays rather than objects, because MATLAB `jsondecode` would turn a key like `"00"` into a field named `x00`. `manifest.json` lists the files, shots, seed, and versions.

## Step 2: run in MATLAB

```matlab
cd matlab
run_validation                                   % all circuits, default settings
summary = run_validation(Circuits=["bell" "ghz"], Shots=10000, Seed=7);
run_tests                                        % matlab.unittest suite
run("examples/reference_circuits_demo.m")        % hand-built circuits only
```

`run_validation` options: `DataDir`, `ResultsDir`, `Circuits`, `ExactTolerance` (default `1e-10`), `Alpha` (default `1e-3`), `Shots` (default: the Aer shot count; `0` skips sampling), `Seed` (MATLAB `rng`, default 2026), `MakePlots` (default `true`). It stops with an error if `quantumCircuit` is not on the path.

For each circuit it:

1. Loads the JSON with `qcg.loadQiskitExport`.
2. Builds the circuit with the generic loader `qcg.circuitFromSpec`. For `bell`, `superposition`, `ghz`, and `bit_flip` it also simulates the hand-built `qcg.referenceCircuit` and checks the two agree.
3. Runs `s = simulate(c)` and takes `abs(s.Amplitudes).^2` over `s.BasisStates`, then cross-checks with `querystates(s, Threshold="none")`.
4. Maps the labels to Qiskit order and runs the exact comparison and the state fidelity check.
5. Seeds `rng`, runs `randsample(s, shots)`, maps the measured labels to clbit strings, and runs the sampled comparison.
6. Writes plots and the report.

### Gate mapping

The loader adds 1 to every qubit index. The spec gate names map one to one:

| Spec | MATLAB | Spec qubits |
| --- | --- | --- |
| `i` | `idGate(t)` | `[t]` |
| `x`, `y`, `z` | `xGate(t)`, `yGate(t)`, `zGate(t)` | `[t]` |
| `h`, `s`, `t` | `hGate(t)`, `sGate(t)`, `tGate(t)` | `[t]` |
| `rx`, `ry`, `rz` | `rxGate(t, theta)`, `ryGate(t, theta)`, `rzGate(t, theta)` | `[t]`, `parameter` in radians |
| `cx` | `cxGate(control, target)` | `[control, target]` |
| `cz` | `czGate(control, target)` | `[control, target]` |
| `swap` | `swapGate(t1, t2)` | `[t1, t2]` |

The rotation matrices in the MathWorks pages match Qiskit's (for example `rz` is `diag(exp(-i*theta/2), exp(i*theta/2))` in both), so states agree up to global phase. The loader rejects anything else, the same way the backend validator does. `quantumCircuit` names must start with a letter and contain only letters, digits, and underscores, so `"Bell State"` becomes `"Bell_State"`. MATLAB circuits have no classical register: measurements are applied afterwards from the exported measurement map.

`QuantumState` has no `probabilities` method. MathWorks documents `probability`, `querystates`, and `histogram` on the state, and a `Probabilities` property on the `QuantumMeasurement` that `randsample` returns. The exact check reads the amplitudes directly because the default `querystates` threshold drops states with near-zero probability.

## Outputs

| File | Contents |
| --- | --- |
| `results/exact_comparison.csv` | Circuit, Qiskit bitstring, MATLAB label, both probabilities, absolute difference, for every basis state |
| `results/sampled_comparison.csv` | Circuit, clbit string, Qiskit exact probability, Aer count and probability, MATLAB count and probability, difference vs Aer |
| `results/summary.csv` | One row per circuit with every metric and pass flag |
| `results/summary.json` | Settings, MATLAB and Qiskit versions, and per-circuit metrics |
| `results/summary.txt` | Readable summary table and overall verdicts |
| `results/plots/<id>_probabilities.png` | Grouped bars: Qiskit vs MATLAB exact; Qiskit exact, Aer, and MATLAB sampled |
| `results/plots/<id>_difference.png` | MATLAB minus Qiskit, exact (with the tolerance band) and sampled |

`results/` is in `.gitignore`.

## Comparison methodology

### Bit ordering

This is the most likely source of a false mismatch.

- Qiskit bitstrings are little-endian: the rightmost character is qubit 0 (or clbit 0 for counts).
- MATLAB `quantumState.BasisStates` lists qubit 1 first (leftmost), and MATLAB qubit k is Qiskit qubit k-1.

So the same basis state is the reversed string. With only Qiskit qubit 0 in |1> on three qubits:

| | Label |
| --- | --- |
| Qiskit | `001` |
| MATLAB | `100` |

`qcg.matlabToQiskitLabel` reverses the string, and `qcg.qiskitToMatlabLabel` is the same operation. For sampled counts, `qcg.matlabLabelToClbits` reads Qiskit qubit q from character q+1 of the MATLAB label and writes it into the clbit named by the measurement map, giving the clbit string Aer would report. Every comparison is done in Qiskit order, and the reports show both labels. The `bit_order_probe` circuit fails the exact check if the mapping is skipped, and both test suites check that.

### Exact comparison (primary)

Qiskit `Statevector` probabilities against MATLAB `simulate` probabilities over all 2^n basis states. Metrics, on the union of labels with 0 for a missing label:

- per-state absolute difference `|p_matlab - p_qiskit|`
- max absolute error
- total variation distance, `0.5 * sum |p - q|`
- Hellinger distance, `sqrt(0.5 * sum (sqrt p - sqrt q)^2)`
- KL divergence `KL(qiskit || matlab)` after adding `epsilon = 1e-12` to every state and renormalising, so a zero does not give infinity
- state fidelity `|<psi_qiskit|psi_matlab>|^2`, which ignores global phase

The check passes when the max absolute error is at most `1e-10`, the fidelity is within `1e-10` of 1, and, for the four reference circuits, the hand-built and loader circuits agree within `1e-10`. Both simulators are deterministic statevector codes in double precision, so real differences are around `1e-16`. `1e-10` leaves room for summation order without hiding a wrong gate.

### Sampled comparison (secondary)

MATLAB `randsample` and Aer use different random number generators, so their counts never match exactly, even with seeds. The sampled check asks whether the difference is larger than shot noise:

- **Goodness of fit**: chi-square of the MATLAB counts against the exact measured distribution, `dof = (states with p > 1e-10) - 1`. Any count on a state with exact probability 0 fails the test.
- **Homogeneity**: two-sample chi-square of the MATLAB counts against the Aer counts.
- Both pass when `p >= alpha`, default `alpha = 1e-3`. TVD and Hellinger against Aer and against the exact distribution are reported as effect sizes.
- The Aer counts are also tested against the exact distribution, as a check on the export.

At `alpha = 1e-3`, a correct implementation still fails one test in a thousand by chance. Rerun with another `Seed` before treating a single sampled failure as a mismatch. Chi-square is approximate when an expected count is small; with 4096 shots and these circuits the smallest expected count is about 45.

### Python twin and equivalence

`tools/compare.py` implements the same mapping, metrics, chi-square tests, and tolerances in Python, and each function's docstring names its MATLAB counterpart. It is standard-library only. `tests/fixtures/metric_cases.json` is generated from it (`python matlab/tools/compare.py --write-fixture`). pytest checks that the fixture is current, and `tests/CompareDistributionsTest.m` and `tests/BitOrderTest.m` check the MATLAB functions against the same values. If either side changes, one of the suites fails.

`tools/tests/matlab_convention_sim.py` is a small statevector simulator that reports results the way MATLAB does (qubit 1 first, 1-based). pytest runs every committed export through it and checks that the mapped probabilities match Qiskit within `1e-10`, and that the asymmetric circuits fail without the mapping. This tests the mapping and metrics end to end without MATLAB, but it is not MATLAB.

```bash
python -m pytest matlab/tools                    # from the repository root, needs pytest only
python matlab/tools/compare.py --check-export matlab/data/qiskit_results
```

## Tests

| Suite | Needs | Covers |
| --- | --- | --- |
| `backend/tests/test_export_for_matlab.py` | backend requirements | files written, probabilities sum to 1, Bell/GHZ/superposition/bit-flip values, schema keys, determinism, committed copy up to date |
| `matlab/tools/tests/test_compare.py` | pytest | bit-order mapping including the reversed case, clbit mapping, metrics, chi-square, fixture, committed exports |
| `tests/BitOrderTest.m` | base MATLAB | mapping, shared fixture, reversed probe |
| `tests/CompareDistributionsTest.m` | base MATLAB | metrics and chi-square against the Python values |
| `tests/LoadExportTest.m` | base MATLAB | loading every committed export, one-element JSON lists, schema check, name sanitising |
| `tests/CircuitLoaderTest.m` | Quantum Computing support package | each gate's type, qubits, and angle; bad gates rejected; loader vs Qiskit for every export; hand-built vs loader; end-to-end `validateCircuit` |

Without the support package, `CircuitLoaderTest` is reported as Incomplete, not Failed.

## Limitations

- The MATLAB code has not been executed in this repository's environment. See the status note at the top.
- Only ideal, noiseless statevector simulation is compared. MATLAB hardware runs (`run` on AWS or IBM) and Aer noise models are out of scope.
- Exact probabilities are compared, not amplitudes. Fidelity covers relative phase, and global phase is ignored on purpose.
- The sampled tests are statistical. They detect a wrong distribution, not a bug that only shifts probabilities by less than shot noise; the exact check covers that.
- Every exported circuit has three or fewer qubits. MathWorks describes `simulate` as practical up to about 15 qubits, and the app caps circuits at 16.
- The export covers the reference circuits and two validation circuits, not language-model output. `qcg.circuitFromSpec` accepts any valid spec, so a saved generated spec can be checked by adding it to `CIRCUITS` in `backend/app/tools/export_for_matlab.py`.
- The committed export was generated with the pinned `qiskit` and `qiskit-aer` versions on Python 3.12, outside Docker. The container uses Python 3.11. Counts and probabilities depend on the Qiskit and Aer versions, not on the Python version, and the freshness test compares them.
