import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Activity,
  ArrowDownToLine,
  BadgeCheck,
  Bell,
  BookOpenCheck,
  Check,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  CircleHelp,
  ClipboardCheck,
  Clock3,
  Database,
  FileCheck2,
  Filter,
  LayoutDashboard,
  Link2,
  ListChecks,
  LockKeyhole,
  PanelRightClose,
  Plus,
  RefreshCw,
  Search,
  Settings2,
  Shield,
  ShieldAlert,
  ShieldCheck,
  SlidersHorizontal,
  Sparkles,
  Upload,
  X,
} from "lucide-react";

type Role = "engineer" | "reviewer" | "approver" | "admin";
type Page =
  | "overview"
  | "findings"
  | "inventory"
  | "advisories"
  | "remediation"
  | "audit";
type AnyRecord = Record<string, any>;

const NAV: { id: Page; label: string; icon: typeof LayoutDashboard }[] = [
  { id: "overview", label: "Overview", icon: LayoutDashboard },
  { id: "findings", label: "Findings", icon: ShieldAlert },
  { id: "inventory", label: "Asset inventory", icon: Database },
  { id: "advisories", label: "Advisory sources", icon: BookOpenCheck },
  { id: "remediation", label: "Remediation", icon: ClipboardCheck },
  { id: "audit", label: "Audit trail", icon: ListChecks },
];

const defaultActions: Record<string, string> = {
  "ICSA-24-226-06":
    "Review the vendor mitigation guidance for FactoryTalk View SE 13.0. Plan a validated upgrade or approved compensating control with operations.",
  "ICSA-24-256-24":
    "Review the vendor correction guidance for Pavilion8 versions prior to 5.20 and schedule a change window after operational impact review.",
  "ICSA-24-284-15":
    "Review the vendor correction guidance for DataMosaix Private Cloud 7.07 and prior. Confirm a supported target version with the system owner.",
};

function App() {
  const [page, setPage] = useState<Page>("overview");
  const [role, setRole] = useState<Role>(
    (localStorage.getItem("otproof-role") as Role) || "reviewer",
  );
  const [manualToken, setManualToken] = useState("");
  const [meta, setMeta] = useState<AnyRecord | null>(null);
  const [dashboard, setDashboard] = useState<AnyRecord | null>(null);
  const [findings, setFindings] = useState<AnyRecord[]>([]);
  const [assets, setAssets] = useState<AnyRecord[]>([]);
  const [assetTotal, setAssetTotal] = useState(0);
  const [advisories, setAdvisories] = useState<AnyRecord[]>([]);
  const [tickets, setTickets] = useState<AnyRecord[]>([]);
  const [audit, setAudit] = useState<AnyRecord[]>([]);
  const [selected, setSelected] = useState<AnyRecord | null>(null);
  const [filter, setFilter] = useState("all");
  const [search, setSearch] = useState("");
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [showTicket, setShowTicket] = useState(false);
  const [aiResult, setAiResult] = useState<AnyRecord | null>(null);
  const [decisionRationale, setDecisionRationale] = useState("");
  const [decisionChoice, setDecisionChoice] = useState<
    "applicable" | "not_applicable" | ""
  >("");
  const [ticketForm, setTicketForm] = useState({
    assigned_to: "OT Maintenance Engineer",
    due_date: "",
    planned_mitigation: "",
    proposed_action: "",
  });
  const [evidenceForm, setEvidenceForm] = useState({
    evidence_type: "Change record",
    label: "Simulated maintenance change record",
    reference: "CHG-2026-1042",
    notes:
      "Synthetic evidence record for the demo. Confirm installation and operational checks during the approved change window.",
    content: "SIMULATED EVIDENCE — no production system change was performed.",
  });
  const [reviewNote, setReviewNote] = useState(
    "Reviewed against the linked public advisory and current inventory record.",
  );

  const token = meta?.demo_mode ? meta?.demo_tokens?.[role] || "" : manualToken;
  const api = useCallback(
    async (path: string, init: RequestInit = {}) => {
      const headers = new Headers(init.headers);
      if (token) headers.set("Authorization", `Bearer ${token}`);
      if (init.body && !(init.body instanceof FormData))
        headers.set("Content-Type", "application/json");
      const response = await fetch(path, { ...init, headers });
      const type = response.headers.get("content-type") || "";
      const payload = type.includes("application/json")
        ? await response.json()
        : await response.text();
      if (!response.ok)
        throw new Error(
          typeof payload === "object"
            ? payload.detail || response.statusText
            : response.statusText,
        );
      return payload;
    },
    [token],
  );

  const refresh = useCallback(async () => {
    setError("");
    const [
      summary,
      findingData,
      assetData,
      advisoryData,
      ticketData,
      auditData,
    ] = await Promise.all([
      api("/api/dashboard"),
      api("/api/findings"),
      api("/api/assets"),
      api("/api/advisories"),
      api("/api/tickets"),
      api("/api/audit"),
    ]);
    setDashboard(summary);
    setFindings(findingData.items);
    setAssets(assetData.items);
    setAssetTotal(assetData.total);
    setAdvisories(advisoryData.items);
    setTickets(ticketData.items);
    setAudit(auditData.items);
    setSelected((old: AnyRecord | null) =>
      old
        ? findingData.items.find((x: AnyRecord) => x.id === old.id) || null
        : null,
    );
  }, [api]);

  useEffect(() => {
    fetch("/api/meta")
      .then((r) => r.json())
      .then(setMeta)
      .catch(() =>
        setError(
          "The OTProof API is not reachable. Start the local stack and refresh.",
        ),
      );
  }, []);
  useEffect(() => {
    if (meta) refresh().catch((e: Error) => setError(e.message));
  }, [meta, refresh]);
  useEffect(() => {
    localStorage.setItem("otproof-role", role);
  }, [role]);

  const run = async (
    label: string,
    action: () => Promise<any>,
    success?: (value: any) => string,
  ) => {
    setBusy(label);
    setError("");
    setNotice("");
    try {
      const value = await action();
      await refresh();
      setNotice(success ? success(value) : `${label} complete.`);
      return value;
    } catch (e) {
      setError(e instanceof Error ? e.message : "Request failed");
      return null;
    } finally {
      setBusy("");
    }
  };

  const analyze = () =>
    run(
      "Analysis",
      () => api("/api/analyze", { method: "POST" }),
      (x) =>
        `Compared ${x.assets_scanned} assets with ${x.advisories_compared} advisories · ${x.applicable_candidates} applicable candidates · ${x.requires_manual_verification} need engineering review.`,
    );

  const filteredFindings = useMemo(
    () =>
      findings.filter((f) => {
        const term = search.trim().toLowerCase();
        const matchesSearch =
          !term ||
          [
            f.asset.asset_id,
            f.asset.vendor,
            f.asset.product,
            f.advisory.external_id,
            f.advisory.title,
            ...(f.advisory.cves || []),
          ]
            .join(" ")
            .toLowerCase()
            .includes(term);
        const matchesFilter =
          filter === "all" ||
          (filter === "applicable" && f.applicability === "applicable") ||
          (filter === "manual" &&
            f.applicability === "requires_manual_verification") ||
          (filter === "notapp" && f.applicability === "not_applicable") ||
          (filter === "unresolved" && f.status === "requires_review");
        return matchesSearch && matchesFilter;
      }),
    [findings, filter, search],
  );

  const decide = async (decision: "applicable" | "not_applicable") => {
    if (!selected || decisionRationale.trim().length < 12) return;
    const result = await run(
      "Engineering decision",
      () =>
        api(`/api/findings/${selected.id}/decision`, {
          method: "POST",
          body: JSON.stringify({ decision, rationale: decisionRationale }),
        }),
      () => `Finding ${selected.id} recorded as ${decision.replace("_", " ")}.`,
    );
    if (result) {
      setDecisionRationale("");
      setDecisionChoice("");
    }
  };

  const submitTicket = async () => {
    if (!selected) return;
    const body = {
      ...ticketForm,
      due_date: ticketForm.due_date || null,
      proposed_action:
        ticketForm.proposed_action ||
        defaultActions[selected.advisory.external_id] ||
        "Review approved vendor guidance and prepare an operationally safe mitigation plan.",
    };
    const result = await run(
      "Ticket proposal",
      () =>
        api(`/api/findings/${selected.id}/tickets`, {
          method: "POST",
          body: JSON.stringify(body),
        }),
      (x) => `Remediation proposal #${x.id} is awaiting approver review.`,
    );
    if (result) setShowTicket(false);
  };

  const decideTicket = (ticket: AnyRecord, decision: "approved" | "rejected") =>
    run(
      "Ticket decision",
      () =>
        api(`/api/tickets/${ticket.id}/decision`, {
          method: "POST",
          body: JSON.stringify({ decision, rationale: reviewNote }),
        }),
      () => `Ticket #${ticket.id} ${decision}.`,
    );

  const attachEvidence = async (ticket: AnyRecord) => {
    if (!selected) return;
    const result = await run(
      "Evidence record",
      () =>
        api(`/api/findings/${selected.id}/evidence`, {
          method: "POST",
          body: JSON.stringify({ ...evidenceForm, ticket_id: ticket.id }),
        }),
      (x) =>
        `Evidence record #${x.id} attached. Finding is pending verification.`,
    );
    if (result)
      setEvidenceForm((f) => ({
        ...f,
        label: "Simulated maintenance change record",
      }));
  };

  const verify = (evidence: AnyRecord) =>
    selected &&
    run(
      "Verification",
      () =>
        api(`/api/findings/${selected.id}/verify`, {
          method: "POST",
          body: JSON.stringify({
            evidence_id: evidence.id,
            rationale: reviewNote,
          }),
        }),
      () =>
        `Finding ${selected.id} is now verified remediated by the approver.`,
    );

  const uploadInventory = async (file?: File) => {
    if (!file) return;
    const form = new FormData();
    form.append("file", file);
    await run(
      "Inventory import",
      () => api("/api/assets/import", { method: "POST", body: form }),
      (x) =>
        `Imported ${x.imported} asset rows. Re-run analysis to refresh applicability.`,
    );
  };

  const ingest = (source: "cisa-ics" | "cisa-kev") =>
    run(
      "Source ingestion",
      () => api(`/api/ingest/${source}`, { method: "POST" }),
      (x) =>
        `${x.source}: ${x.items_seen} entries processed; ${x.inserted} new.`,
    );

  const pageTitle = NAV.find((x) => x.id === page)?.label || "Overview";
  const countLabel = findings.filter(
    (f) => f.status === "requires_review",
  ).length;

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">
            <ShieldCheck size={21} strokeWidth={2.4} />
          </div>
          <div>
            <strong>OTProof</strong>
            <span>INDUSTRIAL ASSURANCE</span>
          </div>
        </div>
        <div className="site-switch">
          <div className="site-avatar">CV</div>
          <div className="site-copy">
            <span>DEMO WORKSPACE</span>
            <strong>Cedar Valley Water</strong>
          </div>
          <ChevronDown size={15} />
        </div>
        <div className="nav-caption">WORKSPACE</div>
        <nav>
          {NAV.map((item) => {
            const Icon = item.icon;
            return (
              <button
                key={item.id}
                className={`nav-item ${page === item.id ? "active" : ""}`}
                onClick={() => setPage(item.id)}
              >
                <Icon size={17} />
                <span>{item.label}</span>
                {item.id === "findings" && countLabel > 0 && (
                  <em>{countLabel}</em>
                )}
              </button>
            );
          })}
        </nav>
        <div className="sidebar-bottom">
          <div className="passive-note">
            <div className="passive-icon">
              <Activity size={15} />
            </div>
            <div>
              <strong>Passive by design</strong>
              <span>No OT connections</span>
            </div>
            <span className="live-dot" />
          </div>
          <button className="nav-item">
            <Settings2 size={17} />
            <span>Workspace settings</span>
          </button>
          <div className="user-row">
            <div className="user-avatar">DA</div>
            <div>
              <strong>Demo Reviewer</strong>
              <span>Water systems team</span>
            </div>
            <ChevronDown size={15} />
          </div>
        </div>
      </aside>

      <main className="main-area">
        <header className="topbar">
          <div className="crumbs">
            <span>OTProof</span>
            <ChevronRight size={14} />
            <strong>{pageTitle}</strong>
            <span className="demo-pill">
              {meta?.demo_mode ? "DEMO DATA" : "CONNECTED API"}
            </span>
          </div>
          <div className="top-actions">
            <div className="data-freshness">
              <span className="fresh-dot" />
              Sources checked <strong>Oct 26, 2026</strong>
            </div>
            <button className="icon-button" aria-label="Notifications">
              <Bell size={17} />
              <i />
            </button>
            <label className="role-switch">
              <span>ROLE</span>
              <select
                value={role}
                onChange={(e) => setRole(e.target.value as Role)}
              >
                <option value="reviewer">Reviewer</option>
                <option value="engineer">Engineer</option>
                <option value="approver">Approver</option>
                <option value="admin">Admin</option>
              </select>
              <ChevronDown size={13} />
            </label>
            {!meta?.demo_mode && (
              <label className="token-entry">
                <span>API TOKEN</span>
                <input
                  aria-label="API token"
                  type="password"
                  autoComplete="off"
                  value={manualToken}
                  onChange={(e) => setManualToken(e.target.value)}
                  placeholder="Paste role token"
                />
              </label>
            )}
          </div>
        </header>

        {(error || notice) && (
          <div className={`flash ${error ? "flash-error" : "flash-success"}`}>
            <span>{error || notice}</span>
            <button
              onClick={() => {
                setError("");
                setNotice("");
              }}
            >
              <X size={15} />
            </button>
          </div>
        )}

        <div className="page-content">
          {page === "overview" && (
            <Overview
              dashboard={dashboard}
              findings={findings}
              advisories={advisories}
              onAnalyze={analyze}
              busy={busy}
              onOpenFindings={() => setPage("findings")}
              onIngest={ingest}
              onReport={() =>
                window.open("/api/report/assurance.pdf", "_blank")
              }
            />
          )}
          {page === "findings" && (
            <section className="findings-layout">
              <div className="findings-main">
                <div className="page-heading">
                  <div>
                    <div className="eyebrow">ENGINEERING REVIEW QUEUE</div>
                    <h1>Vulnerability findings</h1>
                    <p>
                      Deterministic product and version comparisons with
                      source-linked evidence.
                    </p>
                  </div>
                  <button
                    className="button button-primary"
                    onClick={analyze}
                    disabled={!!busy}
                  >
                    <RefreshCw
                      size={15}
                      className={busy === "Analysis" ? "spin" : ""}
                    />
                    Run analysis
                  </button>
                </div>
                <FindingWorkspace
                  findings={filteredFindings}
                  total={findings.length}
                  filter={filter}
                  setFilter={setFilter}
                  search={search}
                  setSearch={setSearch}
                  selected={selected}
                  onSelect={setSelected}
                />
                {findings.length === 0 && (
                  <EmptyState onAnalyze={analyze} busy={busy} />
                )}
              </div>
              <FindingDetail
                finding={selected}
                role={role}
                busy={busy}
                onStartDecision={setDecisionChoice}
                decisionChoice={decisionChoice}
                decisionRationale={decisionRationale}
                setDecisionRationale={setDecisionRationale}
                onDecide={decide}
                onShowTicket={() => setShowTicket(true)}
                showTicket={showTicket}
                ticketForm={ticketForm}
                setTicketForm={setTicketForm}
                onSubmitTicket={submitTicket}
                onTicketDecision={decideTicket}
                evidenceForm={evidenceForm}
                setEvidenceForm={setEvidenceForm}
                onAttachEvidence={attachEvidence}
                onVerify={verify}
                reviewNote={reviewNote}
                setReviewNote={setReviewNote}
                onAI={async () => {
                  const result = await run(
                    "AI extraction",
                    () =>
                      api(
                        `/api/advisories/${selected?.advisory.id}/ai-extract`,
                        { method: "POST" },
                      ),
                    () =>
                      "Local model returned a source-quoted draft. It has no authority over the finding.",
                  );
                  if (result) setAiResult(result);
                }}
                aiResult={aiResult}
              />
            </section>
          )}
          {page === "inventory" && (
            <InventoryView
              assets={assets}
              total={assetTotal}
              search={search}
              setSearch={setSearch}
              onUpload={uploadInventory}
              onAnalyze={analyze}
              busy={busy}
            />
          )}
          {page === "advisories" && (
            <AdvisoriesView
              advisories={advisories}
              onIngest={ingest}
              onNvd={(cve: string) =>
                run(
                  "NVD ingestion",
                  () => api(`/api/ingest/nvd/${cve}`, { method: "POST" }),
                  (x) => `${x.external_id} added from NVD.`,
                )
              }
              onVendor={(url: string) =>
                run(
                  "Vendor bulletin",
                  () =>
                    api(`/api/ingest/vendor?url=${encodeURIComponent(url)}`, {
                      method: "POST",
                    }),
                  (x) => `${x.external_id} imported from vendor source.`,
                )
              }
              busy={busy}
            />
          )}
          {page === "remediation" && (
            <RemediationView
              tickets={tickets}
              findings={findings}
              role={role}
              onSelectFinding={(f: AnyRecord) => {
                setSelected(f);
                setPage("findings");
              }}
              reviewNote={reviewNote}
              setReviewNote={setReviewNote}
            />
          )}
          {page === "audit" && <AuditView audit={audit} />}
        </div>
        <footer className="footer-note">
          <span>
            <LockKeyhole size={13} /> Read-only OT posture · no device access or
            active scanning
          </span>
          <span>
            OTProof MVP v0.1 <i>•</i> Evidence remains subject to human approval
          </span>
        </footer>
      </main>
    </div>
  );
}

function Overview({
  dashboard,
  findings,
  advisories,
  onAnalyze,
  busy,
  onOpenFindings,
  onIngest,
  onReport,
}: AnyRecord) {
  const pending = findings.filter(
    (f: AnyRecord) => f.status === "requires_review",
  );
  const high = pending.filter((f: AnyRecord) =>
    ["High", "Critical"].includes(f.asset.criticality),
  );
  const colorsBy = {
    applicable: "#d57834",
    manual: "#c19b38",
    notapp: "#5d9093",
  };
  return (
    <>
      <div className="overview-hero">
        <div className="hero-grid" />
        <div className="hero-copy">
          <div className="eyebrow light">PASSIVE VULNERABILITY ASSURANCE</div>
          <h1>
            Evidence you can
            <br />
            take to the control room.
          </h1>
          <p>
            Turn public advisories and asset records into a reviewable,
            source-linked workflow. Every applicability call stays explainable.
            Every remediation needs an engineer and an approver.
          </p>
          <div className="hero-buttons">
            <button
              className="button button-light"
              onClick={onAnalyze}
              disabled={!!busy}
            >
              <RefreshCw
                size={15}
                className={busy === "Analysis" ? "spin" : ""}
              />
              {busy === "Analysis"
                ? "Analyzing…"
                : "Run applicability analysis"}
            </button>
            <button
              className="button button-ghost-light"
              onClick={onOpenFindings}
            >
              Review findings <ChevronRight size={15} />
            </button>
          </div>
        </div>
        <div className="hero-stamp">
          <div className="stamp-ring">
            <ShieldCheck size={36} />
          </div>
          <span>PASSIVE</span>
          <strong>BY DESIGN</strong>
          <small>Inventory + public data</small>
        </div>
        <div className="hero-bottom">
          <span>
            <span className="green-check">
              <Check size={11} />
            </span>{" "}
            No network probing
          </span>
          <span>
            <span className="green-check">
              <Check size={11} />
            </span>{" "}
            No automatic remediation
          </span>
          <span>
            <span className="green-check">
              <Check size={11} />
            </span>{" "}
            Human-approved evidence
          </span>
        </div>
      </div>
      <div className="section-title-row">
        <div>
          <div className="eyebrow">WORKSPACE SNAPSHOT</div>
          <h2>Assurance overview</h2>
        </div>
        <button className="button button-outline" onClick={onReport}>
          <ArrowDownToLine size={15} />
          Download assurance report
        </button>
      </div>
      <div className="metric-grid">
        <Metric
          icon={Database}
          label="Assets in scope"
          value={dashboard?.asset_count ?? "—"}
          sub={`${dashboard?.assets_reviewed ?? 0} inventory records verified`}
          tone="teal"
        />
        <Metric
          icon={ShieldAlert}
          label="Applicable candidates"
          value={dashboard?.applicable ?? "—"}
          sub="Require engineer decision"
          tone="amber"
          delta="REVIEW"
        />
        <Metric
          icon={CircleHelp}
          label="Manual verification"
          value={dashboard?.requires_manual_verification ?? "—"}
          sub="Incomplete or ambiguous inventory"
          tone="blue"
        />
        <Metric
          icon={FileCheck2}
          label="Verified remediations"
          value={dashboard?.verified_remediated ?? "—"}
          sub={`${dashboard?.evidence_completeness ?? 0}% findings with evidence`}
          tone="green"
        />
      </div>
      <div className="overview-grid">
        <div className="card exposure-card">
          <div className="card-head">
            <div>
              <h3>Applicability review</h3>
              <p>
                Deterministic screening results across the current inventory.
              </p>
            </div>
            <button className="text-button" onClick={onOpenFindings}>
              Open queue <ChevronRight size={14} />
            </button>
          </div>
          <div className="exposure-total">
            <strong>{dashboard?.finding_count ?? 0}</strong>
            <span>candidate pairs</span>
          </div>
          <div className="stack-bar">
            <i
              style={{
                width: `${dashboard?.finding_count ? (dashboard.applicable / dashboard.finding_count) * 100 : 0}%`,
                background: colorsBy.applicable,
              }}
            />
            <i
              style={{
                width: `${dashboard?.finding_count ? (dashboard.requires_manual_verification / dashboard.finding_count) * 100 : 0}%`,
                background: colorsBy.manual,
              }}
            />
            <i
              style={{
                width: `${dashboard?.finding_count ? (dashboard.not_applicable / dashboard.finding_count) * 100 : 0}%`,
                background: colorsBy.notapp,
              }}
            />
          </div>
          <div className="legend-grid">
            <Legend
              label="Applicable"
              value={dashboard?.applicable ?? 0}
              color={colorsBy.applicable}
            />
            <Legend
              label="Needs review"
              value={dashboard?.requires_manual_verification ?? 0}
              color={colorsBy.manual}
            />
            <Legend
              label="Not applicable"
              value={dashboard?.not_applicable ?? 0}
              color={colorsBy.notapp}
            />
          </div>
          <div className="exposure-foot">
            <span>
              <span className="live-dot" /> Source-linked output
            </span>
            <span>Updated just now</span>
          </div>
        </div>
        <div className="card queue-card">
          <div className="card-head">
            <div>
              <h3>Priority review queue</h3>
              <p>High criticality assets with open candidate findings.</p>
            </div>
            <span className="small-count">{high.length} OPEN</span>
          </div>
          {high.length ? (
            high.slice(0, 4).map((f: AnyRecord) => (
              <div className="queue-row" key={f.id} onClick={onOpenFindings}>
                <div
                  className={`priority-dot ${f.asset.criticality.toLowerCase()}`}
                />
                <div className="queue-copy">
                  <strong>
                    {f.asset.asset_id} <span>·</span> {f.asset.product}
                  </strong>
                  <small>
                    {f.advisory.external_id} <span>·</span>{" "}
                    {f.asset.firmware_version || "Version missing"}
                  </small>
                </div>
                <StatusPill value={f.applicability} compact />
                <ChevronRight size={15} className="queue-arrow" />
              </div>
            ))
          ) : (
            <div className="empty-compact">
              <span className="check-circle">
                <CheckCircle2 size={20} />
              </span>
              <strong>Review queue is clear</strong>
              <span>Run analysis or import a new inventory.</span>
            </div>
          )}
          <button className="queue-link" onClick={onOpenFindings}>
            View all findings <ArrowDownToLine size={14} />
          </button>
        </div>
      </div>
      <div className="lower-grid">
        <div className="card source-card">
          <div className="card-head">
            <div>
              <h3>Public advisory sources</h3>
              <p>Official sources cached with their update timestamps.</p>
            </div>
            <button
              className="round-icon"
              aria-label="Refresh sources"
              onClick={() => onIngest("cisa-ics")}
            >
              <RefreshCw size={15} />
            </button>
          </div>
          <SourceRow
            logo="C"
            name="CISA ICS Advisories"
            detail="Official industrial control advisories"
            status={
              advisories.some((a: AnyRecord) => a.source === "CISA ICS")
                ? `${advisories.filter((a: AnyRecord) => a.source === "CISA ICS").length} advisories`
                : "Not loaded"
            }
          />
          <SourceRow
            logo="K"
            name="Known Exploited Vulnerabilities"
            detail="CISA catalog · public JSON"
            status={
              advisories.some((a: AnyRecord) => a.source === "CISA KEV")
                ? "Imported"
                : "Available"
            }
          />
          <SourceRow
            logo="N"
            name="NVD CVE records"
            detail="Official CVE API · on-demand lookup"
            status="On demand"
          />
        </div>
        <div className="card next-card">
          <div className="next-icon">
            <Sparkles size={20} />
          </div>
          <div>
            <div className="eyebrow">NEXT STEP</div>
            <h3>Keep decisions grounded in evidence.</h3>
            <p>
              Advisory text can guide review. Only a named engineer can confirm
              applicability, and an approver verifies remediation.
            </p>
            <button className="text-button" onClick={onOpenFindings}>
              Open engineering queue <ChevronRight size={14} />
            </button>
          </div>
        </div>
      </div>
    </>
  );
}

function Metric({ icon: Icon, label, value, sub, tone, delta }: AnyRecord) {
  return (
    <div className="metric-card">
      <div className={`metric-icon ${tone}`}>
        <Icon size={17} />
      </div>
      <div className="metric-copy">
        <span>{label}</span>
        <strong>{value}</strong>
        <small>{sub}</small>
      </div>
      {delta && <span className="metric-delta">{delta}</span>}
    </div>
  );
}
function Legend({ label, value, color }: AnyRecord) {
  return (
    <div className="legend-item">
      <span style={{ background: color }} />
      <div>
        <strong>{value}</strong>
        <small>{label}</small>
      </div>
    </div>
  );
}
function SourceRow({ logo, name, detail, status }: AnyRecord) {
  return (
    <div className="source-row">
      <div className={`source-logo ${logo.toLowerCase()}`}>{logo}</div>
      <div className="source-copy">
        <strong>{name}</strong>
        <small>{detail}</small>
      </div>
      <span className="source-status">{status}</span>
    </div>
  );
}

function StatusPill({
  value,
  compact = false,
}: {
  value: string;
  compact?: boolean;
}) {
  const key =
    value === "applicable"
      ? "applicable"
      : value === "not_applicable"
        ? "notapp"
        : value === "verified_remediated"
          ? "verified"
          : value === "open"
            ? "open"
            : "manual";
  const labels: Record<string, string> = {
    applicable: "Applicable",
    manual: "Needs review",
    notapp: "Not applicable",
    verified: "Verified",
    open: "Open",
  };
  return (
    <span className={`status-pill ${key} ${compact ? "compact" : ""}`}>
      <i />
      {labels[key]}
    </span>
  );
}

function FindingWorkspace({
  findings,
  total,
  filter,
  setFilter,
  search,
  setSearch,
  selected,
  onSelect,
}: AnyRecord) {
  const tabs = [
    ["all", "All findings", total],
    [
      "unresolved",
      "Needs review",
      findings.filter((f: AnyRecord) => f.status === "requires_review").length,
    ],
    [
      "applicable",
      "Applicable",
      findings.filter((f: AnyRecord) => f.applicability === "applicable")
        .length,
    ],
    [
      "manual",
      "Ambiguous",
      findings.filter(
        (f: AnyRecord) => f.applicability === "requires_manual_verification",
      ).length,
    ],
    [
      "notapp",
      "Not applicable",
      findings.filter((f: AnyRecord) => f.applicability === "not_applicable")
        .length,
    ],
  ];
  return (
    <div className="card finding-table-card">
      <div className="finding-toolbar">
        <div className="filter-tabs">
          {tabs.map(([key, label, count]) => (
            <button
              key={key}
              className={filter === key ? "selected" : ""}
              onClick={() => setFilter(key)}
            >
              {label}
              <b>{count}</b>
            </button>
          ))}
        </div>
        <div className="search-box">
          <Search size={15} />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search findings"
          />
          <button>
            <SlidersHorizontal size={15} />
          </button>
        </div>
      </div>
      <div className="table-scroll">
        <table className="findings-table">
          <thead>
            <tr>
              <th>ASSET / PRODUCT</th>
              <th>ADVISORY</th>
              <th>APPLICABILITY</th>
              <th>CRITICALITY</th>
              <th>OWNER</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {findings.map((f: AnyRecord) => (
              <tr
                key={f.id}
                className={selected?.id === f.id ? "selected-row" : ""}
                onClick={() => onSelect(f)}
              >
                <td>
                  <div className="asset-name">
                    <span
                      className={`type-icon ${f.asset.equipment_type.toLowerCase().includes("hmi") ? "hmi" : "plc"}`}
                    >
                      {f.asset.equipment_type.toLowerCase().includes("hmi")
                        ? "H"
                        : "O"}
                    </span>
                    <div>
                      <strong>{f.asset.asset_id}</strong>
                      <small>
                        {f.asset.product} ·{" "}
                        {f.asset.firmware_version || "Version missing"}
                      </small>
                    </div>
                  </div>
                </td>
                <td>
                  <strong className="advisory-code">
                    {f.advisory.external_id}
                  </strong>
                  <small>{f.advisory.cves?.[0] || f.advisory.source}</small>
                </td>
                <td>
                  <StatusPill value={f.applicability} compact />
                </td>
                <td>
                  <span
                    className={`criticality ${f.asset.criticality.toLowerCase()}`}
                  >
                    <i />
                    {f.asset.criticality}
                  </span>
                </td>
                <td className="owner-cell">{f.asset.review_owner}</td>
                <td>
                  <ChevronRight size={15} className="table-chevron" />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {findings.length === 0 && (
          <div className="table-empty">
            <ShieldCheck size={24} />
            <strong>No findings match this view.</strong>
            <span>Run an applicability analysis or change the filters.</span>
          </div>
        )}
      </div>
      <div className="table-foot">
        <span>
          Showing <strong>{findings.length}</strong> of {total} candidate
          findings
        </span>
        <span>Public source · deterministic version match</span>
      </div>
    </div>
  );
}

function EmptyState({ onAnalyze, busy }: AnyRecord) {
  return (
    <div className="empty-state">
      <div className="empty-icon">
        <Shield size={23} />
      </div>
      <h3>Start the review</h3>
      <p>
        80 fictional Cedar Valley Water assets and three real CISA ICS
        advisories are loaded. Run the deterministic matcher to produce
        source-linked candidate findings.
      </p>
      <button
        className="button button-primary"
        onClick={onAnalyze}
        disabled={!!busy}
      >
        <RefreshCw size={14} />
        Run applicability analysis
      </button>
    </div>
  );
}

function FindingDetail({
  finding,
  role,
  busy,
  onStartDecision,
  decisionChoice,
  decisionRationale,
  setDecisionRationale,
  onDecide,
  onShowTicket,
  showTicket,
  ticketForm,
  setTicketForm,
  onSubmitTicket,
  onTicketDecision,
  evidenceForm,
  setEvidenceForm,
  onAttachEvidence,
  onVerify,
  reviewNote,
  setReviewNote,
  onAI,
  aiResult,
}: AnyRecord) {
  if (!finding)
    return (
      <aside className="detail-panel blank-detail">
        <div className="blank-detail-icon">
          <PanelRightClose size={21} />
        </div>
        <strong>Select a finding</strong>
        <span>
          Review exact product, version, source evidence, and workflow history.
        </span>
      </aside>
    );
  const allowedReview = role === "reviewer" || role === "admin";
  const allowedEngineer = ["engineer", "reviewer", "admin"].includes(role);
  const allowedApprove = ["approver", "admin"].includes(role);
  const ticket = finding.tickets?.[0];
  const evidence = finding.evidence_records?.[0];
  return (
    <aside className="detail-panel">
      <div className="detail-head">
        <div>
          <span className="eyebrow">FINDING #{finding.id}</span>
          <button
            className="close-detail"
            onClick={() => {}}
            aria-label="Selected finding"
          >
            <PanelRightClose size={16} />
          </button>
        </div>
        <StatusPill value={finding.applicability} compact />
        <h2>{finding.asset.product}</h2>
        <p>
          {finding.asset.asset_id} · {finding.asset.equipment_type} ·{" "}
          {finding.asset.site}
        </p>
      </div>
      <div className="detail-scroll">
        <div className="detail-section">
          <h4>ASSET EVIDENCE</h4>
          <div className="evidence-grid">
            <div>
              <small>Vendor / manufacturer</small>
              <strong>{finding.asset.vendor}</strong>
            </div>
            <div>
              <small>Model</small>
              <strong>{finding.asset.model || "Not recorded"}</strong>
            </div>
            <div>
              <small>Firmware / software</small>
              <strong>{finding.asset.firmware_version || "Missing"}</strong>
            </div>
            <div>
              <small>Last verified</small>
              <strong>{finding.asset.last_verified || "Not recorded"}</strong>
            </div>
          </div>
        </div>
        <div className="detail-section">
          <h4>ADVISORY MATCH</h4>
          <div className="source-citation">
            <div className="cisa-mark">C</div>
            <div>
              <strong>{finding.advisory.external_id}</strong>
              <span>{finding.advisory.title}</span>
            </div>
            <a
              href={finding.advisory.source_url}
              target="_blank"
              rel="noreferrer"
              aria-label="Open source"
            >
              <Link2 size={15} />
            </a>
          </div>
          <div className="source-date">
            Published {finding.advisory.published_at || "date unavailable"} ·{" "}
            {finding.advisory.source}
          </div>
          {finding.advisory.cves?.map((c: string) => (
            <span className="cve-chip" key={c}>
              {c}
            </span>
          ))}
          <div className="match-proof">
            <div className="proof-check">
              <Check size={13} />
            </div>
            <div>
              <strong>Version constraint from source</strong>
              <code>
                {finding.evidence?.matching_source_statement ||
                  finding.evidence?.matched_constraint?.source_statement ||
                  finding.advisory.affected_products?.[0]?.constraints
                    ?.map((x: AnyRecord) => x.raw)
                    .join(" AND ") ||
                  "No supported range: manual verification"}
              </code>
              {finding.reasons?.map((reason: string, i: number) => (
                <small key={i}>{reason}</small>
              ))}
            </div>
          </div>
          <div className="evidence-hash">
            <span>Source URL</span>
            <a
              href={finding.advisory.source_url}
              target="_blank"
              rel="noreferrer"
            >
              Open official advisory <ChevronRight size={13} />
            </a>
          </div>
        </div>
        <div className="detail-section">
          <h4>ENGINEERING DECISION</h4>
          {finding.decision !== "pending" ? (
            <div className="decision-record">
              <BadgeCheck size={17} />
              <div>
                <strong>{finding.decision.replace("_", " ")}</strong>
                <span>{finding.decision_rationale}</span>
                <small>Recorded by {finding.decided_by}</small>
              </div>
            </div>
          ) : (
            <>
              <p className="help-copy">
                Confirm the source and current asset details. This action is
                recorded with your role and rationale.
              </p>
              {allowedReview ? (
                decisionChoice ? (
                  <div className="form-stack">
                    <textarea
                      value={decisionRationale}
                      onChange={(e) => setDecisionRationale(e.target.value)}
                      placeholder="Explain the engineering decision (min 12 characters)"
                    />
                    <div className="inline-actions">
                      <button
                        className="button button-primary"
                        onClick={() => onDecide(decisionChoice)}
                        disabled={
                          decisionRationale.trim().length < 12 || !!busy
                        }
                      >
                        <Check size={14} />
                        Record decision
                      </button>
                      <button
                        className="button button-outline"
                        onClick={() => onStartDecision("")}
                      >
                        Cancel
                      </button>
                    </div>
                  </div>
                ) : (
                  <div className="inline-actions">
                    <button
                      className="button button-primary"
                      onClick={() => onStartDecision("applicable")}
                    >
                      Confirm applicable
                    </button>
                    <button
                      className="button button-outline"
                      onClick={() => onStartDecision("not_applicable")}
                    >
                      Mark not applicable
                    </button>
                  </div>
                )
              ) : (
                <span className="role-hint">
                  <LockKeyhole size={13} />
                  Reviewer role required to decide
                </span>
              )}
            </>
          )}
        </div>
        {finding.decision === "applicable" && (
          <div className="detail-section">
            <h4>REMEDIATION ASSURANCE</h4>
            {ticket ? (
              <div className="ticket-card">
                <div className="ticket-top">
                  <span>PROPOSAL #{ticket.id}</span>
                  <StatusPill
                    value={
                      ticket.status === "verified_remediated"
                        ? "verified"
                        : ticket.status === "proposed"
                          ? "manual"
                          : "open"
                    }
                    compact
                  />
                </div>
                <strong>{ticket.title}</strong>
                <p>{ticket.proposed_action}</p>
                <div className="ticket-meta">
                  <span>
                    Assigned to <b>{ticket.assigned_to}</b>
                  </span>
                  <span>
                    Due <b>{ticket.due_date || "Not set"}</b>
                  </span>
                </div>
                {ticket.status === "proposed" && allowedApprove && (
                  <>
                    <textarea
                      className="compact-textarea"
                      value={reviewNote}
                      onChange={(e) => setReviewNote(e.target.value)}
                    />
                    <div className="inline-actions">
                      <button
                        className="button button-primary"
                        onClick={() => onTicketDecision(ticket, "approved")}
                      >
                        <Check size={14} />
                        Approve proposal
                      </button>
                      <button
                        className="button button-danger-outline"
                        onClick={() => onTicketDecision(ticket, "rejected")}
                      >
                        Reject
                      </button>
                    </div>
                  </>
                )}
                {ticket.status === "proposed" && !allowedApprove && (
                  <span className="role-hint">
                    <LockKeyhole size={13} />
                    Waiting for approver review
                  </span>
                )}
                {ticket.status === "approved" && (
                  <>
                    <div className="evidence-forms">
                      <label>
                        Evidence label
                        <input
                          value={evidenceForm.label}
                          onChange={(e) =>
                            setEvidenceForm({
                              ...evidenceForm,
                              label: e.target.value,
                            })
                          }
                        />
                      </label>
                      <label>
                        Change record / reference
                        <input
                          value={evidenceForm.reference}
                          onChange={(e) =>
                            setEvidenceForm({
                              ...evidenceForm,
                              reference: e.target.value,
                            })
                          }
                        />
                      </label>
                      <label>
                        Evidence notes
                        <textarea
                          value={evidenceForm.notes}
                          onChange={(e) =>
                            setEvidenceForm({
                              ...evidenceForm,
                              notes: e.target.value,
                            })
                          }
                        />
                      </label>
                      <button
                        className="button button-outline full-width"
                        onClick={() => onAttachEvidence(ticket)}
                        disabled={!allowedEngineer}
                      >
                        <Plus size={14} />
                        Attach simulated evidence record
                      </button>
                    </div>
                  </>
                )}
                {ticket.status === "mitigated_pending_verification" && (
                  <div className="pending-verification">
                    <Clock3 size={15} />
                    <span>
                      Evidence is attached. An approver must verify the record
                      to close this finding.
                    </span>
                  </div>
                )}
                {ticket.status === "verified_remediated" && (
                  <div className="verified-banner">
                    <CheckCircle2 size={16} />
                    Verified by approver · {evidence?.verified_at?.slice(0, 10)}
                  </div>
                )}
              </div>
            ) : finding.status === "open" && allowedEngineer ? (
              showTicket ? (
                <div className="form-stack">
                  <label>
                    Assigned engineer
                    <input
                      value={ticketForm.assigned_to}
                      onChange={(e) =>
                        setTicketForm({
                          ...ticketForm,
                          assigned_to: e.target.value,
                        })
                      }
                    />
                  </label>
                  <label>
                    Target date
                    <input
                      type="date"
                      value={ticketForm.due_date}
                      onChange={(e) =>
                        setTicketForm({
                          ...ticketForm,
                          due_date: e.target.value,
                        })
                      }
                    />
                  </label>
                  <label>
                    Proposed action
                    <textarea
                      value={
                        ticketForm.proposed_action ||
                        defaultActions[finding.advisory.external_id] ||
                        ""
                      }
                      onChange={(e) =>
                        setTicketForm({
                          ...ticketForm,
                          proposed_action: e.target.value,
                        })
                      }
                    />
                  </label>
                  <div className="inline-actions">
                    <button
                      className="button button-primary"
                      onClick={onSubmitTicket}
                    >
                      <Plus size={14} />
                      Submit for approval
                    </button>
                    <button
                      className="button button-outline"
                      onClick={() => onShowTicket(false)}
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              ) : (
                <>
                  <p className="help-copy">
                    Propose a review ticket for approval. A proposal alone
                    cannot close this finding.
                  </p>
                  <button
                    className="button button-outline full-width"
                    onClick={onShowTicket}
                  >
                    <Plus size={14} />
                    Propose remediation ticket
                  </button>
                </>
              )
            ) : (
              <span className="role-hint">
                A confirmed applicable decision is required.
              </span>
            )}
          </div>
        )}
        {evidence && (
          <div className="detail-section">
            <h4>EVIDENCE RECORD</h4>
            <div className="evidence-record">
              <div className="evidence-record-icon">
                <FileCheck2 size={16} />
              </div>
              <div>
                <strong>{evidence.label}</strong>
                <span>{evidence.reference}</span>
                <small>
                  SHA-256 {evidence.sha256 || "not supplied"} · Recorded by{" "}
                  {evidence.recorded_by}
                </small>
              </div>
            </div>
            {finding.status === "mitigated_pending_verification" &&
              (allowedApprove ? (
                <>
                  <textarea
                    className="compact-textarea"
                    value={reviewNote}
                    onChange={(e) => setReviewNote(e.target.value)}
                  />
                  <button
                    className="button button-primary full-width"
                    onClick={() => onVerify(evidence)}
                  >
                    <BadgeCheck size={14} />
                    Verify evidence and close
                  </button>
                </>
              ) : (
                <span className="role-hint">
                  <LockKeyhole size={13} />
                  Approver verification required
                </span>
              ))}
          </div>
        )}
        {allowedReview && (
          <div className="detail-section ai-section">
            <div className="ai-head">
              <div className="ai-mark">
                <Sparkles size={14} />
              </div>
              <div>
                <h4>LOCAL AI ASSIST</h4>
                <small>
                  Schema-checked · source quotes required · no verdict authority
                </small>
              </div>
            </div>
            <button className="text-button" onClick={onAI} disabled={!!busy}>
              Draft advisory extraction <ChevronRight size={13} />
            </button>
            {aiResult && (
              <pre className="ai-output">
                {JSON.stringify(aiResult, null, 2)}
              </pre>
            )}
          </div>
        )}
      </div>
      <div className="detail-footer">
        <span>
          <LockKeyhole size={12} />
          Decision actions are audit logged
        </span>
        <span>OTProof</span>
      </div>
    </aside>
  );
}

function InventoryView({
  assets,
  total,
  search,
  setSearch,
  onUpload,
  onAnalyze,
  busy,
}: AnyRecord) {
  const [tab, setTab] = useState("all");
  const filtered = assets.filter((a: AnyRecord) =>
    [a.asset_id, a.vendor, a.product, a.site]
      .join(" ")
      .toLowerCase()
      .includes(search.toLowerCase()),
  );
  return (
    <>
      <div className="page-heading">
        <div>
          <div className="eyebrow">ASSET REGISTER</div>
          <h1>Asset inventory</h1>
          <p>
            Fictional Cedar Valley Water Utility · last verified dates remain
            visible for review.
          </p>
        </div>
        <div className="heading-actions">
          <label className="button button-outline upload-button">
            <Upload size={15} />
            Import CSV / Excel
            <input
              type="file"
              accept=".csv,.xlsx,.xlsm"
              onChange={(e) => onUpload(e.target.files?.[0])}
              hidden
            />
          </label>
          <button
            className="button button-primary"
            onClick={onAnalyze}
            disabled={!!busy}
          >
            <RefreshCw size={15} />
            Run analysis
          </button>
        </div>
      </div>
      <div className="inventory-summary">
        <div>
          <strong>{total}</strong>
          <span>assets in scope</span>
        </div>
        <div>
          <strong>
            {
              assets.filter(
                (a: AnyRecord) =>
                  a.last_verified &&
                  (Date.now() - Date.parse(a.last_verified)) / 86400000 > 180,
              ).length
            }
          </strong>
          <span>records over 180 days old</span>
        </div>
        <div>
          <strong>
            {assets.filter((a: AnyRecord) => !a.firmware_version).length}
          </strong>
          <span>missing software version</span>
        </div>
        <div className="summary-note">
          <ShieldCheck size={16} />
          <span>
            Import validates required identifiers and rejects duplicate IDs in
            the same file.
          </span>
        </div>
      </div>
      <div className="card inventory-card">
        <div className="inventory-tools">
          <div className="filter-tabs">
            <button
              className={tab === "all" ? "selected" : ""}
              onClick={() => setTab("all")}
            >
              All assets <b>{total}</b>
            </button>
            <button
              className={tab === "critical" ? "selected" : ""}
              onClick={() => setTab("critical")}
            >
              Critical / high{" "}
              <b>
                {
                  assets.filter((x: AnyRecord) =>
                    ["Critical", "High"].includes(x.criticality),
                  ).length
                }
              </b>
            </button>
          </div>
          <div className="search-box">
            <Search size={15} />
            <input
              placeholder="Search assets"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
            <Filter size={14} />
          </div>
        </div>
        <div className="table-scroll">
          <table className="inventory-table">
            <thead>
              <tr>
                <th>ASSET ID</th>
                <th>VENDOR / PRODUCT</th>
                <th>MODEL</th>
                <th>VERSION</th>
                <th>TYPE</th>
                <th>SITE</th>
                <th>CRITICALITY</th>
                <th>VERIFIED</th>
              </tr>
            </thead>
            <tbody>
              {filtered
                .filter(
                  (x: AnyRecord) =>
                    tab !== "critical" ||
                    ["Critical", "High"].includes(x.criticality),
                )
                .map((a: AnyRecord) => (
                  <tr key={a.asset_id}>
                    <td>
                      <strong>{a.asset_id}</strong>
                    </td>
                    <td>
                      <strong>{a.vendor || "Not recorded"}</strong>
                      <small>{a.product || "Product missing"}</small>
                    </td>
                    <td>{a.model || "—"}</td>
                    <td>
                      {a.firmware_version || (
                        <span className="missing-tag">Missing</span>
                      )}
                    </td>
                    <td>{a.equipment_type}</td>
                    <td>{a.site}</td>
                    <td>
                      <span
                        className={`criticality ${a.criticality.toLowerCase()}`}
                      >
                        <i />
                        {a.criticality}
                      </span>
                    </td>
                    <td>{a.last_verified || "—"}</td>
                  </tr>
                ))}
            </tbody>
          </table>
        </div>
        <div className="table-foot">
          <span>
            Showing {filtered.length} of {total} fictional assets
          </span>
          <span>Inventory remains local to this demo</span>
        </div>
      </div>
    </>
  );
}

function AdvisoriesView({
  advisories,
  onIngest,
  onNvd,
  onVendor,
  busy,
}: AnyRecord) {
  const [cve, setCve] = useState("CVE-2024-7513");
  const [url, setUrl] = useState("");
  return (
    <>
      <div className="page-heading">
        <div>
          <div className="eyebrow">PUBLIC SECURITY INTELLIGENCE</div>
          <h1>Advisory sources</h1>
          <p>
            Official source records with publication dates, source links, and
            cached retrieval metadata.
          </p>
        </div>
        <button
          className="button button-primary"
          onClick={() => onIngest("cisa-ics")}
          disabled={!!busy}
        >
          <RefreshCw size={15} />
          Sync CISA ICS
        </button>
      </div>
      <div className="source-control-grid">
        <div className="card source-control">
          <div className="source-control-icon cisa-mark">C</div>
          <div>
            <h3>CISA ICS Advisories</h3>
            <p>
              Official ICS advisory RSS feed and source pages. Results are
              cached and retain source publication dates.
            </p>
            <a
              href="https://www.cisa.gov/cybersecurity-advisories/ics-advisories.xml"
              target="_blank"
              rel="noreferrer"
            >
              Open public feed <Link2 size={13} />
            </a>
            <button
              className="button button-outline"
              onClick={() => onIngest("cisa-ics")}
              disabled={!!busy}
            >
              <RefreshCw size={14} />
              Ingest latest advisories
            </button>
          </div>
        </div>
        <div className="card source-control">
          <div className="source-control-icon kev">K</div>
          <div>
            <h3>Known Exploited Vulnerabilities</h3>
            <p>
              CISA JSON catalog is imported as a priority signal. Version
              applicability stays manual when the catalog lacks affected ranges.
            </p>
            <a
              href="https://www.cisa.gov/known-exploited-vulnerabilities-catalog"
              target="_blank"
              rel="noreferrer"
            >
              Open CISA KEV catalog <Link2 size={13} />
            </a>
            <button
              className="button button-outline"
              onClick={() => onIngest("cisa-kev")}
              disabled={!!busy}
            >
              <RefreshCw size={14} />
              Import catalog
            </button>
          </div>
        </div>
        <div className="card source-control nvd-control">
          <div className="source-control-icon nvd">N</div>
          <div>
            <h3>NVD CVE record lookup</h3>
            <p>
              Look up one CVE via NVD's documented public 2.0 API. Requests are
              cached and rate limited.
            </p>
            <a
              href="https://nvd.nist.gov/developers/vulnerabilities"
              target="_blank"
              rel="noreferrer"
            >
              API documentation <Link2 size={13} />
            </a>
            <div className="inline-input">
              <input value={cve} onChange={(e) => setCve(e.target.value)} />
              <button
                className="button button-outline"
                onClick={() => onNvd(cve)}
                disabled={!!busy}
              >
                Import CVE
              </button>
            </div>
          </div>
        </div>
        <div className="card source-control vendor-control">
          <div className="source-control-icon vendor">V</div>
          <div>
            <h3>Vendor security bulletin</h3>
            <p>
              Fetch supported official Rockwell, Schneider Electric, Siemens, or
              Cisco HTTPS bulletins.
            </p>
            <div className="inline-input">
              <input
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                placeholder="https://vendor.example/security/advisory"
              />
              <button
                className="button button-outline"
                onClick={() => onVendor(url)}
                disabled={!url || !!busy}
              >
                Import URL
              </button>
            </div>
            <small>
              Unsupported or unparseable version statements are retained for
              manual analysis.
            </small>
          </div>
        </div>
      </div>
      <div className="section-title-row">
        <div>
          <div className="eyebrow">NORMALIZED ADVISORIES</div>
          <h2>{advisories.length} loaded records</h2>
        </div>
      </div>
      <div className="card advisory-list">
        {advisories.map((a: AnyRecord) => (
          <div className="advisory-row" key={a.id}>
            <div
              className={`source-logo ${a.source === "CISA KEV" ? "k" : "c"}`}
            >
              {a.source === "CISA KEV" ? "K" : a.source === "NVD" ? "N" : "C"}
            </div>
            <div className="advisory-copy">
              <div>
                <strong>{a.title}</strong>
                <span className="advisory-source-tag">{a.source}</span>
              </div>
              <small>
                {a.external_id} {a.cves?.length ? `· ${a.cves.join(", ")}` : ""}{" "}
                · Published {a.published_at || "date not supplied"}
              </small>
              <p>
                {a.vendor} · {a.product} ·{" "}
                {a.affected_products
                  ?.flatMap((p: AnyRecord) =>
                    p.constraints?.map((c: AnyRecord) => c.raw),
                  )
                  .join(" / ") || "No published version range in this source"}
              </p>
            </div>
            <a
              className="advisory-link"
              href={a.source_url}
              target="_blank"
              rel="noreferrer"
            >
              View source <Link2 size={14} />
            </a>
          </div>
        ))}
      </div>
    </>
  );
}

function RemediationView({
  tickets,
  findings,
  role,
  onSelectFinding,
  reviewNote,
  setReviewNote,
}: AnyRecord) {
  const selectedTicketFinding = (id: number) =>
    findings.find((f: AnyRecord) => f.id === id);
  return (
    <>
      <div className="page-heading">
        <div>
          <div className="eyebrow">CHANGE AND EVIDENCE CONTROL</div>
          <h1>Remediation assurance</h1>
          <p>
            Ticket proposals require approver action. Evidence is attached to an
            approved ticket and verified separately.
          </p>
        </div>
      </div>
      <div className="remediation-summary">
        <div className="card process-card">
          <div className="process-step">
            <span>01</span>
            <div>
              <strong>Engineering decision</strong>
              <small>
                Reviewer records applicable / not applicable and rationale
              </small>
            </div>
            <CheckCircle2 size={17} />
          </div>
          <div className="process-connector" />
          <div className="process-step">
            <span>02</span>
            <div>
              <strong>Ticket approval</strong>
              <small>
                Approver accepts or rejects the proposed change work
              </small>
            </div>
            <Clock3 size={17} />
          </div>
          <div className="process-connector" />
          <div className="process-step">
            <span>03</span>
            <div>
              <strong>Evidence verification</strong>
              <small>Approver inspects evidence before closure</small>
            </div>
            <LockKeyhole size={17} />
          </div>
        </div>
        <div className="card evidence-metric">
          <div className="metric-icon green">
            <FileCheck2 size={18} />
          </div>
          <span>Evidence coverage</span>
          <strong>
            {findings.length
              ? Math.round(
                  (findings.filter((f: AnyRecord) => f.evidence_records?.length)
                    .length /
                    findings.length) *
                    100,
                )
              : 0}
            %
          </strong>
          <small>Candidate findings with evidence records</small>
          <div className="mini-bar">
            <i
              style={{
                width: `${findings.length ? (findings.filter((f: AnyRecord) => f.evidence_records?.length).length / findings.length) * 100 : 0}%`,
              }}
            />
          </div>
        </div>
      </div>
      <div className="section-title-row">
        <div>
          <div className="eyebrow">REMEDIATION REGISTER</div>
          <h2>{tickets.length} proposed / active tickets</h2>
        </div>
      </div>
      <div className="card remediation-table">
        <div className="table-scroll">
          <table className="findings-table">
            <thead>
              <tr>
                <th>FINDING / ASSET</th>
                <th>PROPOSED ACTION</th>
                <th>ASSIGNED TO</th>
                <th>DUE</th>
                <th>STATUS</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {tickets.map((t: AnyRecord) => (
                <tr key={t.id}>
                  <td>
                    <strong>Ticket #{t.id}</strong>
                    <small>
                      {selectedTicketFinding(t.finding_id)?.asset.asset_id ||
                        `Finding #${t.finding_id}`}
                    </small>
                  </td>
                  <td className="action-cell">{t.proposed_action}</td>
                  <td>{t.assigned_to}</td>
                  <td>{t.due_date || "—"}</td>
                  <td>
                    <span className={`ticket-status ${t.status}`}>
                      {t.status.replaceAll("_", " ")}
                    </span>
                  </td>
                  <td>
                    <button
                      className="table-action"
                      onClick={() =>
                        selectedTicketFinding(t.finding_id) &&
                        onSelectFinding(selectedTicketFinding(t.finding_id))
                      }
                    >
                      Details <ChevronRight size={13} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {tickets.length === 0 && (
            <div className="table-empty">
              <ClipboardCheck size={24} />
              <strong>No remediation tickets yet.</strong>
              <span>
                Confirm applicability, then propose a change review for
                approval.
              </span>
            </div>
          )}
        </div>
      </div>
      {role === "approver" || role === "admin" ? (
        <div className="approver-note">
          <LockKeyhole size={14} />
          <span>
            Approver actions are enabled. Proposals awaiting your review can be
            approved or rejected in the finding detail panel.
          </span>
          <input
            value={reviewNote}
            onChange={(e) => setReviewNote(e.target.value)}
            aria-label="Approval rationale"
          />
        </div>
      ) : (
        <div className="role-hint page-role-hint">
          <LockKeyhole size={14} />
          Switch to Approver role to approve or reject proposed tickets.
        </div>
      )}
    </>
  );
}

function AuditView({ audit }: AnyRecord) {
  return (
    <>
      <div className="page-heading">
        <div>
          <div className="eyebrow">IMMUTABLE ACTION HISTORY</div>
          <h1>Audit trail</h1>
          <p>
            Records source ingestion, analysis runs, decisions, ticket
            approvals, evidence attachment, and verification events.
          </p>
        </div>
        <span className="audit-seal">
          <ShieldCheck size={16} />
          AUDIT LOG ENABLED
        </span>
      </div>
      <div className="card audit-card">
        <div className="audit-summary">
          <div>
            <strong>{audit.length}</strong>
            <span>events recorded</span>
          </div>
          <div>
            <strong>Every change</strong>
            <span>actor and role included</span>
          </div>
          <div>
            <strong>Source linked</strong>
            <span>advisory and evidence references retained</span>
          </div>
        </div>
        <div className="audit-list">
          {audit.length ? (
            audit.map((e: AnyRecord) => (
              <div className="audit-event" key={e.id}>
                <div className="audit-event-icon">
                  <Activity size={15} />
                </div>
                <div className="audit-event-main">
                  <strong>{e.action.replaceAll(".", " ")}</strong>
                  <span>
                    {e.entity_type} · {e.entity_id} · {e.actor}
                  </span>
                  <small>{JSON.stringify(e.details)}</small>
                </div>
                <time>{e.created_at?.slice(0, 16).replace("T", " ")}</time>
              </div>
            ))
          ) : (
            <div className="table-empty">
              <ListChecks size={23} />
              <strong>No events recorded yet.</strong>
              <span>
                Start with an analysis run, then review candidate findings.
              </span>
            </div>
          )}
        </div>
      </div>
    </>
  );
}

export default App;
