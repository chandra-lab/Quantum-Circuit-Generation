type PromptFormProps = {
  prompt: string;
  shots: number;
  loading: boolean;
  disabled: boolean;
  onPromptChange: (value: string) => void;
  onShotsChange: (value: number) => void;
  onSubmit: () => void;
};

export function PromptForm({
  prompt,
  shots,
  loading,
  disabled,
  onPromptChange,
  onShotsChange,
  onSubmit,
}: PromptFormProps) {
  return (
    <form
      className="panel"
      onSubmit={(event) => {
        event.preventDefault();
        onSubmit();
      }}
    >
      <label htmlFor="prompt" className="text-sm font-semibold text-navy">
        Natural language prompt
      </label>
      <textarea
        id="prompt"
        value={prompt}
        onChange={(event) => onPromptChange(event.target.value)}
        rows={5}
        placeholder="Describe the quantum circuit you want to build."
        className="mt-2 w-full resize-y rounded-md border border-line bg-white px-3 py-2 text-sm leading-relaxed outline-none ring-navy/30 focus:ring-2"
      />
      <div className="mt-4 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <label className="text-sm text-ink/80">
          Shots
          <input
            type="number"
            min={1}
            value={shots}
            onChange={(event) => {
              const next = Number(event.target.value);
              if (Number.isInteger(next) && next > 0) {
                onShotsChange(next);
              }
            }}
            className="mt-1 block w-32 rounded-md border border-line bg-white px-3 py-2 font-mono text-sm outline-none ring-navy/30 focus:ring-2"
          />
        </label>
        <button type="submit" className="btn-primary" disabled={disabled || loading || prompt.trim().length === 0}>
          {loading ? "Generating…" : "Generate"}
        </button>
      </div>
      <p className="mt-3 text-xs leading-relaxed text-ink/60">
        Generate asks Groq for a JSON circuit spec, validates it, then simulates the circuit that
        the restricted gate map builds. If the API key is missing, this button reports a
        configuration error and does not substitute a template.
      </p>
    </form>
  );
}
