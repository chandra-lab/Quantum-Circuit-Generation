import type { ExamplePrompt } from "../data/examples";

type ExamplePromptListProps = {
  prompts: ExamplePrompt[];
  disabled: boolean;
  onSelect: (prompt: string) => void;
};

export function ExamplePromptList({ prompts, disabled, onSelect }: ExamplePromptListProps) {
  return (
    <section className="panel" aria-labelledby="examples-heading">
      <h2 id="examples-heading" className="font-serif text-xl text-navy">
        Example prompts
      </h2>
      <p className="mt-1 text-sm text-ink/70">These fill the prompt box. They do not run the model by themselves.</p>
      <ul className="mt-4 flex flex-wrap gap-2">
        {prompts.map((example) => (
          <li key={example.id}>
            <button
              type="button"
              className="btn-secondary"
              disabled={disabled}
              onClick={() => onSelect(example.prompt)}
            >
              {example.label}
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}
