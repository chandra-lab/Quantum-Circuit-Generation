import { useCallback, useState } from "react";
import type { ViewMode } from "../types/circuit";

export const VIEW_MODE_STORAGE_KEY = "qcg.viewMode";
export const DEFAULT_VIEW_MODE: ViewMode = "pro";

function isViewMode(value: unknown): value is ViewMode {
  return value === "learner" || value === "pro";
}

export function readStoredViewMode(): ViewMode {
  try {
    const stored = window.localStorage.getItem(VIEW_MODE_STORAGE_KEY);
    return isViewMode(stored) ? stored : DEFAULT_VIEW_MODE;
  } catch {
    return DEFAULT_VIEW_MODE;
  }
}

export function useViewMode(): [ViewMode, (mode: ViewMode) => void] {
  const [mode, setModeState] = useState<ViewMode>(readStoredViewMode);

  const setMode = useCallback((next: ViewMode) => {
    setModeState(next);
    try {
      window.localStorage.setItem(VIEW_MODE_STORAGE_KEY, next);
    } catch {
      // Storage can be unavailable in private windows; the toggle still works for this session.
    }
  }, []);

  return [mode, setMode];
}
