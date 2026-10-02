const COLORS: Record<string, string> = {
  created: "border-white/20 text-white/70",
  uploaded: "border-sky-400/40 text-sky-300",
  inspecting: "border-amber-400/40 text-amber-300",
  field_mapping: "border-violet-400/40 text-violet-300",
  queued: "border-white/20 text-white/70",
  cleaning: "border-amber-400/40 text-amber-300",
  indexing: "border-cyan-400/40 text-cyan-300",
  matching: "border-teal-400/40 text-teal-300",
  enriching: "border-emerald-400/40 text-emerald-300",
  completed: "border-accent-500/50 text-accent-400",
  matched: "border-accent-500/50 text-accent-400",
  unmatched: "border-orange-400/40 text-orange-300",
  failed: "border-rose-400/40 text-rose-300",
};

export function StatusBadge({ status }: { status: string }) {
  return (
    <span className={`chip ${COLORS[status] || "border-white/20 text-white/70"}`}>
      {status.replaceAll("_", " ")}
    </span>
  );
}
