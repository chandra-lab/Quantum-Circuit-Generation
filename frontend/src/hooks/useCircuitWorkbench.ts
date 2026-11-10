import { useCallback, useEffect, useState } from "react";
import type { ExamplePrompt } from "../data/examples";
import { ApiError, generateAndSimulate, getHealth, simulate } from "../services/api";
import type { CircuitResult, HealthResponse } from "../types/circuit";

export function useCircuitWorkbench() {
  const [prompt, setPrompt] = useState("");
  const [shots, setShots] = useState(1000);
  const [loading, setLoading] = useState<"generate" | "reference" | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const [result, setResult] = useState<CircuitResult | null>(null);
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [healthError, setHealthError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    getHealth()
      .then((next) => {
        if (!cancelled) {
          setHealth(next);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setHealthError("The API health check did not respond.");
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const generate = useCallback(async () => {
    setLoading("generate");
    setError(null);
    try {
      const response = await generateAndSimulate(prompt, shots);
      setResult({
        source: "llm",
        prompt: response.prompt,
        spec: response.spec,
        validation: response.validation,
        shots: response.shots,
        counts: response.counts,
        probabilities: response.probabilities,
        metadata: response.metadata,
        visualization: response.visualization,
        learnerExplanation: response.learner_explanation,
      });
    } catch (caught) {
      setError(
        caught instanceof ApiError
          ? caught
          : new ApiError(0, "network_error", "Could not reach the API."),
      );
    } finally {
      setLoading(null);
    }
  }, [prompt, shots]);

  const simulateReference = useCallback(
    async (example: ExamplePrompt) => {
      if (!example.spec) {
        return;
      }
      setPrompt(example.prompt);
      setLoading("reference");
      setError(null);
      try {
        const response = await simulate(example.spec, shots);
        setResult({
          source: "reference",
          prompt: example.prompt,
          referenceLabel: example.label,
          spec: response.spec,
          validation: response.validation,
          shots: response.shots,
          counts: response.counts,
          probabilities: response.probabilities,
          metadata: response.metadata,
          visualization: response.visualization,
          learnerExplanation: response.learner_explanation,
        });
      } catch (caught) {
        setError(
          caught instanceof ApiError
            ? caught
            : new ApiError(0, "network_error", "Could not reach the API."),
        );
      } finally {
        setLoading(null);
      }
    },
    [shots],
  );

  return {
    prompt,
    setPrompt,
    shots,
    setShots,
    loading,
    error,
    result,
    health,
    healthError,
    generate,
    simulateReference,
  };
}
