"use client";

import { useState } from "react";
import Link from "next/link";
import { api, SearchResult } from "@/lib/api";
import { StatusBadge } from "@/components/StatusBadge";

export default function SearchPage() {
  const [query, setQuery] = useState("john.carter@example.com");
  const [ident, setIdent] = useState("");
  const [result, setResult] = useState<SearchResult | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function run(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      setResult(await api.search(query, ident || undefined));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Search failed");
    } finally {
      setBusy(false);
    }
  }

  const entity = result?.entity;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-semibold">Progressive entity search</h1>
        <p className="mt-1 max-w-2xl text-sm text-white/55">
          Start with one identifier. The engine walks every dataset in BFS hops, harvesting new
          emails, phones, usernames, and member IDs until the graph is closed.
        </p>
      </div>

      <form onSubmit={run} className="card flex flex-wrap items-end gap-3 p-5">
        <label className="min-w-[280px] flex-1 text-xs text-white/50">
          Identifier
          <input
            className="mt-1"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="email, phone, username, member id"
            required
          />
        </label>
        <label className="w-48 text-xs text-white/50">
          Type (optional)
          <select className="mt-1" value={ident} onChange={(e) => setIdent(e.target.value)}>
            <option value="">auto-detect</option>
            <option value="email">email</option>
            <option value="phone">phone</option>
            <option value="username">username</option>
            <option value="member_id">member_id</option>
          </select>
        </label>
        <button className="btn-primary" disabled={busy}>
          {busy ? "Searching..." : "Resolve entity"}
        </button>
      </form>

      {error ? (
        <div className="rounded-xl border border-rose-400/30 bg-rose-500/10 px-4 py-3 text-sm text-rose-200">
          {error}
        </div>
      ) : null}

      {result ? (
        <div className="grid gap-6 lg:grid-cols-5">
          <div className="space-y-3 lg:col-span-2">
            <div className="card p-5">
              <div className="text-xs uppercase tracking-[0.16em] text-white/45">Traversal</div>
              <div className="mt-2 font-mono text-2xl">{result.records_visited} records</div>
              <div className="mt-1 text-xs text-white/45">
                Datasets: {result.datasets_touched.join(", ") || "none"}
              </div>
            </div>
            {result.hops.map((hop, i) => (
              <div key={i} className="card p-4">
                <div className="flex items-center justify-between text-xs">
                  <span className="chip">hop {hop.hop}</span>
                  <span className="font-mono text-white/50">{hop.records_found} hits</span>
                </div>
                <div className="mt-2 font-mono text-sm">
                  {hop.identifier_type}: {hop.identifier_value}
                </div>
                {hop.new_identifiers.length > 0 ? (
                  <div className="mt-2 flex flex-wrap gap-1">
                    {hop.new_identifiers.map((n, k) => (
                      <span key={k} className="chip text-accent-400">
                        {n.identifier_type}:{n.identifier_value}
                      </span>
                    ))}
                  </div>
                ) : null}
              </div>
            ))}
          </div>

          <div className="lg:col-span-3">
            {entity ? (
              <div className="card p-6">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <h2 className="text-2xl font-semibold">{entity.display_name}</h2>
                    <p className="mt-1 text-xs text-white/45">Master entity #{entity.id}</p>
                  </div>
                  <StatusBadge status={entity.status} />
                </div>
                <div className="mt-4 flex flex-wrap gap-2">
                  {Object.entries(entity.identifiers).map(([k, vals]) =>
                    vals.map((v) => (
                      <span key={`${k}-${v}`} className="chip">
                        {k}: {v}
                      </span>
                    ))
                  )}
                </div>
                <div className="mt-6 grid gap-3 sm:grid-cols-2">
                  {Object.entries(entity.merged).map(([k, v]) => (
                    <div key={k} className="rounded-xl border border-white/10 bg-white/[0.03] px-3 py-2">
                      <div className="text-[11px] uppercase tracking-wider text-white/40">{k}</div>
                      <div className="font-mono text-sm">{v}</div>
                    </div>
                  ))}
                </div>
                <h3 className="mt-6 text-xs uppercase tracking-[0.16em] text-white/45">
                  Source attribution
                </h3>
                <div className="mt-2 overflow-x-auto">
                  <table className="w-full text-left text-xs">
                    <thead className="text-white/40">
                      <tr>
                        <th className="py-2">Field</th>
                        <th>Original</th>
                        <th>Normalized</th>
                        <th>Source</th>
                      </tr>
                    </thead>
                    <tbody>
                      {entity.fields.map((f, i) => (
                        <tr key={i} className="border-t border-white/5">
                          <td className="py-2 font-medium">{f.field_name}</td>
                          <td className="font-mono">{f.original_value}</td>
                          <td className="font-mono text-accent-400">{f.normalized_value}</td>
                          <td>
                            {f.source_db}/{f.source_table}#{f.row_id}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <div className="mt-4">
                  <Link href={`/entity/${entity.id}`} className="text-sm text-accent-400 hover:underline">
                    Open full entity card
                  </Link>
                </div>
              </div>
            ) : (
              <div className="card p-8 text-sm text-white/45">No master entity assembled for this query.</div>
            )}
          </div>
        </div>
      ) : null}
    </div>
  );
}
