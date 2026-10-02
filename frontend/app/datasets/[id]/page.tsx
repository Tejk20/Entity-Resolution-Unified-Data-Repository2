"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { api, Dataset, Job, TableMapping } from "@/lib/api";
import { Pipeline } from "@/components/Pipeline";
import { StatusBadge } from "@/components/StatusBadge";

const CANONICAL = [
  "",
  "email",
  "phone",
  "name",
  "username",
  "member_id",
  "address",
  "company",
  "city",
  "country",
  "age",
  "gender",
  "dob",
];

export default function DatasetDetailPage() {
  const params = useParams();
  const id = Number(params.id);
  const [dataset, setDataset] = useState<Dataset | null>(null);
  const [mappings, setMappings] = useState<TableMapping[]>([]);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [partName, setPartName] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState("");

  async function load() {
    if (!id) return;
    try {
      const [d, j] = await Promise.all([api.dataset(id), api.jobs(id)]);
      setDataset(d);
      setJobs(j);
      if (["field_mapping", "inspecting", "completed", "matching", "cleaning", "indexing", "enriching"].includes(d.status) || d.table_count > 0) {
        try {
          setMappings(await api.mappings(id));
        } catch {
          /* mappings may not exist yet */
        }
      }
      setError("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load");
    }
  }

  useEffect(() => {
    load();
    const t = setInterval(load, 3000);
    return () => clearInterval(t);
  }, [id]);

  async function onUpload(files: FileList | null) {
    if (!files || files.length === 0) return;
    setBusy("upload");
    try {
      await api.upload(id, files, partName);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Upload failed");
    } finally {
      setBusy("");
    }
  }

  async function inspect() {
    setBusy("inspect");
    try {
      await api.inspect(id);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Inspect failed");
    } finally {
      setBusy("");
    }
  }

  function updateMap(tableId: number, col: string, value: string) {
    setMappings((prev) =>
      prev.map((t) => {
        if (t.table_id !== tableId) return t;
        const mapping = { ...t.mapping };
        if (!value) delete mapping[col];
        else mapping[col] = value;
        return { ...t, mapping };
      })
    );
  }

  async function saveAndProcess() {
    setBusy("process");
    try {
      for (const t of mappings) {
        await api.saveMapping(id, t.table_id, t.mapping);
      }
      await api.confirmMappings(id);
      await api.process(id, true);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Process failed");
    } finally {
      setBusy("");
    }
  }

  const job = jobs[0];

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-3xl font-semibold">{dataset?.name || "Dataset"}</h1>
          <p className="mt-1 font-mono text-sm text-white/50">{dataset?.source_tag}</p>
        </div>
        {dataset ? <StatusBadge status={dataset.status} /> : null}
      </div>

      {error ? (
        <div className="rounded-xl border border-rose-400/30 bg-rose-500/10 px-4 py-3 text-sm text-rose-200">
          {error}
        </div>
      ) : null}

      <Pipeline job={job} />

      <div className="card space-y-3 p-5">
        <h2 className="text-sm font-semibold uppercase tracking-[0.14em] text-white/60">
          Multi-part upload
        </h2>
        <p className="text-sm text-white/50">
          Attach CSV or SQL files. Use the same source dataset for File_Part1 / File_Part2.
        </p>
        <div className="flex flex-wrap gap-3">
          <input
            placeholder="Part name e.g. File_Part1"
            value={partName}
            onChange={(e) => setPartName(e.target.value)}
            className="max-w-xs"
          />
          <label className="btn-ghost cursor-pointer">
            {busy === "upload" ? "Uploading..." : "Choose files"}
            <input
              type="file"
              multiple
              accept=".csv,.sql"
              className="hidden"
              onChange={(e) => onUpload(e.target.files)}
            />
          </label>
          <button className="btn-ghost" onClick={inspect} disabled={busy !== ""}>
            Inspect structure
          </button>
        </div>
      </div>

      {mappings.map((table) => (
        <div key={table.table_id} className="card overflow-hidden">
          <div className="flex items-center justify-between border-b border-white/10 px-5 py-3">
            <div>
              <div className="font-medium">{table.table_name}</div>
              <div className="text-xs text-white/45">{table.row_count} rows</div>
            </div>
            {table.mapping_confirmed ? <StatusBadge status="completed" /> : <StatusBadge status="field_mapping" />}
          </div>
          <table className="w-full text-left text-sm">
            <thead className="text-xs uppercase tracking-wider text-white/40">
              <tr>
                <th className="px-5 py-2">Source column</th>
                <th className="px-5 py-2">Suggested canonical</th>
                <th className="px-5 py-2">Confidence</th>
                <th className="px-5 py-2">Override</th>
              </tr>
            </thead>
            <tbody>
              {table.columns.map((col) => {
                const suggestion = table.suggestions.find((s) => s.source_column === col);
                return (
                  <tr key={col} className="border-t border-white/5">
                    <td className="px-5 py-2 font-mono text-xs">{col}</td>
                    <td className="px-5 py-2 text-accent-400">{suggestion?.canonical_field || "—"}</td>
                    <td className="px-5 py-2 font-mono text-xs">{suggestion ? Math.round(suggestion.confidence * 100) : 0}%</td>
                    <td className="px-5 py-2">
                      <select
                        value={table.mapping[col] || ""}
                        onChange={(e) => updateMap(table.table_id, col, e.target.value)}
                      >
                        {CANONICAL.map((c) => (
                          <option key={c || "none"} value={c}>
                            {c || "(ignore)"}
                          </option>
                        ))}
                      </select>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      ))}

      <div className="flex justify-end">
        <button className="btn-primary" onClick={saveAndProcess} disabled={busy !== ""}>
          {busy === "process" ? "Starting..." : "Confirm mappings and process"}
        </button>
      </div>
    </div>
  );
}
