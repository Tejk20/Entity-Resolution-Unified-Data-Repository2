"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, Dataset, Job, Stats } from "@/lib/api";
import { MetricCard } from "@/components/MetricCard";
import { Pipeline } from "@/components/Pipeline";
import { StatusBadge } from "@/components/StatusBadge";

export default function OverviewPage() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function load() {
    try {
      const [s, d, j] = await Promise.all([api.stats(), api.datasets(), api.jobs()]);
      setStats(s);
      setDatasets(d);
      setJobs(j);
      setError("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load");
    }
  }

  useEffect(() => {
    load();
    const t = setInterval(load, 4000);
    return () => clearInterval(t);
  }, []);

  async function bootstrap() {
    setBusy(true);
    setError("");
    try {
      await api.bootstrap();
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Bootstrap failed");
    } finally {
      setBusy(false);
    }
  }

  const latest = jobs[0];

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl font-semibold">Entity resolution control plane</h1>
          <p className="mt-1 max-w-2xl text-sm text-white/55">
            Ingest SQL dumps and CSV extracts, map fields, match identities across sources, and
            enrich a single master entity with full source traceability.
          </p>
        </div>
        <div className="flex gap-2">
          <button className="btn-ghost" onClick={bootstrap} disabled={busy}>
            {busy ? "Seeding..." : "Load sample datasets"}
          </button>
          <Link href="/datasets" className="btn-primary">
            Import data
          </Link>
        </div>
      </div>

      {error ? (
        <div className="rounded-xl border border-rose-400/30 bg-rose-500/10 px-4 py-3 text-sm text-rose-200">
          {error}
        </div>
      ) : null}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <MetricCard label="Source records" value={stats?.total_records ?? 0} />
        <MetricCard label="Master entities" value={stats?.total_entities ?? 0} hint={`${stats?.matched_entities ?? 0} matched`} />
        <MetricCard label="Duplicates caught" value={stats?.duplicates_caught ?? 0} />
        <MetricCard
          label="Avg process time"
          value={`${stats?.avg_processing_seconds ?? 0}s`}
          hint={`${stats?.total_datasets ?? 0} datasets`}
        />
      </div>

      <Pipeline job={latest} />

      <div className="grid gap-6 lg:grid-cols-2">
        <div className="card p-5">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-sm font-semibold uppercase tracking-[0.14em] text-white/60">Datasets</h2>
            <Link href="/datasets" className="text-xs text-accent-400 hover:underline">
              Manage
            </Link>
          </div>
          <div className="space-y-2">
            {datasets.length === 0 ? (
              <p className="text-sm text-white/45">No datasets yet. Load samples or import a file.</p>
            ) : (
              datasets.slice(0, 6).map((d) => (
                <Link
                  key={d.id}
                  href={`/datasets/${d.id}`}
                  className="flex items-center justify-between rounded-xl border border-white/5 bg-white/[0.03] px-3 py-2 hover:bg-white/[0.06]"
                >
                  <div>
                    <div className="text-sm font-medium">{d.name}</div>
                    <div className="font-mono text-[11px] text-white/40">{d.source_tag}</div>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="font-mono text-xs text-white/50">{d.record_count} rows</span>
                    <StatusBadge status={d.status} />
                  </div>
                </Link>
              ))
            )}
          </div>
        </div>
        <div className="card p-5">
          <h2 className="mb-4 text-sm font-semibold uppercase tracking-[0.14em] text-white/60">
            Recent jobs
          </h2>
          <div className="space-y-2">
            {jobs.length === 0 ? (
              <p className="text-sm text-white/45">No processing jobs yet.</p>
            ) : (
              jobs.slice(0, 6).map((j) => (
                <div key={j.id} className="rounded-xl border border-white/5 bg-white/[0.03] px-3 py-2">
                  <div className="flex items-center justify-between">
                    <StatusBadge status={j.stage} />
                    <span className="font-mono text-[11px] text-white/40">
                      {j.records_processed}/{j.records_total}
                    </span>
                  </div>
                  <p className="mt-1 truncate text-xs text-white/55">{j.message}</p>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
