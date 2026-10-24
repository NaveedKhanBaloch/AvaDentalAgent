"use client";
import { useCallback, useEffect, useState } from "react";
import { request, input, button, panel } from "./api";
type Patient = {
  id: string;
  first_name: string;
  last_name: string;
  phone: string | null;
  email: string | null;
  date_of_birth: string | null;
  preferred_contact_method: string;
  notes: string | null;
  status: string;
  do_not_contact: boolean;
  email_consent: boolean;
  sms_consent: boolean;
  revision: number;
  created_at: string;
  last_appointment?: string;
  next_appointment?: string;
  open_followups?: number;
};
type RecordRow = { [key: string]: string | number | null };
const blank = {
  first_name: "",
  last_name: "",
  phone: "",
  email: "",
  date_of_birth: "",
  preferred_contact_method: "phone",
  notes: "",
  do_not_contact: false,
  email_consent: false,
  sms_consent: false,
};
export default function Patients() {
  const [items, setItems] = useState<Patient[]>([]),
    [total, setTotal] = useState(0),
    [page, setPage] = useState(1),
    [search, setSearch] = useState(""),
    [status, setStatus] = useState("active"),
    [sort, setSort] = useState("created_at");
  const [patient, setPatient] = useState<Patient | null>(null),
    [tab, setTab] = useState("Overview"),
    [rows, setRows] = useState<RecordRow[]>([]),
    [relatedPage, setRelatedPage] = useState(1),
    [relatedTotal, setRelatedTotal] = useState(0);
  const [permissions, setPermissions] = useState<string[]>([]),
    [error, setError] = useState(""),
    [loading, setLoading] = useState(false),
    [editing, setEditing] = useState(false),
    [creating, setCreating] = useState(false),
    [form, setForm] = useState(blank);
  const [insurance, setInsurance] = useState({
    carrier_name: "",
    policy_number: "",
    status: "pending",
  });
  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await request(
        `/patients?search=${encodeURIComponent(search)}&status=${status}&sort=${sort}&page=${page}&page_size=10`,
      );
      setItems(data.items);
      setTotal(data.total);
      setError("");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, [search, status, sort, page]);
  useEffect(() => {
    void load();
  }, [load]);
  useEffect(() => {
    request("/operations/capabilities")
      .then((d) => setPermissions(d.permissions))
      .catch((e) => setError(e.message));
    const id = new URLSearchParams(window.location.search).get("patient");
    if (id)
      request(`/patients/${id}/profile`)
        .then(setPatient)
        .catch((e) => setError(e.message));
  }, []);
  const open = async (id: string) => {
    try {
      setPatient(await request(`/patients/${id}/profile`));
      setTab("Overview");
      setRelatedPage(1);
      const url = new URL(window.location.href);
      url.searchParams.set("patient", id);
      url.searchParams.set("section", "patients");
      window.history.replaceState(null, "", url);
    } catch (e) {
      setError((e as Error).message);
    }
  };
  useEffect(() => {
    if (!patient || tab === "Overview") return;
    setLoading(true);
    setRows([]);
    const path =
      tab === "Estimates"
        ? `/estimates?patient_id=${patient.id}`
        : `/patients/${patient.id}/${tab.toLowerCase()}`;
    request(
      path +
        `${path.includes("?") ? "&" : "?"}page=${relatedPage}&page_size=10`,
    )
      .then((d) => {
        setRows(d.items ?? []);
        setRelatedTotal(d.total ?? d.items?.length ?? 0);
        setError("");
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [patient, tab, relatedPage]);
  async function save(e: React.FormEvent) {
    e.preventDefault();
    try {
      const body = {
        ...form,
        date_of_birth: form.date_of_birth || null,
        ...(!creating && patient
          ? { expected_revision: patient.revision }
          : {}),
      };
      const p = await request(
        creating ? "/patients" : `/patients/${patient?.id}`,
        creating ? "POST" : "PATCH",
        body,
      );
      setEditing(false);
      setCreating(false);
      setPatient(p);
      await load();
    } catch (e) {
      setError((e as Error).message);
    }
  }
  async function archive() {
    if (
      !patient ||
      !confirm(
        `${patient.status === "active" ? "Archive" : "Restore"} this patient? Existing records will be retained.`,
      )
    )
      return;
    try {
      setPatient(
        await request(
          `/patients/${patient.id}/${patient.status === "active" ? "archive" : "restore"}`,
          "POST",
          { confirmed: true, expected_revision: patient.revision },
        ),
      );
      await load();
    } catch (e) {
      setError((e as Error).message);
    }
  }
  return (
    <section aria-label="Patient administration" className="space-y-4">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-2xl font-semibold">Patient workspace</h2>
          <p className="text-sm">
            Profiles, related records and administrative history
          </p>
        </div>
        {permissions.includes("patient_write") && (
          <button
            className={button}
            onClick={() => {
              setCreating(true);
              setEditing(true);
              setForm(blank);
            }}
          >
            Add patient
          </button>
        )}
      </header>
      {error && (
        <p role="alert" className="rounded-xl bg-rose-50 p-3 text-rose-800">
          {error}
        </p>
      )}
      {loading && <p role="status">Loading records…</p>}
      {editing && (
        <form onSubmit={save} className={panel} aria-label="Patient form">
          <h3 className="font-semibold">
            {creating ? "New patient" : "Edit patient"}
          </h3>
          <div className="grid gap-3 md:grid-cols-2">
            {(
              [
                "first_name",
                "last_name",
                "phone",
                "email",
                "date_of_birth",
                "notes",
              ] as const
            ).map((k) => (
              <label key={k}>
                {k.replaceAll("_", " ")}
                <input
                  className={input}
                  type={
                    k === "date_of_birth"
                      ? "date"
                      : k === "email"
                        ? "email"
                        : "text"
                  }
                  required={k === "first_name" || k === "last_name"}
                  value={form[k]}
                  onChange={(e) => setForm({ ...form, [k]: e.target.value })}
                />
              </label>
            ))}
            <label>
              Contact preference
              <select
                className={input}
                value={form.preferred_contact_method}
                onChange={(e) =>
                  setForm({ ...form, preferred_contact_method: e.target.value })
                }
              >
                <option value="phone">Phone</option>
                <option value="email">Email</option>
                <option value="text">Text</option>
              </select>
            </label>
            {(["do_not_contact", "email_consent", "sms_consent"] as const).map(
              (k) => (
                <label key={k}>
                  <input
                    type="checkbox"
                    checked={form[k]}
                    onChange={(e) =>
                      setForm({ ...form, [k]: e.target.checked })
                    }
                  />{" "}
                  {k.replaceAll("_", " ")}
                </label>
              ),
            )}
          </div>
          <div className="mt-3 flex gap-2">
            <button className={button}>Save patient</button>
            <button type="button" onClick={() => setEditing(false)}>
              Cancel editing
            </button>
          </div>
        </form>
      )}
      <div className="grid gap-4 xl:grid-cols-[1fr_1.4fr]">
        <div className={panel}>
          <div className="grid gap-2 sm:grid-cols-3">
            <label>
              Search patients
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
                <option value="active">Active</option>
                <option value="archived">Archived</option>
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
                <option value="created_at">Registered</option>
                <option value="name">Name</option>
                <option value="last_appointment">Last visit</option>
              </select>
            </label>
          </div>
          {!items.length && !loading && <p>No patients match these filters.</p>}
          <ul className="divide-y">
            {items.map((p) => (
              <li key={p.id} className="py-3">
                <button
                  className="font-semibold text-cyan-700"
                  onClick={() => open(p.id)}
                >
                  {p.first_name} {p.last_name}
                </button>
                <p className="text-sm">
                  {p.phone || p.email || "No contact recorded"} · {p.status}
                </p>
                <p className="text-xs">
                  Registered {new Date(p.created_at).toLocaleDateString()} ·
                  Last visit{" "}
                  {p.last_appointment
                    ? new Date(p.last_appointment).toLocaleDateString()
                    : "—"}{" "}
                  · Next{" "}
                  {p.next_appointment
                    ? new Date(p.next_appointment).toLocaleDateString()
                    : "—"}
                </p>
              </li>
            ))}
          </ul>
          <div className="flex items-center gap-3">
            <button disabled={page === 1} onClick={() => setPage(page - 1)}>
              Previous patients
            </button>
            <span>
              {page} · {total} patients
            </span>
            <button
              disabled={page * 10 >= total}
              onClick={() => setPage(page + 1)}
            >
              Next patients
            </button>
          </div>
        </div>
        {patient && (
          <article className={panel}>
            <header>
              <h3 className="text-xl font-semibold">
                {patient.first_name} {patient.last_name}
              </h3>
              <p>
                {patient.status} ·{" "}
                {patient.phone || patient.email || "No contact"} · Revision{" "}
                {patient.revision}
              </p>
              <div className="my-3 flex gap-3">
                {permissions.includes("patient_write") && (
                  <button
                    className={button}
                    onClick={() => {
                      setCreating(false);
                      setEditing(true);
                      setForm({
                        ...blank,
                        ...patient,
                        phone: patient.phone || "",
                        email: patient.email || "",
                        date_of_birth: patient.date_of_birth || "",
                        notes: patient.notes || "",
                      });
                    }}
                  >
                    Edit patient
                  </button>
                )}
                {permissions.includes("patient_archive") && (
                  <button onClick={archive}>
                    {patient.status === "active"
                      ? "Archive patient"
                      : "Restore patient"}
                  </button>
                )}
              </div>
            </header>
            <div
              role="tablist"
              aria-label="Patient sections"
              className="flex flex-wrap gap-2 border-b pb-3"
            >
              {[
                "Overview",
                "Appointments",
                "Communications",
                "Follow-ups",
                "Insurance",
                "Timeline",
                ...(permissions.includes("estimate_read") ? ["Estimates"] : []),
              ].map((t) => (
                <button
                  key={t}
                  role="tab"
                  aria-selected={tab === t}
                  className={tab === t ? button : "rounded-xl border p-2"}
                  onClick={() => {
                    setTab(t);
                    setRelatedPage(1);
                  }}
                >
                  {t}
                </button>
              ))}
            </div>
            <div role="tabpanel" aria-label={tab} className="space-y-3 pt-3">
              {tab === "Overview" ? (
                <dl className="grid gap-2">
                  <dt>Contact preference</dt>
                  <dd>{patient.preferred_contact_method}</dd>
                  <dt>Do not contact</dt>
                  <dd>{patient.do_not_contact ? "Yes" : "No"}</dd>
                  <dt>Date of birth</dt>
                  <dd>{patient.date_of_birth || "Not recorded"}</dd>
                  <dt>Most recent completed visit</dt>
                  <dd>
                    {patient.last_appointment
                      ? new Date(patient.last_appointment).toLocaleString()
                      : "None recorded"}
                  </dd>
                  <dt>Next appointment</dt>
                  <dd>
                    {patient.next_appointment
                      ? new Date(patient.next_appointment).toLocaleString()
                      : "None scheduled"}
                  </dd>
                  <dt>Open follow-ups</dt>
                  <dd>{patient.open_followups ?? 0}</dd>
                  <dt>Registered</dt>
                  <dd>{new Date(patient.created_at).toLocaleString()}</dd>
                </dl>
              ) : (
                <>
                  {!rows.length && !loading && (
                    <p>No {tab.toLowerCase()} recorded.</p>
                  )}
                  <ul className="space-y-2">
                    {rows.map((r, i) => (
                      <li
                        key={String(r.id ?? i)}
                        className="rounded-xl border p-3 text-sm"
                      >
                        {tab === "Appointments" && (
                          <a
                            className="font-medium underline"
                            href="/dashboard?section=appointments"
                          >
                            Manage appointments
                          </a>
                        )}
                        {tab === "Communications" && (
                          <a
                            className="font-medium underline"
                            href="/dashboard?section=calls"
                          >
                            Open call workspace
                          </a>
                        )}
                        {tab === "Estimates" && (
                          <a
                            className="font-medium underline"
                            href={`/dashboard?section=estimates&estimate=${r.id}`}
                          >
                            Open estimate {r.number}
                          </a>
                        )}
                        {tab === "Follow-ups" && (
                          <a
                            className="font-medium underline"
                            href="/dashboard?section=follow-ups"
                          >
                            Open follow-up workspace
                          </a>
                        )}
                        {Object.entries(r)
                          .filter(([k]) =>
                            [
                              "description",
                              "timestamp",
                              "actor",
                              "status",
                              "start_time",
                              "outcome",
                              "reason",
                              "due_at",
                              "carrier_name",
                              "policy_number",
                              "number",
                              "total",
                              "currency",
                              "version",
                            ].includes(k),
                          )
                          .map(([k, v]) => (
                            <p key={k}>
                              <span className="font-medium">
                                {k.replaceAll("_", " ")}:
                              </span>{" "}
                              {String(v ?? "—")}
                            </p>
                          ))}
                      </li>
                    ))}
                  </ul>
                  {tab !== "Insurance" && (
                    <div className="flex gap-3">
                      <button
                        disabled={relatedPage === 1}
                        onClick={() => setRelatedPage(relatedPage - 1)}
                      >
                        Previous records
                      </button>
                      <span>{relatedTotal} records</span>
                      <button
                        disabled={relatedPage * 10 >= relatedTotal}
                        onClick={() => setRelatedPage(relatedPage + 1)}
                      >
                        Next records
                      </button>
                    </div>
                  )}
                </>
              )}
              {tab === "Insurance" && permissions.includes("patient_write") && (
                <form
                  aria-label="Patient insurance"
                  onSubmit={async (e) => {
                    e.preventDefault();
                    try {
                      await request(
                        `/patients/${patient.id}/insurance`,
                        "POST",
                        insurance,
                      );
                      setRows(
                        (await request(`/patients/${patient.id}/insurance`))
                          .items,
                      );
                      setInsurance({
                        carrier_name: "",
                        policy_number: "",
                        status: "pending",
                      });
                    } catch (e) {
                      setError((e as Error).message);
                    }
                  }}
                >
                  <label>
                    Carrier name
                    <input
                      className={input}
                      required
                      value={insurance.carrier_name}
                      onChange={(e) =>
                        setInsurance({
                          ...insurance,
                          carrier_name: e.target.value,
                        })
                      }
                    />
                  </label>
                  <label>
                    Policy number
                    <input
                      className={input}
                      value={insurance.policy_number}
                      onChange={(e) =>
                        setInsurance({
                          ...insurance,
                          policy_number: e.target.value,
                        })
                      }
                    />
                  </label>
                  <button className={button}>
                    Add insurance for this patient
                  </button>
                </form>
              )}
            </div>
          </article>
        )}
      </div>
    </section>
  );
}
