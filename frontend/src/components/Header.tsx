import { ModeToggle } from "./ModeToggle";
import type { ViewMode } from "../types/circuit";

type HeaderProps = {
  mode: ViewMode;
  onModeChange: (mode: ViewMode) => void;
};

export function Header({ mode, onModeChange }: HeaderProps) {
  return (
    <header className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
      <div>
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-copper">Research framework</p>
        <h1 className="mt-1 font-serif text-4xl font-medium tracking-tight text-navy">
          LLM-Based Quantum Circuit Generation
        </h1>
        <p className="mt-3 max-w-2xl text-base leading-relaxed text-ink/80">
          A framework for natural language to quantum programs. Describe a circuit, receive a
          validated JSON specification, and simulate it on Qiskit Aer. The model returns a spec,
          never Python.
        </p>
      </div>
      <div className="flex shrink-0 flex-col items-start gap-4 sm:items-end">
        <ModeToggle mode={mode} onChange={onModeChange} />
        <div className="hidden h-16 w-28 sm:block" aria-hidden="true">
          <svg viewBox="0 0 120 64" className="h-full w-full text-navy">
            <line x1="8" y1="16" x2="112" y2="16" stroke="currentColor" strokeWidth="1.5" />
            <line x1="8" y1="48" x2="112" y2="48" stroke="currentColor" strokeWidth="1.5" />
            <rect x="28" y="6" width="20" height="20" fill="#fffdf8" stroke="currentColor" strokeWidth="1.5" />
            <text x="38" y="20" textAnchor="middle" fontSize="11" fill="currentColor">
              H
            </text>
            <line x1="58" y1="16" x2="58" y2="48" stroke="currentColor" strokeWidth="1.5" />
            <circle cx="58" cy="16" r="4" fill="currentColor" />
            <circle cx="58" cy="48" r="5" fill="#fffdf8" stroke="currentColor" strokeWidth="1.5" />
            <path d="M92 16 l6 6 l-6 6" fill="none" stroke="currentColor" strokeWidth="1.5" />
            <path d="M92 48 l6 6 l-6 6" fill="none" stroke="currentColor" strokeWidth="1.5" />
          </svg>
        </div>
      </div>
    </header>
  );
}
