import { useRef, type KeyboardEvent } from "react";
import type { ViewMode } from "../types/circuit";

type ModeToggleProps = {
  mode: ViewMode;
  onChange: (mode: ViewMode) => void;
};

const OPTIONS: { value: ViewMode; label: string; hint: string }[] = [
  { value: "learner", label: "Learner", hint: "Results explained in plain language" },
  { value: "pro", label: "Pro", hint: "Full technical view" },
];

export function ModeToggle({ mode, onChange }: ModeToggleProps) {
  const refs = useRef<(HTMLButtonElement | null)[]>([]);

  function handleKeyDown(event: KeyboardEvent<HTMLButtonElement>, index: number) {
    const keys: Record<string, number> = {
      ArrowRight: 1,
      ArrowDown: 1,
      ArrowLeft: -1,
      ArrowUp: -1,
    };
    let next: number | null = null;
    if (event.key in keys) {
      next = (index + keys[event.key] + OPTIONS.length) % OPTIONS.length;
    } else if (event.key === "Home") {
      next = 0;
    } else if (event.key === "End") {
      next = OPTIONS.length - 1;
    }
    if (next === null) {
      return;
    }
    event.preventDefault();
    onChange(OPTIONS[next].value);
    refs.current[next]?.focus();
  }

  return (
    <div className="flex flex-col items-start gap-1 sm:items-end">
      <span id="view-mode-label" className="text-xs font-semibold uppercase tracking-wide text-ink/60">
        View mode
      </span>
      <div
        role="radiogroup"
        aria-labelledby="view-mode-label"
        className="inline-flex rounded-lg border border-line bg-card p-1 shadow-card"
      >
        {OPTIONS.map((option, index) => {
          const selected = option.value === mode;
          return (
            <button
              key={option.value}
              ref={(element) => {
                refs.current[index] = element;
              }}
              type="button"
              role="radio"
              aria-checked={selected}
              tabIndex={selected ? 0 : -1}
              title={option.hint}
              onClick={() => onChange(option.value)}
              onKeyDown={(event) => handleKeyDown(event, index)}
              className={`rounded-md px-4 py-1.5 text-sm font-semibold transition focus:outline-none focus-visible:ring-2 focus-visible:ring-copper focus-visible:ring-offset-1 ${
                selected ? "bg-navy text-white" : "text-ink/70 hover:text-navy"
              }`}
            >
              {option.label}
            </button>
          );
        })}
      </div>
    </div>
  );
}
