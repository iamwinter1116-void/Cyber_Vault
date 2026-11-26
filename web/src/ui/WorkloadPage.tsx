import { JobTable } from "./AppComponents";
import type { Job } from "../api";

type WorkloadKind = "file_analysis" | "ai_scan";

const CONTENT: Record<WorkloadKind, { title: string; intro: string; reason: string }> = {
  file_analysis: {
    title: "Suspicious file analysis",
    intro: "Static triage, optional network-isolated detonation, and a report tied to the submitted sample hash.",
    reason: "Submission is unavailable in this local website demo because the real analyzer and detonator workers are not integrated.",
  },
  ai_scan: {
    title: "AI red-team scans",
    intro: "Offline probes against the approved target, with findings mapped to OWASP LLM risk identifiers.",
    reason: "Submission is unavailable because the real offline target and scanner worker are not integrated or approved.",
  },
};

export function WorkloadPage({ kind, jobs }: { kind: WorkloadKind; jobs: Job[] }) {
  const content = CONTENT[kind];
  const rows = jobs.filter(job => job.kind === kind);
  return <div className="dashboard-grid">
    <section className="panel span-2"><div className="panel-title"><h2>{content.title}</h2></div>
      <p>{content.intro}</p><div className="notice-banner" role="status">{content.reason} No job was submitted; no scan result is fabricated.</div>
      <button className="primary" disabled title={content.reason}>{kind === "file_analysis" ? "Upload sample" : "Start scan"}</button>
    </section>
    <section className="panel span-2"><div className="panel-title"><h2>Actual job history</h2></div><JobTable jobs={rows} /></section>
  </div>;
}
