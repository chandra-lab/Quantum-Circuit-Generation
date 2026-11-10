import type { CircuitSpec } from "../types/circuit";

type SpecViewerProps = {
  spec: CircuitSpec;
};

export function SpecViewer({ spec }: SpecViewerProps) {
  return (
    <pre className="max-h-80 overflow-auto rounded-lg bg-ink px-4 py-3 font-mono text-xs leading-relaxed text-paper">
      {JSON.stringify(spec, null, 2)}
    </pre>
  );
}
