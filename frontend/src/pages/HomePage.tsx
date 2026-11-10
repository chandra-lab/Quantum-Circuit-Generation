import { ConfigNotice } from "../components/ConfigNotice";
import { ErrorBanner } from "../components/ErrorBanner";
import { ExamplePromptList } from "../components/ExamplePromptList";
import { ExtractionNotice } from "../components/ExtractionNotice";
import { Header } from "../components/Header";
import { PromptForm } from "../components/PromptForm";
import { ReferenceCircuitList } from "../components/ReferenceCircuitList";
import { ResultsPanel } from "../components/ResultsPanel";
import { examplePrompts, referenceCircuits } from "../data/examples";
import { useCircuitWorkbench } from "../hooks/useCircuitWorkbench";
import { useViewMode } from "../hooks/useViewMode";

export function HomePage() {
  const workbench = useCircuitWorkbench();
  const [mode, setMode] = useViewMode();
  const busy = workbench.loading !== null;

  return (
    <div className="mx-auto max-w-6xl px-4 py-8 sm:px-6 lg:px-8">
      <Header mode={mode} onModeChange={setMode} />
      <div className="mt-6 space-y-3">
        {workbench.health && !workbench.health.llm.configured ? (
          <ConfigNotice model={workbench.health.llm.model} />
        ) : null}
        {workbench.healthError ? (
          <p className="text-sm text-copper" role="status">
            {workbench.healthError}
          </p>
        ) : null}
        {workbench.error ? <ErrorBanner error={workbench.error} mode={mode} /> : null}
        {workbench.error?.extraction ? (
          <ExtractionNotice extraction={workbench.error.extraction} onEdit={workbench.editExtraction} />
        ) : null}
      </div>
      <div className="mt-6 grid items-start gap-6 lg:grid-cols-2">
        <div className="space-y-6">
          <PromptForm
            prompt={workbench.prompt}
            shots={workbench.shots}
            loading={workbench.loading === "generate"}
            disabled={busy}
            attachment={workbench.attachment}
            maxUploadMb={workbench.health?.uploads?.max_upload_mb}
            onPromptChange={workbench.setPrompt}
            onShotsChange={workbench.setShots}
            onAttachmentChange={workbench.setAttachment}
            onSubmit={() => {
              void workbench.generate();
            }}
          />
          <ExamplePromptList
            prompts={examplePrompts}
            disabled={busy}
            onSelect={workbench.setPrompt}
          />
          <ReferenceCircuitList
            circuits={referenceCircuits}
            disabled={busy}
            onSimulate={(example) => {
              void workbench.simulateReference(example);
            }}
          />
        </div>
        <ResultsPanel
          result={workbench.result}
          loading={workbench.loading}
          mode={mode}
          onEditExtraction={workbench.editExtraction}
        />
      </div>
      <footer className="mt-10 border-t border-line pt-4 text-xs leading-relaxed text-ink/60">
        Simulator: Qiskit Aer. Qubit count is capped by MAX_QUBITS. PyTorch is installed in the
        backend image for later research and is not used to simulate circuits. This MVP does not
        fine-tune a model, optimize circuits, or run on quantum hardware.
      </footer>
    </div>
  );
}
