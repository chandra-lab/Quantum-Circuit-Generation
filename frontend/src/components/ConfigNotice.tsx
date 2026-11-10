type ConfigNoticeProps = {
  model: string;
};

export function ConfigNotice({ model }: ConfigNoticeProps) {
  return (
    <aside className="rounded-xl border border-copper/30 bg-copper/10 px-4 py-3 text-sm leading-relaxed text-ink">
      <p className="font-semibold text-copper">Natural-language generation needs GROQ_API_KEY.</p>
      <p className="mt-1">
        The configured model name is <span className="font-mono">{model}</span>. Generate will return
        a configuration error until the key is set. The reference circuits below still simulate on
        Qiskit Aer.
      </p>
    </aside>
  );
}
