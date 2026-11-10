type CircuitDiagramProps = {
  svg: string;
};

export function CircuitDiagram({ svg }: CircuitDiagramProps) {
  const src = `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`;
  return (
    <figure className="overflow-auto rounded-lg border border-line bg-white p-3">
      <img
        src={src}
        alt="Qiskit circuit diagram with qubit lines, gate symbols, and measurements"
        className="mx-auto h-auto max-w-full"
      />
      <figcaption className="mt-2 text-center text-xs text-ink/60">
        Diagram rendered from the Qiskit circuit that was simulated.
      </figcaption>
    </figure>
  );
}
