import type { ReactNode } from "react";
import type { LearnerExplanation as Explanation } from "../types/circuit";

type LearnerExplanationProps = {
  explanation: Explanation;
};

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div>
      <h4 className="text-sm font-semibold text-navy">{title}</h4>
      <div className="mt-1 space-y-1 text-sm leading-relaxed text-ink/85">{children}</div>
    </div>
  );
}

export function LearnerExplanation({ explanation }: LearnerExplanationProps) {
  return (
    <section
      aria-labelledby="learner-explanation-heading"
      className="space-y-4 rounded-lg border border-pine/30 bg-pine/5 px-4 py-4"
    >
      <h3 id="learner-explanation-heading" className="font-serif text-lg text-pine">
        What this circuit does, in plain language
      </h3>
      {explanation.key_idea ? (
        <p className="rounded-md bg-card px-3 py-2 text-sm font-semibold leading-relaxed text-ink">
          {explanation.key_idea}
        </p>
      ) : null}
      <Section title="The goal">
        <p>{explanation.overview}</p>
      </Section>
      {explanation.steps.length > 0 ? (
        <Section title="Step by step">
          <ol className="list-none space-y-1">
            {explanation.steps.map((step) => (
              <li key={step}>{step}</li>
            ))}
          </ol>
        </Section>
      ) : null}
      {explanation.measurements.length > 0 ? (
        <Section title="Measurements">
          {explanation.measurements.map((sentence) => (
            <p key={sentence}>{sentence}</p>
          ))}
          {explanation.bit_order ? <p className="font-medium">{explanation.bit_order}</p> : null}
        </Section>
      ) : null}
      {explanation.outcome.length > 0 ? (
        <Section title="What the simulation showed">
          {explanation.outcome.map((sentence) => (
            <p key={sentence}>{sentence}</p>
          ))}
        </Section>
      ) : null}
      <Section title="Validation">
        <p>{explanation.validation}</p>
        {explanation.errors.length > 0 ? (
          <ul className="list-disc space-y-1 pl-5">
            {explanation.errors.map((error) => (
              <li key={error}>{error}</li>
            ))}
          </ul>
        ) : null}
      </Section>
    </section>
  );
}
