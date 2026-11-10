import { CircuitDiagram } from "./CircuitDiagram";
import { Histogram } from "./Histogram";
import { ProbabilityBars } from "./ProbabilityBars";
import { SpecViewer } from "./SpecViewer";
import { StatusBadge } from "./StatusBadge";
import type { CircuitResult } from "../types/circuit";

type ResultsPanelProps = {
  result: CircuitResult | null;
  loading: "generate" | "reference" | null;
};

function formatGate(gate: string, qubits: number[], parameter?: number | null): string {
  const targets = qubits.map((qubit) => `q${qubit}`).join(", ");
  const angle = parameter === undefined || parameter === null ? "" : `(${parameter})`;
  return `${gate.toUpperCase()}${angle} ${targets}`;
}

export function ResultsPanel({ result, loading }: ResultsPanelProps) {
  return (
    <section className="panel min-h-[28rem]" aria-live="polite" aria-busy={loading !== null}>
      <h2 className="font-serif text-xl text-navy">Results</h2>
      {loading ? (
        <p className="mt-6 text-sm text-ink/70">
          {loading === "reference" ? "Simulating the predefined reference circuit…" : "Generating and simulating…"}
        </p>
      ) : null}
      {!loading && !result ? (
        <p className="mt-6 text-sm leading-relaxed text-ink/70">
          Generate a circuit from a prompt, or simulate a predefined reference circuit. Counts,
          probabilities, and the Qiskit diagram appear here.
        </p>
      ) : null}
      {result ? (
        <div className="mt-4 space-y-5">
          <h3 className="font-serif text-2xl text-ink">{result.spec.circuit_name}</h3>
          <div className="flex flex-wrap items-center gap-2">
            <StatusBadge valid={result.validation.valid} />
            {result.source === "reference" ? (
              <span className="inline-flex rounded-full bg-copper/10 px-2.5 py-1 text-xs font-semibold text-copper">
                Predefined reference circuit — not LLM output
              </span>
            ) : (
              <span className="inline-flex rounded-full bg-navy/10 px-2.5 py-1 text-xs font-semibold text-navy">
                LLM output
              </span>
            )}
          </div>
          <div>
            <h3 className="text-xs font-semibold uppercase tracking-wide text-ink/50">Original prompt</h3>
            <p className="mt-1 text-sm leading-relaxed">{result.prompt}</p>
          </div>
          <dl className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <Stat label="Qubits" value={String(result.spec.num_qubits)} />
            <Stat label="Clbits" value={String(result.spec.num_clbits)} />
            <Stat label="Shots" value={String(result.shots)} />
            <Stat label="Simulator" value={result.metadata.simulator} />
          </dl>
          <div>
            <h3 className="text-xs font-semibold uppercase tracking-wide text-ink/50">Gates applied</h3>
            <ul className="mt-2 flex flex-wrap gap-2">
              {result.spec.gates.map((gate, index) => (
                <li key={`${gate.gate}-${index}`} className="rounded-md bg-paper px-2 py-1 font-mono text-xs">
                  {formatGate(gate.gate, gate.qubits, gate.parameter)}
                </li>
              ))}
            </ul>
          </div>
          <p className="text-sm leading-relaxed text-ink/80">{result.spec.description}</p>
          <CircuitDiagram svg={result.visualization.svg} />
          <div className="grid gap-6 lg:grid-cols-2">
            <div>
              <h3 className="text-sm font-semibold text-navy">Counts</h3>
              <Histogram counts={result.counts} />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-navy">Probabilities</h3>
              <div className="mt-3">
                <ProbabilityBars probabilities={result.probabilities} />
              </div>
            </div>
          </div>
          <p className="text-xs text-ink/50">
            Bitstrings use Qiskit order: the rightmost bit is classical bit 0. Probabilities are count
            divided by shots.
          </p>
          <div>
            <h3 className="text-xs font-semibold uppercase tracking-wide text-ink/50">Spec JSON</h3>
            <div className="mt-2">
              <SpecViewer spec={result.spec} />
            </div>
          </div>
        </div>
      ) : null}
    </section>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg bg-paper px-3 py-2">
      <dt className="text-[11px] uppercase tracking-wide text-ink/50">{label}</dt>
      <dd className="mt-1 font-mono text-sm">{value}</dd>
    </div>
  );
}
