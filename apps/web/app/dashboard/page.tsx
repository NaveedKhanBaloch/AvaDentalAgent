"use client";

import { useEffect, useState } from 'react';
import { Activity, CalendarCheck2, MessageSquareText, Users } from 'lucide-react';

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

type Summary = {
  appointments_today: number;
  upcoming: number;
  pending_confirmations: number;
  cancelled: number;
  new_patients: number;
  calls_handled: number;
  missed_calls: number;
  follow_up_requests: number;
};

type PatientRow = {
  id: string;
  first_name: string;
  last_name: string;
  phone?: string | null;
  email?: string | null;
  preferred_contact_method?: string | null;
  notes?: string | null;
};

type AppointmentRow = {
  id: string;
  status: string;
  start_time: string;
};

type ProviderRow = {
  id: string;
  name: string;
  title?: string | null;
  specialty?: string | null;
};

type ServiceRow = {
  id: string;
  name: string;
  description?: string | null;
  default_duration_minutes: number;
  indicative_price: number;
};

const defaultForm = {
  first_name: '',
  last_name: '',
  phone: '',
  email: '',
  preferred_contact_method: 'phone',
  notes: '',
};

export default function DashboardPage() {
  const [summary, setSummary] = useState<Summary>({
    appointments_today: 0,
    upcoming: 0,
    pending_confirmations: 0,
    cancelled: 0,
    new_patients: 0,
    calls_handled: 0,
    missed_calls: 0,
    follow_up_requests: 0,
  });
  const [analytics, setAnalytics] = useState({ appointment_trends: [0, 0, 0, 0, 0, 0, 0], call_outcomes: { booked: 0, missed: 0, follow_up: 0 } });
  const [patients, setPatients] = useState<PatientRow[]>([]);
  const [appointments, setAppointments] = useState<AppointmentRow[]>([]);
  const [providers, setProviders] = useState<ProviderRow[]>([]);
  const [services, setServices] = useState<ServiceRow[]>([]);
  const [form, setForm] = useState(defaultForm);
  const [status, setStatus] = useState('');

  async function loadDashboard() {
    const [summaryRes, analyticsRes, patientsRes, appointmentsRes, providersRes, servicesRes] = await Promise.all([
      fetch(`${API_URL}/api/v1/dashboard/summary`),
      fetch(`${API_URL}/api/v1/dashboard/analytics`),
      fetch(`${API_URL}/api/v1/patients`),
      fetch(`${API_URL}/api/v1/appointments`),
      fetch(`${API_URL}/api/v1/providers`),
      fetch(`${API_URL}/api/v1/services`),
    ]);

    if (summaryRes.ok) setSummary(await summaryRes.json());
    if (analyticsRes.ok) setAnalytics(await analyticsRes.json());
    if (patientsRes.ok) {
      const patientData = await patientsRes.json();
      setPatients(patientData.items ?? []);
    }
    if (appointmentsRes.ok) {
      const appointmentData = await appointmentsRes.json();
      setAppointments(appointmentData.items ?? []);
    }
    if (providersRes.ok) {
      const providerData = await providersRes.json();
      setProviders(providerData.items ?? []);
    }
    if (servicesRes.ok) {
      const serviceData = await servicesRes.json();
      setServices(serviceData.items ?? []);
    }
  }

  useEffect(() => {
    loadDashboard();
  }, []);

  async function handleCreatePatient(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const response = await fetch(`${API_URL}/api/v1/patients`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(form),
    });

    if (response.ok) {
      setForm(defaultForm);
      setStatus('Patient added successfully.');
      await loadDashboard();
    } else {
      const error = await response.json();
      setStatus(error.detail ?? 'Unable to add patient');
    }
  }

  const metrics = [
    { label: 'Appointments today', value: summary.appointments_today, icon: CalendarCheck2 },
    { label: 'Upcoming', value: summary.upcoming, icon: Activity },
    { label: 'Patients', value: summary.new_patients, icon: Users },
    { label: 'AI calls', value: summary.calls_handled, icon: MessageSquareText },
  ];

  return (
    <main className="min-h-screen bg-slate-100 p-6 text-slate-900">
      <div className="mx-auto max-w-7xl">
        <header className="mb-6 flex items-center justify-between">
          <div>
            <p className="text-sm uppercase tracking-[0.2em] text-slate-500">Dashboard</p>
            <h1 className="text-3xl font-bold">Harbor Dental Demo</h1>
          </div>
          <div className="rounded-full bg-white px-4 py-2 text-sm font-medium text-slate-700 shadow-sm">Clinic owner</div>
        </header>

        <section className="mb-8 grid gap-4 md:grid-cols-4">
          {metrics.map((metric) => (
            <div key={metric.label} className="rounded-2xl bg-white p-5 shadow-sm ring-1 ring-slate-200">
              <div className="mb-3 flex items-center justify-between text-slate-500">
                <span className="text-sm">{metric.label}</span>
                <metric.icon size={18} className="text-brand-600" />
              </div>
              <div className="text-3xl font-bold">{metric.value}</div>
            </div>
          ))}
        </section>

        <section className="mb-8 grid gap-6 lg:grid-cols-[1.5fr_1fr]">
          <div className="rounded-3xl bg-white p-5 shadow-sm ring-1 ring-slate-200">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-xl font-semibold">Schedule overview</h2>
              <span className="rounded-full bg-brand-50 px-3 py-1 text-xs font-medium text-brand-600">Live</span>
            </div>
            <div className="flex h-40 items-end gap-3">
              {analytics.appointment_trends.map((value, index) => (
                <div key={index} className="flex flex-1 flex-col items-center gap-2">
                  <div className="w-full rounded-t-xl bg-brand-500/80" style={{ height: `${Math.max(18, value * 24)}px` }} />
                  <span className="text-[10px] text-slate-500">{index + 1}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="rounded-3xl bg-white p-5 shadow-sm ring-1 ring-slate-200">
            <h2 className="mb-4 text-xl font-semibold">AI receptionist activity</h2>
            <ul className="space-y-3 text-sm text-slate-600">
              <li className="rounded-xl bg-slate-50 p-3">Booked {analytics.call_outcomes.booked} conversations this week.</li>
              <li className="rounded-xl bg-slate-50 p-3">Missed calls: {analytics.call_outcomes.missed}.</li>
              <li className="rounded-xl bg-slate-50 p-3">Follow-up requests: {analytics.call_outcomes.follow_up}.</li>
            </ul>
          </div>
        </section>

        <section className="grid gap-6 lg:grid-cols-[1.1fr_1fr]">
          <div className="rounded-3xl bg-white p-5 shadow-sm ring-1 ring-slate-200">
            <h2 className="mb-4 text-xl font-semibold">Add patient</h2>
            <form className="space-y-3" onSubmit={handleCreatePatient}>
              <div className="grid gap-3 md:grid-cols-2">
                <input value={form.first_name} onChange={(event) => setForm({ ...form, first_name: event.target.value })} placeholder="First name" className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 outline-none" />
                <input value={form.last_name} onChange={(event) => setForm({ ...form, last_name: event.target.value })} placeholder="Last name" className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 outline-none" />
              </div>
              <div className="grid gap-3 md:grid-cols-2">
                <input value={form.phone} onChange={(event) => setForm({ ...form, phone: event.target.value })} placeholder="Phone" className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 outline-none" />
                <input value={form.email} onChange={(event) => setForm({ ...form, email: event.target.value })} placeholder="Email" className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 outline-none" />
              </div>
              <input value={form.preferred_contact_method} onChange={(event) => setForm({ ...form, preferred_contact_method: event.target.value })} placeholder="Preferred contact method" className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 outline-none" />
              <textarea value={form.notes} onChange={(event) => setForm({ ...form, notes: event.target.value })} placeholder="Notes" rows={3} className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 outline-none" />
              <button type="submit" className="rounded-xl bg-slate-900 px-4 py-2 font-medium text-white">Save patient</button>
              {status ? <p className="text-sm text-slate-600">{status}</p> : null}
            </form>
          </div>

          <div className="rounded-3xl bg-white p-5 shadow-sm ring-1 ring-slate-200">
            <h2 className="mb-4 text-xl font-semibold">Care team</h2>
            <div className="space-y-3">
              {providers.map((provider) => (
                <div key={provider.id} className="rounded-xl bg-slate-50 p-3 text-sm text-slate-700">
                  <div className="font-semibold text-slate-900">{provider.name}</div>
                  <div>{provider.title ?? 'Provider'} · {provider.specialty ?? 'General care'}</div>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="mt-8 grid gap-6 lg:grid-cols-[1.2fr_1fr]">
          <div className="rounded-3xl bg-white p-5 shadow-sm ring-1 ring-slate-200">
            <h2 className="mb-4 text-xl font-semibold">Upcoming appointments</h2>
            <div className="space-y-3">
              {appointments.map((appointment) => (
                <div key={appointment.id} className="flex items-center justify-between rounded-xl bg-slate-50 p-3 text-sm text-slate-700">
                  <span>{new Date(appointment.start_time).toLocaleString()}</span>
                  <span className="rounded-full bg-brand-50 px-2 py-1 text-xs font-medium text-brand-600">{appointment.status}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="rounded-3xl bg-white p-5 shadow-sm ring-1 ring-slate-200">
            <h2 className="mb-4 text-xl font-semibold">Service menu</h2>
            <div className="space-y-3">
              {services.map((service) => (
                <div key={service.id} className="rounded-xl bg-slate-50 p-3 text-sm text-slate-700">
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-slate-900">{service.name}</span>
                    <span>{service.default_duration_minutes} min</span>
                  </div>
                  <div className="mt-1">${service.indicative_price.toFixed(2)}</div>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="mt-8 rounded-3xl bg-white p-5 shadow-sm ring-1 ring-slate-200">
          <h2 className="mb-4 text-xl font-semibold">Recent patients</h2>
          <div className="space-y-3">
            {patients.map((patient) => (
              <div key={patient.id} className="rounded-xl bg-slate-50 p-3 text-sm text-slate-700">
                <div className="font-semibold text-slate-900">{patient.first_name} {patient.last_name}</div>
                <div>{patient.phone ?? patient.email ?? 'No contact info'}</div>
              </div>
            ))}
          </div>
        </section>

      </div>
    </main>
  );
}
