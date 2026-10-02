"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { api, EntityCard } from "@/lib/api";
import { StatusBadge } from "@/components/StatusBadge";

export default function EntityPage() {
  const params = useParams();
  const id = Number(params.id);
  const [entity, setEntity] = useState<EntityCard | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!id) return;
    api
      .entity(id)
      .then(setEntity)
      .catch((e) => setError(e instanceof Error ? e.message : "Failed"));
  }, [id]);

  if (error) return <p className="text-rose-300">{error}</p>;
  if (!entity) return <p className="text-white/50">Loading entity...</p>;

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-3xl font-semibold">{entity.display_name}</h1>
          <p className="mt-1 text-sm text-white/50">
            {entity.match_count} linked records across {entity.source_count} sources
          </p>
        </div>
        <StatusBadge status={entity.status} />
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        {entity.linked_sources.map((src, i) => (
          <div key={i} className="card p-5">
            <div className="text-xs uppercase tracking-[0.16em] text-white/45">{src.source_tag}</div>
            <div className="mt-1 font-medium">{src.dataset_name}</div>
            <div className="font-mono text-xs text-white/40">
              {src.table_name} / row {src.row_id}
            </div>
            <pre className="mt-3 overflow-x-auto rounded-xl bg-ink-950 p-3 font-mono text-[11px] text-accent-400">
              {JSON.stringify(src.raw, null, 2)}
            </pre>
          </div>
        ))}
      </div>
    </div>
  );
}
