import type { ApiError } from "../services/api";

type ErrorBannerProps = {
  error: ApiError;
};

export function ErrorBanner({ error }: ErrorBannerProps) {
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
    </div>
  );
}
