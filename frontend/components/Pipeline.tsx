import { Job } from "@/lib/api";

const STAGES = [
  "uploaded",
  "inspecting",
  "field_mapping",
  "cleaning",
  "indexing",
  "matching",
  "enriching",
  "completed",
];

export function Pipeline({ job }: { job?: Job | null }) {
  const current = job?.stage || "uploaded";
  const idx = STAGES.indexOf(current);
  return (
    <div className="card p-5">
      <div className="mb-4 flex items-center justify-between">
        <div>
          <div className="text-sm font-semibold">Ingestion pipeline</div>
          <div className="text-xs text-white/50">{job?.message || "Idle"}</div>
        </div>
        <div className="font-mono text-sm text-accent-400">{Math.round(job?.progress || 0)}%</div>
      </div>
      <div className="mb-4 h-1.5 overflow-hidden rounded-full bg-white/10">
        <div
          className="h-full rounded-full bg-accent-500 transition-all"
          style={{ width: `${job?.progress || 0}%` }}
        />
      </div>
      <div className="grid grid-cols-2 gap-2 md:grid-cols-4 lg:grid-cols-8">
        {STAGES.map((stage, i) => {
          const done = idx > i || current === "completed";
          const active = idx === i && current !== "completed";
          return (
            <div
              key={stage}
              className={`rounded-xl border px-2 py-2 text-center text-[11px] ${
                done
                  ? "border-accent-500/40 bg-accent-500/10 text-accent-400"
                  : active
                    ? "border-amber-400/40 bg-amber-400/10 text-amber-200"
                    : "border-white/10 text-white/40"
              }`}
            >
              {stage.replaceAll("_", " ")}
            </div>
          );
        })}
      </div>
    </div>
  );
}
