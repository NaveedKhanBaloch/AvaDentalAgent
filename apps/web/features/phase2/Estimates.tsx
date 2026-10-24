"use client";
import { useCallback, useEffect, useState } from "react";
import { request, input, button, panel } from "./api";
type Line = {
  service_id: string;
  quantity: string;
  unit_price: string;
  discount_percent: string;
  tax_label: string;
};
type Estimate = {
  id: string;
  number: string;
  patient_id: string;
  patient_name?: string;
  status: string;
  revision: number;
  current_version: number;
  total?: string;
  currency?: string;
  created_at: string;
};
type Detail = Estimate & {
  version: number;
  version_page: number;
  history_page: number;
  version_total: number;
  history_total: number;
  document: {
    status: string;
    total: string;
    subtotal: string;
    tax: string;
    discount: string;
    currency: string;
    issue_date: string;
    valid_until: string | null;
    terms: string;
  };
  items: (Line & { description: string; total: string })[];
  versions: {
    version: number;
    status: string;
    total: string;
    reason: string | null;
  }[];
  history: {
    id: string;
    status: string;
    created_at: string;
    reason: string | null;
  }[];
  acknowledgement: {
    decision: string;
    acknowledged_by_name: string;
    method: string;
  } | null;
};
const blankLine: Line = {
  service_id: "",
  quantity: "1",
  unit_price: "",
  discount_percent: "0",
  tax_label: "none",
};
export default function Estimates() {
  const [items, setItems] = useState<Estimate[]>([]),
    [page, setPage] = useState(1),
    [total, setTotal] = useState(0),
    [search, setSearch] = useState(""),
    [status, setStatus] = useState(""),
    [sort, setSort] = useState("created_at"),
    [from, setFrom] = useState(""),
    [to, setTo] = useState("");
  const [selected, setSelected] = useState<Detail | null>(null),
    [mode, setMode] = useState<"new" | "edit" | "revision" | null>(null),
    [patientId, setPatientId] = useState(""),
    [patients, setPatients] = useState<
      { id: string; first_name: string; last_name: string }[]
    >([]),
    [patientSearch, setPatientSearch] = useState(""),
    [services, setServices] = useState<
      { id: string; name: string; indicative_price: number }[]
    >([]),
    [lines, setLines] = useState<Line[]>([{ ...blankLine }]),
    [issueDate, setIssueDate] = useState(new Date().toISOString().slice(0, 10)),
    [expiry, setExpiry] = useState(""),
    [reason, setReason] = useState("");
  const [permissions, setPermissions] = useState<string[]>([]),
    [policy, setPolicy] = useState<{
      configured?: boolean;
      currency: string;
      minor_units?: number;
      tax_rates?: Record<string, string>;
      max_discount_percent?: string;
      terms?: string;
      validity_days?: number;
      revision?: number;
    } | null>(null),
    [showPolicy, setShowPolicy] = useState(false),
    [policyForm, setPolicyForm] = useState({
      currency: "",
      minor_units: "2",
      tax_rates: '{"none":"0"}',
      max_discount_percent: "0",
      terms: "",
      validity_days: "",
      approved: false,
    });
  const [preview, setPreview] = useState<{
      total: string;
      subtotal: string;
      tax: string;
      discount: string;
    } | null>(null),
    [error, setError] = useState(""),
    [loading, setLoading] = useState(false);
  const load = useCallback(async () => {
    setLoading(true);
    try {
      const q = new URLSearchParams({
        page: String(page),
        page_size: "10",
        search,
        status,
        sort,
      });
      if (from) q.set("created_from", from);
      if (to) q.set("created_to", to);
      const d = await request("/estimates?" + q);
      setItems(d.items);
      setTotal(d.total);
      setError("");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, [page, search, status, sort, from, to]);
  const loadPolicy = useCallback(async () => {
    try {
      const p = await request("/estimates/policy");
      setPolicy(p);
      setPolicyForm({
        currency: p.currency,
        minor_units: String(p.minor_units ?? 2),
        tax_rates: JSON.stringify(p.tax_rates ?? { none: "0" }),
        max_discount_percent: String(p.max_discount_percent ?? 0),
        terms: p.terms ?? "",
        validity_days: p.validity_days ? String(p.validity_days) : "",
        approved: false,
      });
    } catch (e) {
      setError((e as Error).message);
    }
  }, []);
  useEffect(() => {
    const q = new URLSearchParams(window.location.search);
    setStatus(q.get("status") ?? "");
    const id = q.get("estimate");
    if (id) void open(id);
  }, []);
  useEffect(() => {
    void load();
  }, [load]);
  useEffect(() => {
    void loadPolicy();
    request("/operations/capabilities")
      .then((d) => setPermissions(d.permissions))
      .catch((e) => setError(e.message));
    request("/services")
      .then((d) => setServices(d.items))
      .catch((e) => setError(e.message));
  }, [loadPolicy]);
  useEffect(() => {
    request(
      "/patients?status=active&page_size=100&search=" +
        encodeURIComponent(patientSearch),
    )
      .then((d) => setPatients(d.items))
      .catch((e) => setError(e.message));
  }, [patientSearch]);
  async function open(
    id: string,
    version?: number,
    versionPage = 1,
    historyPage = 1,
  ) {
    setLoading(true);
    try {
      setSelected(
        await request(
          "/estimates/" +
            id +
            `?version_page=${versionPage}&history_page=${historyPage}` +
            (version ? "&version=" + version : ""),
        ),
      );
      setMode(null);
      setError("");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }
  function edit(next: "new" | "edit" | "revision") {
    setMode(next);
    setPreview(null);
    setReason("");
    if (next === "new") {
      setPatientId("");
      setLines([
        {
          ...blankLine,
          tax_label: Object.keys(policy?.tax_rates ?? {})[0] ?? "none",
        },
      ]);
      setIssueDate(new Date().toISOString().slice(0, 10));
      setExpiry("");
    } else if (selected) {
      setPatientId(selected.patient_id);
      setLines(
        selected.items.map((r) => ({
          service_id: r.service_id,
          quantity: r.quantity,
          unit_price: r.unit_price,
          discount_percent: r.discount_percent,
          tax_label: r.tax_label,
        })),
      );
      setIssueDate(selected.document.issue_date);
      setExpiry(selected.document.valid_until ?? "");
    }
  }
  function body() {
    return {
      patient_id: patientId,
      issue_date: issueDate,
      valid_until: expiry || null,
      items: lines.map((l) => ({
        ...l,
        unit_price: l.unit_price === "" ? null : l.unit_price,
      })),
      ...(mode !== "new" && selected
        ? { expected_revision: selected.revision }
        : {}),
      ...(mode === "revision" ? { revision_reason: reason } : {}),
    };
  }
  async function save(e: React.FormEvent) {
    e.preventDefault();
    try {
      const path =
        mode === "new"
          ? "/estimates"
          : mode === "revision"
            ? `/estimates/${selected?.id}/revisions`
            : `/estimates/${selected?.id}`;
      setSelected(
        await request(path, mode === "edit" ? "PATCH" : "POST", body()),
      );
      setMode(null);
      setPreview(null);
      await load();
    } catch (e) {
      setError((e as Error).message);
    }
  }
  async function action(target: string) {
    if (!selected) return;
    let method = "",
      name = "",
      note = "";
    if (target === "sent") {
      method =
        prompt(
          "How was this version delivered outside the application? No message will be sent.",
        ) ?? "";
      if (!method) return;
    } else if (["accepted", "declined"].includes(target)) {
      name =
        prompt(
          "Patient or representative name for this version-specific acknowledgement:",
        ) ?? "";
      if (!name) return;
      method =
        prompt(
          "How was the acknowledgement obtained? This records an administrative acknowledgement, not an electronic signature.",
        ) ?? "";
      if (!method) return;
    } else if (target === "cancelled") {
      note = prompt("Cancellation reason:") ?? "";
      if (!note) return;
    }
    if (
      !confirm(
        `Record ${target} for ${selected.number} version ${selected.version}?`,
      )
    )
      return;
    try {
      setSelected(
        await request(`/estimates/${selected.id}/status`, "POST", {
          expected_revision: selected.revision,
          version: selected.version,
          status: target,
          confirmed: true,
          method: method || null,
          acknowledged_by_name: name || null,
          reason: note || null,
        }),
      );
      await load();
    } catch (e) {
      setError((e as Error).message);
    }
  }
  async function pdf() {
    if (!selected) return;
    try {
      const blob = await request(
        `/estimates/${selected.id}/pdf?version=${selected.version}`,
      );
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${selected.number}-v${selected.version}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      setError((e as Error).message);
    }
  }
  return (
    <section className="space-y-4">
      <header className="flex flex-wrap justify-between gap-3">
        <div>
          <h2 className="text-2xl font-semibold">Treatment estimates</h2>
          <p>Versioned quotations and recorded patient acknowledgements</p>
        </div>
        <div className="flex gap-2">
          {permissions.includes("estimate_admin") && (
            <button
              className={button}
              onClick={() => setShowPolicy(!showPolicy)}
            >
              Clinic estimate policy
            </button>
          )}
          {permissions.includes("estimate_write") && (
            <button
              disabled={!policy || policy.configured === false}
              className={button}
              onClick={() => edit("new")}
            >
              New estimate
            </button>
          )}
        </div>
      </header>
      {error && (
        <p role="alert" className="rounded-xl bg-rose-50 p-3 text-rose-800">
          {error}
        </p>
      )}
      {loading && <p role="status">Loading estimates…</p>}
      {policy?.configured === false && (
        <p className={panel}>
          An authorized owner must configure the clinic currency, taxes,
          discounts and terms before estimates can be created.
        </p>
      )}
      {showPolicy && (
        <form
          aria-label="Estimate policy"
          className={panel}
          onSubmit={async (e) => {
            e.preventDefault();
            try {
              await request("/estimates/policy", "PUT", {
                currency: policyForm.currency,
                minor_units: Number(policyForm.minor_units),
                tax_rates: JSON.parse(policyForm.tax_rates),
                max_discount_percent: policyForm.max_discount_percent,
                terms: policyForm.terms,
                validity_days: policyForm.validity_days
                  ? Number(policyForm.validity_days)
                  : null,
                clinically_approved: policyForm.approved,
                expected_revision: policy?.revision ?? null,
              });
              await loadPolicy();
              setShowPolicy(false);
            } catch (e) {
              setError((e as Error).message);
            }
          }}
        >
          <h3 className="font-semibold">Owner-approved estimate settings</h3>
          <div className="grid gap-3 md:grid-cols-2">
            {(
              [
                "currency",
                "minor_units",
                "max_discount_percent",
                "validity_days",
              ] as const
            ).map((k) => (
              <label key={k}>
                {k.replaceAll("_", " ")}
                <input
                  className={input}
                  required={k !== "validity_days"}
                  value={policyForm[k]}
                  onChange={(e) =>
                    setPolicyForm({ ...policyForm, [k]: e.target.value })
                  }
                />
              </label>
            ))}
            <label>
              Approved tax labels and rates (JSON)
              <textarea
                className={input}
                value={policyForm.tax_rates}
                onChange={(e) =>
                  setPolicyForm({ ...policyForm, tax_rates: e.target.value })
                }
              />
            </label>
            <label>
              Clinic terms
              <textarea
                className={input}
                value={policyForm.terms}
                onChange={(e) =>
                  setPolicyForm({ ...policyForm, terms: e.target.value })
                }
              />
            </label>
            <label>
              <input
                type="checkbox"
                required
                checked={policyForm.approved}
                onChange={(e) =>
                  setPolicyForm({ ...policyForm, approved: e.target.checked })
                }
              />{" "}
              I confirm these settings are approved by this clinic.
            </label>
          </div>
          <button className={button}>Save approved policy</button>
        </form>
      )}
      {mode && (
        <form className={panel} aria-label="Estimate form" onSubmit={save}>
          <h3 className="text-lg font-semibold">
            {mode === "new"
              ? "New estimate"
              : mode === "edit"
                ? "Edit draft"
                : "Create revision"}
          </h3>
          <div className="grid gap-3 md:grid-cols-2">
            <label>
              Find patient
              <input
                className={input}
                value={patientSearch}
                onChange={(e) => setPatientSearch(e.target.value)}
              />
            </label>
            <label>
              Patient
              <select
                className={input}
                required
                disabled={mode !== "new"}
                value={patientId}
                onChange={(e) => setPatientId(e.target.value)}
              >
                <option value="">Select patient</option>
                {patients.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.first_name} {p.last_name}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Issue date
              <input
                type="date"
                className={input}
                required
                value={issueDate}
                onChange={(e) => setIssueDate(e.target.value)}
              />
            </label>
            <label>
              Valid until
              <input
                type="date"
                className={input}
                value={expiry}
                onChange={(e) => setExpiry(e.target.value)}
              />
            </label>
            {mode === "revision" && (
              <label>
                Revision reason
                <input
                  className={input}
                  required
                  value={reason}
                  onChange={(e) => setReason(e.target.value)}
                />
              </label>
            )}
          </div>
          <div className="mt-3 space-y-3">
            {lines.map((line, index) => (
              <fieldset className="rounded-xl border p-3" key={index}>
                <legend>Treatment {index + 1}</legend>
                <div className="grid gap-2 sm:grid-cols-3">
                  <label>
                    Treatment
                    <select
                      className={input}
                      required
                      value={line.service_id}
                      onChange={(e) => {
                        setLines(
                          lines.map((r, i) =>
                            i === index
                              ? { ...r, service_id: e.target.value }
                              : r,
                          ),
                        );
                        setPreview(null);
                      }}
                    >
                      <option value="">Select treatment</option>
                      {services.map((s) => (
                        <option key={s.id} value={s.id}>
                          {s.name}
                        </option>
                      ))}
                    </select>
                  </label>
                  {(
                    ["quantity", "unit_price", "discount_percent"] as const
                  ).map((k) => (
                    <label key={k}>
                      {k === "unit_price"
                        ? "Unit price (blank uses catalog)"
                        : k.replaceAll("_", " ")}
                      <input
                        className={input}
                        type="number"
                        step={k === "quantity" ? "0.001" : "0.0001"}
                        min="0"
                        required={k !== "unit_price"}
                        value={line[k]}
                        onChange={(e) => {
                          setLines(
                            lines.map((r, i) =>
                              i === index ? { ...r, [k]: e.target.value } : r,
                            ),
                          );
                          setPreview(null);
                        }}
                      />
                    </label>
                  ))}
                  <label>
                    Tax treatment
                    <select
                      className={input}
                      value={line.tax_label}
                      onChange={(e) => {
                        setLines(
                          lines.map((r, i) =>
                            i === index
                              ? { ...r, tax_label: e.target.value }
                              : r,
                          ),
                        );
                        setPreview(null);
                      }}
                    >
                      {Object.keys(policy?.tax_rates ?? {}).map((k) => (
                        <option key={k} value={k}>
                          {k} ({policy?.tax_rates?.[k]}%)
                        </option>
                      ))}
                    </select>
                  </label>
                  <button
                    type="button"
                    disabled={lines.length === 1}
                    onClick={() => {
                      setLines(lines.filter((_, i) => i !== index));
                      setPreview(null);
                    }}
                  >
                    Remove treatment
                  </button>
                </div>
              </fieldset>
            ))}
          </div>
          <div className="my-3 flex flex-wrap gap-3">
            <button
              type="button"
              onClick={() => {
                setLines([
                  ...lines,
                  {
                    ...blankLine,
                    tax_label:
                      Object.keys(policy?.tax_rates ?? {})[0] ?? "none",
                  },
                ]);
                setPreview(null);
              }}
            >
              Add treatment
            </button>
            <button
              type="button"
              className={button}
              onClick={async () => {
                try {
                  setPreview(
                    await request("/estimates/preview", "POST", body()),
                  );
                } catch (e) {
                  setError((e as Error).message);
                }
              }}
            >
              Review backend totals
            </button>
            <button className={button}>Save draft</button>
            <button type="button" onClick={() => setMode(null)}>
              Cancel editing
            </button>
          </div>
          {preview && (
            <p role="status">
              Subtotal {preview.subtotal} · Discount {preview.discount} · Tax{" "}
              {preview.tax} · Total {preview.total} {policy?.currency}
            </p>
          )}
        </form>
      )}
      <div className={panel}>
        <div className="grid gap-2 sm:grid-cols-3">
          <label>
            Search estimates
            <input
              className={input}
              value={search}
              onChange={(e) => {
                setSearch(e.target.value);
                setPage(1);
              }}
            />
          </label>
          <label>
            Status
            <select
              className={input}
              value={status}
              onChange={(e) => {
                setStatus(e.target.value);
                setPage(1);
              }}
            >
              <option value="">All statuses</option>
              {[
                "draft",
                "sent",
                "accepted",
                "declined",
                "expired",
                "cancelled",
              ].map((s) => (
                <option key={s}>{s}</option>
              ))}
            </select>
          </label>
          <label>
            Sort
            <select
              className={input}
              value={sort}
              onChange={(e) => {
                setSort(e.target.value);
                setPage(1);
              }}
            >
              {["created_at", "number", "total"].map((s) => (
                <option key={s}>{s}</option>
              ))}
            </select>
          </label>
          <label>
            Created from
            <input
              type="date"
              className={input}
              value={from}
              onChange={(e) => {
                setFrom(e.target.value);
                setPage(1);
              }}
            />
          </label>
          <label>
            Created to
            <input
              type="date"
              className={input}
              value={to}
              onChange={(e) => {
                setTo(e.target.value);
                setPage(1);
              }}
            />
          </label>
        </div>
        <ul className="divide-y">
          {items.map((e) => (
            <li
              className="flex flex-wrap justify-between gap-2 py-3"
              key={e.id}
            >
              <button
                className="font-semibold text-cyan-700"
                onClick={() => open(e.id)}
              >
                {e.number} · v{e.current_version}
              </button>
              <span>
                {e.patient_name} · {e.status} · {e.total} {e.currency}
              </span>
            </li>
          ))}
        </ul>
        {!items.length && !loading && <p>No estimates match these filters.</p>}
        <div className="flex gap-3">
          <button disabled={page === 1} onClick={() => setPage(page - 1)}>
            Previous estimates
          </button>
          <span>
            {total} estimates · page {page}
          </span>
          <button
            disabled={page * 10 >= total}
            onClick={() => setPage(page + 1)}
          >
            Next estimates
          </button>
        </div>
      </div>
      {selected && !mode && (
        <article className={panel} aria-label="Estimate detail">
          <h3 className="text-xl font-semibold">
            {selected.number} · version {selected.version} ·{" "}
            {selected.document.status}
          </h3>
          <a
            className="text-cyan-700"
            href={`/dashboard?section=patients&patient=${selected.patient_id}`}
          >
            Open patient profile
          </a>
          <p>
            Issued {selected.document.issue_date} · Valid until{" "}
            {selected.document.valid_until || "Not specified"}
          </p>
          <div className="overflow-x-auto">
            <table className="my-3 w-full text-left text-sm">
              <thead>
                <tr>
                  {[
                    "Treatment",
                    "Quantity",
                    "Unit price",
                    "Discount %",
                    "Tax",
                    "Total",
                  ].map((h) => (
                    <th className="p-2" key={h}>
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {selected.items.map((i, n) => (
                  <tr className="border-t" key={n}>
                    <td className="p-2">{i.description}</td>
                    <td>{i.quantity}</td>
                    <td>{i.unit_price}</td>
                    <td>{i.discount_percent}</td>
                    <td>{i.tax_label}</td>
                    <td>{i.total}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="font-semibold">
            Subtotal {selected.document.subtotal} · Discount{" "}
            {selected.document.discount} · Tax {selected.document.tax} · Total{" "}
            {selected.document.total} {selected.document.currency}
          </p>
          <p className="whitespace-pre-wrap">{selected.document.terms}</p>
          <div className="my-3 flex flex-wrap gap-2">
            <button className={button} onClick={pdf}>
              Download PDF
            </button>
            {selected.version === selected.current_version && (
              <>
                {permissions.includes("estimate_write") &&
                  selected.status === "draft" && (
                    <>
                      <button className={button} onClick={() => edit("edit")}>
                        Edit draft
                      </button>
                      <button className={button} onClick={() => action("sent")}>
                        Record delivery
                      </button>
                    </>
                  )}
                {permissions.includes("estimate_approve") &&
                  selected.status === "sent" && (
                    <>
                      <button
                        className={button}
                        onClick={() => action("accepted")}
                      >
                        Record acceptance
                      </button>
                      <button
                        className={button}
                        onClick={() => action("declined")}
                      >
                        Record decline
                      </button>
                    </>
                  )}
                {permissions.includes("estimate_write") &&
                  ["draft", "sent"].includes(selected.status) && (
                    <button onClick={() => action("cancelled")}>
                      Cancel estimate
                    </button>
                  )}
                {permissions.includes("estimate_write") &&
                  selected.status === "sent" && (
                    <button onClick={() => action("expired")}>
                      Record expiry
                    </button>
                  )}
                {permissions.includes("estimate_admin") &&
                  selected.status !== "draft" && (
                    <button className={button} onClick={() => edit("revision")}>
                      Create revision
                    </button>
                  )}
              </>
            )}
            {permissions.includes("estimate_write") && (
              <button
                onClick={async () => {
                  if (
                    !confirm(
                      "Duplicate this estimate into a new draft using current clinic policy?",
                    )
                  )
                    return;
                  try {
                    setSelected(
                      await request(
                        `/estimates/${selected.id}/duplicate`,
                        "POST",
                      ),
                    );
                    await load();
                  } catch (e) {
                    setError((e as Error).message);
                  }
                }}
              >
                Duplicate to draft
              </button>
            )}
          </div>
          {selected.acknowledgement && (
            <p>
              Administrative acknowledgement:{" "}
              {selected.acknowledgement.decision} ·{" "}
              {selected.acknowledgement.acknowledged_by_name} ·{" "}
              {selected.acknowledgement.method}
            </p>
          )}
          <h4 className="font-semibold">Version history</h4>
          <ul>
            {selected.versions.map((v) => (
              <li key={v.version}>
                <button
                  className="text-cyan-700"
                  onClick={() => open(selected.id, v.version)}
                >
                  View version {v.version}
                </button>{" "}
                · {v.status} · {v.total} · {v.reason}
              </li>
            ))}
          </ul>
          <div className="flex gap-3">
            <button
              disabled={selected.version_page === 1}
              onClick={() =>
                open(
                  selected.id,
                  selected.version,
                  selected.version_page - 1,
                  selected.history_page,
                )
              }
            >
              Previous versions
            </button>
            <button
              disabled={selected.version_page * 25 >= selected.version_total}
              onClick={() =>
                open(
                  selected.id,
                  selected.version,
                  selected.version_page + 1,
                  selected.history_page,
                )
              }
            >
              More versions
            </button>
          </div>
          <h4 className="mt-3 font-semibold">Status history</h4>
          <ul>
            {selected.history.map((h) => (
              <li key={h.id}>
                {h.status} · {new Date(h.created_at).toLocaleString()} ·{" "}
                {h.reason}
              </li>
            ))}
          </ul>
          <div className="flex gap-3">
            <button
              disabled={selected.history_page === 1}
              onClick={() =>
                open(
                  selected.id,
                  selected.version,
                  selected.version_page,
                  selected.history_page - 1,
                )
              }
            >
              Previous status events
            </button>
            <button
              disabled={selected.history_page * 25 >= selected.history_total}
              onClick={() =>
                open(
                  selected.id,
                  selected.version,
                  selected.version_page,
                  selected.history_page + 1,
                )
              }
            >
              More status events
            </button>
          </div>
        </article>
      )}
    </section>
  );
}
