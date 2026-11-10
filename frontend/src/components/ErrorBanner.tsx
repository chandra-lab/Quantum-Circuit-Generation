import type { ApiError } from "../services/api";
import type { ViewMode } from "../types/circuit";

type ErrorBannerProps = {
  error: ApiError;
  mode?: ViewMode;
};

export function ErrorBanner({ error, mode = "pro" }: ErrorBannerProps) {
  const explanation = mode === "learner" ? error.learnerExplanation : undefined;
  const configuration = error.code === "configuration_error";
  return (
    <div
      role="alert"
      className={`rounded-xl border px-4 py-3 text-sm leading-relaxed ${
        configuration ? "border-copper/40 bg-copper/10 text-ink" : "border-red-300 bg-red-50 text-red-950"
      }`}
    >
      <p className="font-semibold">{configuration ? "Groq is not configured" : "Request failed"}</p>
      <p className="mt-1">{error.message}</p>
      {error.details.length > 0 ? (
        <ul className="mt-2 list-disc pl-5">
          {error.details.map((detail) => (
            <li key={detail}>{detail}</li>
          ))}
        </ul>
      ) : null}
      {explanation ? (
        <div className="mt-3 border-t border-red-200 pt-3">
          <p className="font-semibold">What this means</p>
          <p className="mt-1">{explanation.validation}</p>
          {explanation.errors.length > 0 ? (
            <ul className="mt-2 list-disc pl-5">
              {explanation.errors.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
