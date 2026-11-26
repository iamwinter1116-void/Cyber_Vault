import { useCallback, useEffect, useState } from "react";
import { api, type AuditRecord, type Checkpoint, type VerifyResult } from "../api";

export function AuditPage({ csrf, canVerify, onError }: { csrf: string; canVerify: boolean; onError: (message: string) => void }) {
  const [records, setRecords] = useState<AuditRecord[]>([]); const [checkpoints, setCheckpoints] = useState<Checkpoint[]>([]);
  const [action, setAction] = useState(""); const [outcome, setOutcome] = useState("");
  const [filter, setFilter] = useState({ action: "", outcome: "" });
  const [verified, setVerified] = useState<VerifyResult | null>(null); const [busy, setBusy] = useState(false);
  const refresh = useCallback(async () => loadAudit(filter, setRecords, setCheckpoints, onError), [filter, onError]);
  useEffect(() => { void refresh(); }, [refresh]);
  const verify = async () => runVerification(csrf, setVerified, refresh, setBusy, onError);
  const download = async (kind: "records" | "checkpoints") => exportAudit(kind, onError);
  function applyFilters(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault(); setFilter({ action, outcome });
  }
  return <div className="audit-page">
    <AuditSummary checkpoints={checkpoints} verified={verified} canVerify={canVerify} busy={busy} verify={verify} download={download} />
    <AuditRecordTable records={records} action={action} outcome={outcome} setAction={setAction} setOutcome={setOutcome} applyFilters={applyFilters} />
  </div>;
}

async function loadAudit(filter: { action: string; outcome: string }, setRecords: (records: AuditRecord[]) => void, setCheckpoints: (items: Checkpoint[]) => void, onError: (message: string) => void) {
  try {
    const [recordPage, checkpointPage] = await Promise.all([api.audit(filter), api.checkpoints()]);
    setRecords(recordPage.items); setCheckpoints(checkpointPage.items);
  } catch (cause) { onError(cause instanceof Error ? cause.message : "Could not load audit data"); }
}

async function runVerification(csrf: string, setVerified: (result: VerifyResult) => void, refresh: () => Promise<void>, setBusy: (busy: boolean) => void, onError: (message: string) => void) {
  setBusy(true);
  try { setVerified(await api.verifyAudit(csrf)); await refresh(); }
  catch (cause) { onError(cause instanceof Error ? cause.message : "Verification failed"); }
  finally { setBusy(false); }
}

async function exportAudit(kind: "records" | "checkpoints", onError: (message: string) => void) {
  try {
    const url = URL.createObjectURL(await api.exportAudit(kind));
    const link = document.createElement("a"); link.href = url; link.download = `abhedya-audit-${kind}.ndjson`;
    link.click(); window.setTimeout(() => URL.revokeObjectURL(url), 1000);
  } catch (cause) { onError(cause instanceof Error ? cause.message : "Audit export failed"); }
}

function AuditSummary({ checkpoints, verified, canVerify, busy, verify, download }: { checkpoints: Checkpoint[]; verified: VerifyResult | null; canVerify: boolean; busy: boolean; verify: () => Promise<void>; download: (kind: "records" | "checkpoints") => Promise<void> }) {
  const last = checkpoints.at(-1);
  return <section className="panel"><div className="panel-title"><h2>Audit verification</h2>{canVerify && <AuditActions busy={busy} verify={verify} download={download} />}</div>
    {verified && <div className={verified.ok ? "verify-result ok" : "verify-result bad"} role="status"><strong>{verified.verdict}</strong><span>{verified.records} records · {verified.checkpoints} checkpoints · checked {verified.checked_at}</span></div>}
    <div className="checkpoint"><strong>Last checkpoint</strong>{last ? <span>Tree size {last.tree_size} · {last.ts} · root <code>{last.root_hash.slice(0, 16)}…</code></span> : <span>No checkpoint returned by the API.</span>}</div>
  </section>;
}

function AuditActions({ busy, verify, download }: { busy: boolean; verify: () => Promise<void>; download: (kind: "records" | "checkpoints") => Promise<void> }) {
  return <div className="row-actions"><button className="secondary small-button" disabled={busy} onClick={() => void download("records")}>Export records</button>
    <button className="secondary small-button" disabled={busy} onClick={() => void download("checkpoints")}>Export checkpoints</button>
    <button className="primary small-button" disabled={busy} onClick={() => void verify()}>{busy ? "Verifying…" : "Verify"}</button></div>;
}

function AuditRecordTable({ records, action, outcome, setAction, setOutcome, applyFilters }: { records: AuditRecord[]; action: string; outcome: string; setAction: (value: string) => void; setOutcome: (value: string) => void; applyFilters: (event: React.FormEvent<HTMLFormElement>) => void }) {
  return <section className="panel"><div className="panel-title"><h2>Ledger records</h2></div>
    <form className="audit-filters" onSubmit={applyFilters}><label>Action<input value={action} onChange={event => setAction(event.target.value)} placeholder="env.create" /></label>
      <label>Outcome<select value={outcome} onChange={event => setOutcome(event.target.value)}><option value="">All outcomes</option><option value="success">Success</option><option value="denied">Denied</option><option value="error">Error</option></select></label>
      <button className="secondary small-button">Apply filters</button></form>
    <div className="table-wrap"><table><thead><tr><th>Seq</th><th>Time</th><th>Actor</th><th>Action</th><th>Target</th><th>Outcome</th><th>Hash</th></tr></thead><tbody>
      {records.map(record => <tr key={record.seq}><td>{record.seq}</td><td>{record.ts}</td><td>{record.actor_role}</td><td>{record.action}</td><td>{record.target_type}:{record.target_id.slice(0, 8)}</td><td>{record.outcome}</td><td><code>{record.hash.slice(0, 14)}…</code></td></tr>)}
    </tbody></table></div>
    {!records.length && <div className="empty"><p>No audit records match the current filter.</p></div>}
  </section>;
}
