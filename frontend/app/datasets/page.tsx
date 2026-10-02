"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, Dataset } from "@/lib/api";
import { StatusBadge } from "@/components/StatusBadge";

export default function DatasetsPage() {
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [name, setName] = useState("");
  const [tag, setTag] = useState("");
  const [description, setDescription] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function load() {
    try {
      setDatasets(await api.datasets());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load datasets");
    }
  }

  useEffect(() => {
    load();
    const t = setInterval(load, 5000);
    return () => clearInterval(t);
  }, []);

  async function create(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const ds = await api.createDataset({
        name,
        source_tag: tag || name.toLowerCase().replace(/\s+/g, "_"),
        description,
      });
      setName("");
      setTag("");
      setDescription("");
      window.location.href = `/datasets/${ds.id}`;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Create failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-semibold">Dataset management</h1>
        <p className="mt-1 text-sm text-white/55">
          Group multi-part SQL dumps and CSV files under one source, inspect schemas, then confirm
          AI field mappings before batch ingestion.
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <form onSubmit={create} className="card space-y-3 p-5 lg:col-span-1">
          <h2 className="text-sm font-semibold uppercase tracking-[0.14em] text-white/60">
            New source dataset
          </h2>
          <label className="block text-xs text-white/50">
            Name
            <input value={name} onChange={(e) => setName(e.target.value)} required className="mt-1" />
          </label>
          <label className="block text-xs text-white/50">
            Source tag
            <input
              value={tag}
              onChange={(e) => setTag(e.target.value)}
              placeholder="database_a"
              className="mt-1"
            />
          </label>
          <label className="block text-xs text-white/50">
            Description
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={3}
              className="mt-1"
            />
          </label>
          {error ? <p className="text-xs text-rose-300">{error}</p> : null}
          <button className="btn-primary w-full" disabled={busy}>
            {busy ? "Creating..." : "Create dataset"}
          </button>
        </form>

        <div className="card overflow-hidden lg:col-span-2">
          <table className="w-full text-left text-sm">
            <thead className="bg-white/5 text-xs uppercase tracking-wider text-white/45">
              <tr>
                <th className="px-4 py-3">Name</th>
                <th className="px-4 py-3">Tag</th>
                <th className="px-4 py-3">Rows</th>
                <th className="px-4 py-3">Status</th>
              </tr>
            </thead>
            <tbody>
              {datasets.map((d) => (
                <tr key={d.id} className="border-t border-white/5 hover:bg-white/[0.03]">
                  <td className="px-4 py-3">
                    <Link href={`/datasets/${d.id}`} className="font-medium hover:text-accent-400">
                      {d.name}
                    </Link>
                    <div className="text-xs text-white/40">{d.file_count} files / {d.table_count} tables</div>
                  </td>
                  <td className="px-4 py-3 font-mono text-xs">{d.source_tag}</td>
                  <td className="px-4 py-3 font-mono">{d.record_count}</td>
                  <td className="px-4 py-3">
                    <StatusBadge status={d.status} />
                  </td>
                </tr>
              ))}
              {datasets.length === 0 ? (
                <tr>
                  <td colSpan={4} className="px-4 py-8 text-center text-white/40">
                    No datasets yet
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
