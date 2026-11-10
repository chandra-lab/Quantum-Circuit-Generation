type StatusBadgeProps = {
  valid: boolean;
};

export function StatusBadge({ valid }: StatusBadgeProps) {
  return (
    <span
      className={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ${
        valid ? "bg-pine/10 text-pine" : "bg-red-100 text-red-900"
      }`}
    >
      {valid ? "Validation passed" : "Validation failed"}
    </span>
  );
}
