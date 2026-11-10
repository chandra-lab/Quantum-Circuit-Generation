import type { ExamplePrompt } from "../data/examples";

type ReferenceCircuitListProps = {
  circuits: ExamplePrompt[];
  disabled: boolean;
  onSimulate: (example: ExamplePrompt) => void;
};

export function ReferenceCircuitList({ circuits, disabled, onSimulate }: ReferenceCircuitListProps) {
  return (
    <section className="panel" aria-labelledby="reference-heading">
      <h2 id="reference-heading" className="font-serif text-xl text-navy">
        Predefined reference circuits
      </h2>
      <p className="mt-1 text-sm leading-relaxed text-ink/70">
        These are validated specs shipped with the app, not language-model output. Simulate posts
        them to the Aer endpoint and works without a Groq key.
      </p>
      <ul className="mt-4 grid gap-3 sm:grid-cols-2">
        {circuits.map((circuit) => (
          <li key={circuit.id} className="rounded-lg border border-line bg-paper/60 p-3">
            <p className="text-sm font-semibold text-navy">{circuit.label}</p>
            <p className="mt-1 text-xs leading-relaxed text-ink/70">{circuit.description}</p>
            <button
              type="button"
              className="btn-secondary mt-3"
              disabled={disabled}
              onClick={() => onSimulate(circuit)}
            >
              Simulate reference
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}
