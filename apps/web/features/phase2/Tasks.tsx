"use client";
import { useCallback, useEffect, useState } from "react";
import { request, input, button, panel } from "./api";
type Row = {
  id: string;
  patient_id: string | null;
  patient_name?: string;
  recall_rule_id?: string;
  contact_name?: string;
  contact_phone?: string;
  reason: string;
  status: string;
  priority?: string;
  followup_type?: string;
  recall_type?: string;
  due_at?: string | null;
  due_date?: string;
  assigned_user_id?: string | null;
  appointment_id?: string | null;
  origin_appointment_id?: string | null;
  call_id?: string | null;
  estimate_id?: string | null;
  notes?: string;
  completion_reason?: string;
  contact_preference?: string;
  revision: number;
  completed_at?: string;
};
type Patient = { id: string; first_name: string; last_name: string };
const empty = {
  patient_id: "",
  contact_name: "",
  contact_phone: "",
  reason: "",
  priority: "normal",
  followup_type: "general_callback",
  recall_type: "",
  due_at: "",
  due_date: "",
  assigned_user_id: "",
  appointment_id: "",
  origin_appointment_id: "",
  call_id: "",
  estimate_id: "",
  notes: "",
  contact_preference: "phone",
  completion_reason: "",
  status: "pending",
  recall_rule_id: "",
  log_contact_attempt: false,
};
export default function Tasks({ kind }: { kind: "follow-ups" | "recalls" }) {
  const recall = kind === "recalls",
    label = recall ? "Recall" : "Follow-up",
    permission = recall ? "recall_write" : "followup_write";
  const [rules, setRules] = useState<
      { id: string; name: string; interval_days: number }[]
    >([]),
    [ruleName, setRuleName] = useState(""),
    [interval, setInterval] = useState(""),
    [ruleApproved, setRuleApproved] = useState(false);
  const [items, setItems] = useState<Row[]>([]),
    [patients, setPatients] = useState<Patient[]>([]),
    [staff, setStaff] = useState<{ user_id: string; full_name: string }[]>([]),
    [calls, setCalls] = useState<{ id: string; status: string }[]>([]),
    [appointments, setAppointments] = useState<
      { id: string; start_time: string; status: string }[]
    >([]);
  const [page, setPage] = useState(1),
    [total, setTotal] = useState(0),
    [search, setSearch] = useState(""),
    [status, setStatus] = useState(""),
    [overdue, setOverdue] = useState(false),
    [dueFrom, setDueFrom] = useState(""),
    [dueTo, setDueTo] = useState(""),
    [assignee, setAssignee] = useState(""),
    [priority, setPriority] = useState("");
  const [error, setError] = useState(""),
    [loading, setLoading] = useState(false),
    [permissions, setPermissions] = useState<string[]>([]),
    [editing, setEditing] = useState(false),
    [selected, setSelected] = useState<Row | null>(null),
    [form, setForm] = useState(empty),
    [patientSearch, setPatientSearch] = useState(""),
    [sandbox, setSandbox] = useState("");
  const [estimates, setEstimates] = useState<{ id: string; number: string }[]>(
    [],
  );
  useEffect(() => {
    if (!recall && form.patient_id && permissions.includes("estimate_read"))
      request(`/estimates?patient_id=${form.patient_id}&page_size=100`)
        .then((d) => setEstimates(d.items))
        .catch((e) => setError(e.message));
    else setEstimates([]);
  }, [recall, form.patient_id, permissions]);
  const load = useCallback(async () => {
    setLoading(true);
    try {
      const q = new URLSearchParams({
        page: String(page),
        page_size: "10",
        search,
        status,
        overdue: String(overdue),
      });
      if (assignee) q.set("assigned_user_id", assignee);
      if (priority && !recall) q.set("priority", priority);
      if (dueFrom) q.set("due_from", recall ? dueFrom : dueFrom + "T00:00:00Z");
      if (dueTo) q.set("due_to", recall ? dueTo : dueTo + "T23:59:59Z");
      const d = await request(`/operations/${kind}?${q}`);
      setItems(d.items);
      setTotal(d.total);
      setError("");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, [
    page,
    search,
    status,
    overdue,
    kind,
    assignee,
    priority,
    dueFrom,
    dueTo,
    recall,
  ]);
  useEffect(() => {
    const q = new URLSearchParams(window.location.search);
    setStatus(q.get("status") ?? "");
    setOverdue(q.get("overdue") === "true");
  }, []);
  useEffect(() => {
    void load();
  }, [load]);
  useEffect(() => {
    if (recall)
      request("/operations/recall-rules")
        .then((d) => setRules(d.items))
        .catch((e) => setError(e.message));
  }, [recall]);
  useEffect(() => {
    request("/operations/capabilities")
      .then((d) => setPermissions(d.permissions))
      .catch((e) => setError(e.message));
    request("/staff")
      .then((d) => setStaff(d.items))
      .catch((e) => setError(e.message));
  }, []);
  useEffect(() => {
    request(
      `/patients?status=active&search=${encodeURIComponent(patientSearch)}&page_size=100`,
    )
      .then((d) => setPatients(d.items))
      .catch((e) => setError(e.message));
  }, [patientSearch]);
  useEffect(() => {
    if (!recall && form.patient_id)
      request(`/patients/${form.patient_id}/communications?page_size=100`)
        .then((d) => setCalls(d.items))
        .catch((e) => setError(e.message));
    else setCalls([]);
  }, [form.patient_id, recall]);
  useEffect(() => {
    if (form.patient_id)
      request(`/patients/${form.patient_id}/appointments?page_size=100`)
        .then((d) => setAppointments(d.items))
        .catch((e) => setError(e.message));
    else setAppointments([]);
  }, [form.patient_id]);
  function edit(r: Row | null) {
    setSelected(r);
    setEditing(true);
    setForm({
      ...empty,
      status: recall ? "due" : "pending",
      ...(r
        ? Object.fromEntries(Object.entries(r).map(([k, v]) => [k, v ?? ""]))
        : {}),
      due_at: r?.due_at
        ? new Date(
            new Date(r.due_at).getTime() -
              new Date(r.due_at).getTimezoneOffset() * 60000,
          )
            .toISOString()
            .slice(0, 16)
        : "",
    } as typeof empty);
  }
  async function save(e: React.FormEvent) {
    e.preventDefault();
    if (
      selected &&
      form.status !== selected.status &&
      !confirm(`Change ${label.toLowerCase()} to ${form.status}?`)
    )
      return;
    try {
      const common = {
        patient_id: form.patient_id || null,
        reason: form.reason,
        assigned_user_id: form.assigned_user_id || null,
        appointment_id: form.appointment_id || null,
      };
      const body = recall
        ? {
            ...common,
            recall_type: form.recall_type,
            due_date: form.due_date || null,
            recall_rule_id: form.recall_rule_id || null,
            origin_appointment_id: form.origin_appointment_id || null,
            contact_preference: form.contact_preference,
            ...(selected
              ? { log_contact_attempt: form.log_contact_attempt }
              : {}),
            ...(selected
              ? { completion_reason: form.completion_reason || null }
              : {}),
          }
        : {
            ...common,
            contact_name: form.contact_name || null,
            contact_phone: form.contact_phone || null,
            followup_type: form.followup_type,
            priority: form.priority,
            due_at: form.due_at ? new Date(form.due_at).toISOString() : null,
            notes: form.notes || null,
            call_id: form.call_id || null,
            estimate_id: form.estimate_id || null,
          };
      await request(
        `/operations/${kind}${selected ? "/" + selected.id : ""}`,
        selected ? "PATCH" : "POST",
        {
          ...body,
          ...(selected
            ? { expected_revision: selected.revision, status: form.status }
            : {}),
        },
      );
      setEditing(false);
      await load();
    } catch (e) {
      setError((e as Error).message);
    }
  }
  const states = recall
    ? [
        "due",
        "contact_pending",
        "contacted",
        "scheduled",
        "completed",
        "cancelled",
      ]
    : ["pending", "in_progress", "completed", "cancelled"];
  return (
    <section className="space-y-4">
      <header className="flex flex-wrap justify-between gap-3">
        <div>
          <h2 className="text-2xl font-semibold">
            {recall ? "Patient recalls" : "Follow-up workspace"}
          </h2>
          <p>
            {recall
              ? "Future visits with clinician-approved dates"
              : "Unresolved administrative actions and callbacks"}
          </p>
        </div>
        {permissions.includes(permission) && (
          <button className={button} onClick={() => edit(null)}>
            New {label.toLowerCase()}
          </button>
        )}
      </header>
      {error && (
        <p role="alert" className="rounded-xl bg-rose-50 p-3 text-rose-800">
          {error}
        </p>
      )}
      {loading && <p role="status">Loading…</p>}
      <div className={panel}>
        <div className="grid gap-3 sm:grid-cols-3">
          <label>
            Search
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
              {states.map((s) => (
                <option key={s}>{s}</option>
              ))}
            </select>
          </label>
          <label>
            Assigned staff
            <select
              className={input}
              value={assignee}
              onChange={(e) => {
                setAssignee(e.target.value);
                setPage(1);
              }}
            >
              <option value="">All staff</option>
              {staff.map((s) => (
                <option key={s.user_id} value={s.user_id}>
                  {s.full_name}
                </option>
              ))}
            </select>
          </label>
          <label>
            Due from
            <input
              className={input}
              type="date"
              value={dueFrom}
              onChange={(e) => {
                setDueFrom(e.target.value);
                setPage(1);
              }}
            />
          </label>
          <label>
            Due to
            <input
              className={input}
              type="date"
              value={dueTo}
              onChange={(e) => {
                setDueTo(e.target.value);
                setPage(1);
              }}
            />
          </label>
          {!recall && (
            <label>
              Priority
              <select
                className={input}
                value={priority}
                onChange={(e) => {
                  setPriority(e.target.value);
                  setPage(1);
                }}
              >
                <option value="">All priorities</option>
                {["low", "normal", "high"].map((s) => (
                  <option key={s}>{s}</option>
                ))}
              </select>
            </label>
          )}
          <label>
            <input
              type="checkbox"
              checked={overdue}
              onChange={(e) => {
                setOverdue(e.target.checked);
                setPage(1);
              }}
            />{" "}
            Overdue only
          </label>
        </div>
      </div>
      {editing && (
        <form onSubmit={save} className={panel} aria-label={`${label} form`}>
          <h3 className="font-semibold">
            {selected ? "Edit" : "Create"} {label.toLowerCase()}
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
                required={recall}
                value={form.patient_id}
                onChange={(e) =>
                  setForm({
                    ...form,
                    patient_id: e.target.value,
                    appointment_id: "",
                    origin_appointment_id: "",
                  })
                }
              >
                <option value="">
                  {recall
                    ? "Select patient"
                    : "Unverified callback / no linked patient"}
                </option>
                {patients.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.first_name} {p.last_name}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Reason
              <input
                className={input}
                required={!recall}
                value={form.reason}
                onChange={(e) => setForm({ ...form, reason: e.target.value })}
              />
            </label>
            <label>
              Type
              <input
                className={input}
                required
                value={recall ? form.recall_type : form.followup_type}
                onChange={(e) =>
                  setForm({
                    ...form,
                    [recall ? "recall_type" : "followup_type"]: e.target.value,
                  })
                }
              />
            </label>
            <label>
              {recall ? "Approved due date" : "Due time (device timezone)"}
              <input
                className={input}
                required={recall && !form.recall_rule_id}
                type={recall ? "date" : "datetime-local"}
                value={recall ? form.due_date : form.due_at}
                onChange={(e) =>
                  setForm({
                    ...form,
                    [recall ? "due_date" : "due_at"]: e.target.value,
                  })
                }
              />
            </label>
            <label>
              Assign staff
              <select
                className={input}
                value={form.assigned_user_id}
                onChange={(e) =>
                  setForm({ ...form, assigned_user_id: e.target.value })
                }
              >
                <option value="">Unassigned</option>
                {staff.map((s) => (
                  <option key={s.user_id} value={s.user_id}>
                    {s.full_name}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Related appointment
              <select
                className={input}
                value={form.appointment_id}
                onChange={(e) =>
                  setForm({ ...form, appointment_id: e.target.value })
                }
              >
                <option value="">None</option>
                {appointments.map((a) => (
                  <option key={a.id} value={a.id}>
                    {new Date(a.start_time).toLocaleString()} · {a.status}
                  </option>
                ))}
              </select>
            </label>
            {!recall ? (
              <>
                <label>
                  Related verified call
                  <select
                    className={input}
                    value={form.call_id}
                    onChange={(e) =>
                      setForm({ ...form, call_id: e.target.value })
                    }
                  >
                    <option value="">None</option>
                    {calls.map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.status} · {c.id}
                      </option>
                    ))}
                  </select>
                </label>
                {permissions.includes("estimate_read") && (
                  <label>
                    Related estimate
                    <select
                      className={input}
                      value={form.estimate_id}
                      onChange={(e) =>
                        setForm({ ...form, estimate_id: e.target.value })
                      }
                    >
                      <option value="">None</option>
                      {estimates.map((e) => (
                        <option key={e.id} value={e.id}>
                          {e.number}
                        </option>
                      ))}
                    </select>
                  </label>
                )}
                <label>
                  Callback name
                  <input
                    className={input}
                    value={form.contact_name}
                    onChange={(e) =>
                      setForm({ ...form, contact_name: e.target.value })
                    }
                  />
                </label>
                <label>
                  Callback phone
                  <input
                    className={input}
                    required={!form.patient_id}
                    value={form.contact_phone}
                    onChange={(e) =>
                      setForm({ ...form, contact_phone: e.target.value })
                    }
                  />
                </label>
                <label>
                  Priority
                  <select
                    className={input}
                    value={form.priority}
                    onChange={(e) =>
                      setForm({ ...form, priority: e.target.value })
                    }
                  >
                    {["low", "normal", "high"].map((s) => (
                      <option key={s}>{s}</option>
                    ))}
                  </select>
                </label>
                <label>
                  Notes
                  <textarea
                    className={input}
                    value={form.notes}
                    onChange={(e) =>
                      setForm({ ...form, notes: e.target.value })
                    }
                  />
                </label>
              </>
            ) : (
              <>
                <label>
                  Approved interval rule
                  <select
                    className={input}
                    value={form.recall_rule_id}
                    onChange={(e) =>
                      setForm({ ...form, recall_rule_id: e.target.value })
                    }
                  >
                    <option value="">Manual approved due date</option>
                    {rules.map((r) => (
                      <option key={r.id} value={r.id}>
                        {r.name} · {r.interval_days} days after completed origin
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  Completed origin appointment
                  <select
                    className={input}
                    value={form.origin_appointment_id}
                    onChange={(e) =>
                      setForm({
                        ...form,
                        origin_appointment_id: e.target.value,
                      })
                    }
                  >
                    <option value="">None</option>
                    {appointments
                      .filter((a) => a.status === "completed")
                      .map((a) => (
                        <option key={a.id} value={a.id}>
                          {new Date(a.start_time).toLocaleString()}
                        </option>
                      ))}
                  </select>
                </label>
                <label>
                  Contact preference
                  <select
                    className={input}
                    value={form.contact_preference}
                    onChange={(e) =>
                      setForm({ ...form, contact_preference: e.target.value })
                    }
                  >
                    {["phone", "email", "sms"].map((s) => (
                      <option key={s}>{s}</option>
                    ))}
                  </select>
                </label>
                {selected && (
                  <label>
                    <input
                      type="checkbox"
                      checked={form.log_contact_attempt}
                      onChange={(e) =>
                        setForm({
                          ...form,
                          log_contact_attempt: e.target.checked,
                        })
                      }
                    />{" "}
                    Record a contact attempt already made by staff
                  </label>
                )}
                {selected && (
                  <label>
                    Administrative completion reason
                    <input
                      className={input}
                      value={form.completion_reason}
                      onChange={(e) =>
                        setForm({ ...form, completion_reason: e.target.value })
                      }
                    />
                  </label>
                )}
              </>
            )}
            {selected && (
              <label>
                Status
                <select
                  className={input}
                  value={form.status}
                  onChange={(e) => setForm({ ...form, status: e.target.value })}
                >
                  {states.map((s) => (
                    <option key={s}>{s}</option>
                  ))}
                </select>
              </label>
            )}
          </div>
          <div className="mt-3 flex gap-3">
            <button className={button}>Save {label.toLowerCase()}</button>
            <button type="button" onClick={() => setEditing(false)}>
              Cancel editing
            </button>
          </div>
          {selected?.completed_at && (
            <p>Completed {new Date(selected.completed_at).toLocaleString()}</p>
          )}
        </form>
      )}
      <div className="space-y-3">
        {!items.length && !loading && <p>No records match these filters.</p>}
        {items.map((r) => (
          <article key={r.id} className={panel}>
            <div className="flex flex-wrap justify-between gap-2">
              <div>
                <h3 className="font-semibold">
                  {r.reason || r.recall_type || r.followup_type}
                </h3>
                <p>
                  {r.patient_name || r.contact_name || "Unverified callback"}
                </p>
                <p>
                  {r.status} · {r.priority || "Recall"} ·{" "}
                  {r.due_date ||
                    (r.due_at
                      ? new Date(r.due_at).toLocaleString()
                      : "No due time")}
                </p>
                <p>
                  {r.patient_id
                    ? patients.find((p) => p.id === r.patient_id)?.first_name ||
                      "Linked patient"
                    : r.contact_name || r.contact_phone || "Callback"}
                </p>
                {r.patient_id && (
                  <a
                    className="text-cyan-700"
                    href={`/dashboard?section=patients&patient=${r.patient_id}`}
                  >
                    Open patient profile
                  </a>
                )}
              </div>
              {permissions.includes(permission) && (
                <button className={button} onClick={() => edit(r)}>
                  View / edit
                </button>
              )}
            </div>
          </article>
        ))}
      </div>
      <div className="flex gap-3">
        <button disabled={page === 1} onClick={() => setPage(page - 1)}>
          Previous records
        </button>
        <span>
          {total} records · page {page}
        </span>
        <button disabled={page * 10 >= total} onClick={() => setPage(page + 1)}>
          Next records
        </button>
      </div>
      {recall && permissions.includes("manage_schedule") && (
        <form
          className={panel}
          aria-label="Recall interval rule"
          onSubmit={async (e) => {
            e.preventDefault();
            try {
              await request("/operations/recall-rules", "POST", {
                name: ruleName,
                interval_days: Number(interval),
                clinically_approved: ruleApproved,
              });
              setRules((await request("/operations/recall-rules")).items);
              setRuleName("");
              setInterval("");
              setRuleApproved(false);
            } catch (e) {
              setError((e as Error).message);
            }
          }}
        >
          <h3 className="font-semibold">Approve a clinic recall interval</h3>
          <label>
            Rule name
            <input
              className={input}
              required
              value={ruleName}
              onChange={(e) => setRuleName(e.target.value)}
            />
          </label>
          <label>
            Interval in days
            <input
              className={input}
              type="number"
              min="1"
              max="3650"
              required
              value={interval}
              onChange={(e) => setInterval(e.target.value)}
            />
          </label>
          <label>
            <input
              type="checkbox"
              required
              checked={ruleApproved}
              onChange={(e) => setRuleApproved(e.target.checked)}
            />{" "}
            This interval has clinical approval for this clinic.
          </label>
          <button className={button}>Save approved interval</button>
        </form>
      )}
      {permissions.includes("operations_report") && (
        <div className={panel}>
          <h3 className="font-semibold">Sandbox reminders</h3>
          <p>Prepares due records only. No email, SMS or phone call is sent.</p>
          <button
            className={button}
            onClick={async () => {
              try {
                const d = await request(
                  "/operations/reminders/prepare",
                  "POST",
                );
                setSandbox(
                  `${d.processed} preparations; ${d.messages_sent} messages sent.`,
                );
              } catch (e) {
                setError((e as Error).message);
              }
            }}
          >
            Prepare sandbox reminders
          </button>
          <p role="status">{sandbox}</p>
        </div>
      )}
    </section>
  );
}
