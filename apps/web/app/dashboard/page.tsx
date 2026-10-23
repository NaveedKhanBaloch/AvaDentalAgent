"use client";

import { useCallback, useEffect, useMemo, useState } from 'react';
import { Activity, CalendarCheck2, LogOut, MessageSquareText, Users } from 'lucide-react';
import { useRouter } from 'next/navigation';

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

type StaffRow = {
  id: string;
  user_id: string;
  full_name: string;
  email?: string | null;
  role?: string | null;
  status?: string | null;
};

type CallLogRow = {
  id: string;
  caller_number?: string | null;
  direction?: string | null;
  status?: string | null;
  outcome?: string | null;
  duration?: number | null;
  summary?: string | null;
  start_time?: string | null;
};

type FollowUpRow = {
  id: string;
  contact_name?: string | null;
  contact_phone?: string | null;
  reason?: string | null;
  priority?: string | null;
  status?: string | null;
};

const defaultForm = {
  first_name: '',
  last_name: '',
  phone: '',
  email: '',
  preferred_contact_method: 'phone',
  notes: '',
};

const defaultBookingForm = {
  patient_id: '',
  provider_id: '',
  service_id: '',
  start_time: '',
  notes: '',
};

type UserProfile = {
  id: string;
  email: string;
  full_name: string;
  status: string;
  role?: string | null;
};

function getAuthHeaders(): HeadersInit {
  const token = typeof window !== 'undefined' ? localStorage.getItem('dentalvoice_token') : null;
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export default function DashboardPage() {
  const router = useRouter();
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
  const [staff, setStaff] = useState<StaffRow[]>([]);
  const [calls, setCalls] = useState<CallLogRow[]>([]);
  const [followUps, setFollowUps] = useState<FollowUpRow[]>([]);
  const [user, setUser] = useState<UserProfile | null>(null);
  const [form, setForm] = useState(defaultForm);
  const [bookingForm, setBookingForm] = useState(defaultBookingForm);
  const [status, setStatus] = useState('');
  const [bookingStatus, setBookingStatus] = useState('');
  const [insuranceForm, setInsuranceForm] = useState({
    carrier_name: '',
    policy_number: '',
    group_number: '',
    member_name: '',
    subscriber_dob: '',
    relationship_to_patient: 'self',
    status: 'pending',
    notes: '',
  });
  const [insuranceMessage, setInsuranceMessage] = useState('');
  const [activeSection, setActiveSection] = useState<'dashboard' | 'patients' | 'appointments' | 'providers' | 'services' | 'insurance' | 'calls' | 'staff' | 'settings'>('dashboard');
  const [patientSearch, setPatientSearch] = useState('');
  const [appointmentSearch, setAppointmentSearch] = useState('');
  const [providerSearch, setProviderSearch] = useState('');
  const [serviceSearch, setServiceSearch] = useState('');
  const [providerForm, setProviderForm] = useState({ name: '', title: '', specialty: '', active_status: true });
  const [serviceForm, setServiceForm] = useState({ name: '', description: '', default_duration_minutes: 30, indicative_price: 0, currency: 'USD', active_status: true });

  const loadDashboard = useCallback(async () => {
    const token = typeof window !== 'undefined' ? localStorage.getItem('dentalvoice_token') : null;
    if (!token) {
      router.push('/login');
      return;
    }

    const [summaryRes, analyticsRes, patientsRes, appointmentsRes, providersRes, servicesRes, staffRes, callsRes, followUpsRes] = await Promise.all([
      fetch(`${API_URL}/api/v1/dashboard/summary`),
      fetch(`${API_URL}/api/v1/dashboard/analytics`),
      fetch(`${API_URL}/api/v1/patients`),
      fetch(`${API_URL}/api/v1/appointments`),
      fetch(`${API_URL}/api/v1/providers`),
      fetch(`${API_URL}/api/v1/services`),
      fetch(`${API_URL}/api/v1/staff`),
      fetch(`${API_URL}/api/v1/operations/calls`),
      fetch(`${API_URL}/api/v1/operations/follow-ups`),
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
      setBookingForm((current) => ({
        ...current,
        provider_id: current.provider_id || providerData.items?.[0]?.id || '',
      }));
    }
    if (servicesRes.ok) {
      const serviceData = await servicesRes.json();
      setServices(serviceData.items ?? []);
      setBookingForm((current) => ({
        ...current,
        service_id: current.service_id || serviceData.items?.[0]?.id || '',
      }));
    }
    if (staffRes.ok) {
      const staffData = await staffRes.json();
      setStaff(staffData.items ?? []);
    }
    if (callsRes.ok) {
      const callData = await callsRes.json();
      setCalls(callData.items ?? []);
    }
    if (followUpsRes.ok) {
      const followUpData = await followUpsRes.json();
      setFollowUps(followUpData.items ?? []);
    }

    try {
      const meResponse = await fetch(`${API_URL}/api/v1/auth/me`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (meResponse.ok) {
        setUser(await meResponse.json());
      }
    } catch {
      // no-op
    }
  }, [router]);

  useEffect(() => {
    void loadDashboard();
  }, [loadDashboard]);

  const filteredPatients = useMemo(() => patients.filter((patient) => {
    const term = patientSearch.toLowerCase();
    if (!term) return true;
    return `${patient.first_name} ${patient.last_name}`.toLowerCase().includes(term)
      || (patient.email ?? '').toLowerCase().includes(term)
      || (patient.phone ?? '').toLowerCase().includes(term);
  }), [patients, patientSearch]);

  const filteredAppointments = useMemo(() => appointments.filter((appointment) => {
    const term = appointmentSearch.toLowerCase();
    if (!term) return true;
    return appointment.status.toLowerCase().includes(term) || new Date(appointment.start_time).toLocaleString().toLowerCase().includes(term);
  }), [appointments, appointmentSearch]);

  const filteredProviders = useMemo(() => providers.filter((provider) => {
    const term = providerSearch.toLowerCase();
    if (!term) return true;
    return provider.name.toLowerCase().includes(term) || (provider.specialty ?? '').toLowerCase().includes(term);
  }), [providers, providerSearch]);

  const filteredServices = useMemo(() => services.filter((service) => {
    const term = serviceSearch.toLowerCase();
    if (!term) return true;
    return service.name.toLowerCase().includes(term) || (service.description ?? '').toLowerCase().includes(term);
  }), [services, serviceSearch]);

  async function handleCreatePatient(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const payload = {
      ...form,
      phone: form.phone.trim() || null,
      email: form.email.trim() || null,
      notes: form.notes.trim() || null,
    };

    const response = await fetch(`${API_URL}/api/v1/patients`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
      body: JSON.stringify(payload),
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

  async function handleCreateAppointment(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!bookingForm.patient_id || !bookingForm.provider_id || !bookingForm.service_id || !bookingForm.start_time) {
      setBookingStatus('Please choose a patient, provider, service, and time.');
      return;
    }

    const service = services.find((item) => item.id === bookingForm.service_id);
    const start = new Date(bookingForm.start_time);
    const durationMs = ((service?.default_duration_minutes ?? 30) * 60 * 1000);
    const payload = {
      patient_id: bookingForm.patient_id,
      provider_id: bookingForm.provider_id,
      service_id: bookingForm.service_id,
      start_time: start.toISOString(),
      end_time: new Date(start.getTime() + durationMs).toISOString(),
      status: 'scheduled',
      source: 'dashboard',
      notes: bookingForm.notes,
    };

    const response = await fetch(`${API_URL}/api/v1/appointments`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
      body: JSON.stringify(payload),
    });

    if (response.ok) {
      setBookingForm({ ...defaultBookingForm, provider_id: providers[0]?.id ?? '', service_id: services[0]?.id ?? '' });
      setBookingStatus('Appointment scheduled successfully.');
      await loadDashboard();
    } else {
      const error = await response.json();
      setBookingStatus(error.detail ?? 'Unable to schedule appointment');
    }
  }

  async function handleUpdateAppointment(appointmentId: string, nextStatus: string) {
    const response = await fetch(`${API_URL}/api/v1/appointments/${appointmentId}/status`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
      body: JSON.stringify({ status: nextStatus }),
    });

    if (response.ok) {
      setBookingStatus(`Appointment marked as ${nextStatus}.`);
      await loadDashboard();
    } else {
      const error = await response.json();
      setBookingStatus(error.detail ?? 'Unable to update appointment');
    }
  }

  async function handleDeleteAppointment(appointmentId: string) {
    const response = await fetch(`${API_URL}/api/v1/appointments/${appointmentId}`, {
      method: 'DELETE',
      headers: getAuthHeaders(),
    });

    if (response.ok) {
      setBookingStatus('Appointment cancelled and removed from the active schedule.');
      await loadDashboard();
    } else {
      const error = await response.json();
      setBookingStatus(error.detail ?? 'Unable to cancel appointment');
    }
  }

  async function handleDeletePatient(patientId: string) {
    const response = await fetch(`${API_URL}/api/v1/patients/${patientId}`, {
      method: 'DELETE',
      headers: getAuthHeaders(),
    });

    if (response.ok) {
      setStatus('Patient deleted successfully.');
      await loadDashboard();
    } else {
      const error = await response.json();
      setStatus(error.detail ?? 'Unable to delete patient');
    }
  }

  async function handleCreateProvider(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const response = await fetch(`${API_URL}/api/v1/providers`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
      body: JSON.stringify({
        ...providerForm,
        name: providerForm.name.trim(),
        title: providerForm.title.trim() || null,
        specialty: providerForm.specialty.trim() || null,
      }),
    });
    if (response.ok) {
      setProviderForm({ name: '', title: '', specialty: '', active_status: true });
      await loadDashboard();
    }
  }

  async function handleDeleteProvider(providerId: string) {
    const response = await fetch(`${API_URL}/api/v1/providers/${providerId}`, {
      method: 'DELETE',
      headers: getAuthHeaders(),
    });
    if (response.ok) {
      await loadDashboard();
    }
  }

  async function handleCreateService(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const response = await fetch(`${API_URL}/api/v1/services`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
      body: JSON.stringify({
        ...serviceForm,
        name: serviceForm.name.trim(),
        description: serviceForm.description.trim() || null,
      }),
    });
    if (response.ok) {
      setServiceForm({ name: '', description: '', default_duration_minutes: 30, indicative_price: 0, currency: 'USD', active_status: true });
      await loadDashboard();
    }
  }

  async function handleDeleteService(serviceId: string) {
    const response = await fetch(`${API_URL}/api/v1/services/${serviceId}`, {
      method: 'DELETE',
      headers: getAuthHeaders(),
    });
    if (response.ok) {
      await loadDashboard();
    }
  }

  async function handleInsuranceSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!patients[0]?.id) {
      setInsuranceMessage('Add a patient before submitting insurance details.');
      return;
    }

    const response = await fetch(`${API_URL}/api/v1/patients/${patients[0].id}/insurance`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
      body: JSON.stringify({
        ...insuranceForm,
        member_name: insuranceForm.member_name || `${patients[0].first_name} ${patients[0].last_name}`,
      }),
    });

    if (response.ok) {
      setInsuranceForm({
        carrier_name: '',
        policy_number: '',
        group_number: '',
        member_name: '',
        subscriber_dob: '',
        relationship_to_patient: 'self',
        status: 'pending',
        notes: '',
      });
      setInsuranceMessage('Insurance intake saved.');
    } else {
      const error = await response.json();
      setInsuranceMessage(error.detail ?? 'Unable to save insurance intake');
    }
  }

  const selectedService = useMemo(
    () => services.find((service) => service.id === bookingForm.service_id),
    [bookingForm.service_id, services],
  );

  function handleLogout() {
    localStorage.removeItem('dentalvoice_token');
    router.push('/login');
  }

  const metrics = [
    { label: 'Appointments today', value: summary.appointments_today, icon: CalendarCheck2 },
    { label: 'Upcoming', value: summary.upcoming, icon: Activity },
    { label: 'Patients', value: summary.new_patients, icon: Users },
    { label: 'AI calls', value: summary.calls_handled, icon: MessageSquareText },
  ];

  const navItems = [
    { id: 'dashboard', label: 'Dashboard', icon: Activity },
    { id: 'patients', label: 'Patients', icon: Users },
    { id: 'appointments', label: 'Appointments', icon: CalendarCheck2 },
    { id: 'providers', label: 'Providers', icon: Users },
    { id: 'services', label: 'Services', icon: Activity },
    { id: 'insurance', label: 'Insurance', icon: MessageSquareText },
    { id: 'calls', label: 'Calls', icon: MessageSquareText },
    { id: 'staff', label: 'Staff', icon: Users },
    { id: 'settings', label: 'Settings', icon: Activity },
  ] as const;

  return (
    <div className="min-h-screen bg-[#e8ebf0] p-4 text-slate-900 md:p-6">
      <div className="mx-auto max-w-[1600px] overflow-hidden rounded-[28px] border border-[#dfe5ee] bg-[#f4f6fa] shadow-[0_20px_60px_rgba(15,23,42,0.08)]">
        <div className="flex min-h-[calc(100vh-48px)]">
          <aside className="w-[268px] shrink-0 border-r border-[#e7ebf1] bg-[#f3f5f8] p-4">
            <div className="mb-6 flex items-center gap-3 px-2 py-2">
              <div className="flex h-8 w-8 items-center justify-center rounded-full bg-[#0f172a] text-xs font-bold text-white">S</div>
              <div className="text-xl font-bold tracking-[-0.03em] text-slate-900">Shoopers</div>
            </div>

            <nav className="space-y-1.5">
              {navItems.map(({ id, label, icon: Icon }) => (
                <button
                  key={id}
                  type="button"
                  onClick={() => setActiveSection(id)}
                  className={`flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-left text-[15px] font-medium transition ${
                    activeSection === id
                      ? 'bg-[#eaf2ff] text-[#2563eb] shadow-[inset_0_0_0_1px_rgba(37,99,235,0.06)]'
                      : 'text-slate-600 hover:bg-white'
                  }`}
                >
                  <Icon size={16} className={activeSection === id ? 'text-[#2563eb]' : 'text-slate-500'} />
                  {label}
                </button>
              ))}
            </nav>

            <div className="mt-8 rounded-[22px] bg-[#0b7fdc] p-4 text-white shadow-[0_12px_25px_rgba(37,99,235,0.28)]">
              <div className="text-[11px] font-medium uppercase tracking-[0.18em] text-blue-100">Upgrade</div>
              <div className="mt-2 text-xl font-semibold">Premium</div>
              <button
                onClick={handleLogout}
                className="mt-4 flex w-full items-center justify-center gap-2 rounded-xl bg-white/15 px-3 py-2.5 text-sm font-semibold text-white hover:bg-white/20"
              >
                <LogOut size={15} />
                Log out
              </button>
            </div>
          </aside>

          <main className="flex-1 bg-[#f4f6fa] px-5 py-4">
            <header className="mb-5 flex items-center justify-between gap-4 rounded-[18px] border border-[#e5e7eb] bg-[#f8fafc] px-4 py-3 shadow-[0_1px_0_rgba(15,23,42,0.02)]">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-[#e5e7eb] bg-white text-slate-400">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="h-4 w-4">
                    <circle cx="11" cy="11" r="6" />
                    <path d="M16 16L21 21" />
                  </svg>
                </div>
                <div className="flex h-10 w-[360px] items-center gap-2 rounded-xl border border-[#e5e7eb] bg-white px-3 text-sm text-slate-500 shadow-sm">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="h-4 w-4 text-slate-400">
                    <circle cx="11" cy="11" r="6" />
                    <path d="M16 16L21 21" />
                  </svg>
                  <span>Search anything...</span>
                  <span className="ml-auto rounded-md border border-[#e5e7eb] bg-slate-50 px-1.5 py-0.5 text-[10px] font-semibold text-slate-500">⌘K</span>
                </div>
              </div>

              <div className="flex items-center gap-3">
                <button type="button" className="flex h-10 w-10 items-center justify-center rounded-full border border-[#e5e7eb] bg-white text-slate-500 transition hover:text-slate-700" aria-label="Settings">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="h-4 w-4">
                    <path d="M12 3v2.5M12 18.5V21M4.93 4.93l1.77 1.77M17.3 17.3l1.77 1.77M3 12h2.5M18.5 12H21M4.93 19.07l1.77-1.77M17.3 6.7l1.77-1.77" />
                    <circle cx="12" cy="12" r="3.5" />
                  </svg>
                </button>
                <button type="button" className="flex h-10 w-10 items-center justify-center rounded-full border border-[#e5e7eb] bg-white text-slate-500 transition hover:text-slate-700" aria-label="Notifications">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="h-4 w-4">
                    <path d="M15 17h5l-1.4-1.4A2 2 0 0 1 18 14.2V11a6 6 0 0 0-12 0v3.2a2 2 0 0 1-.6 1.4L4 17h5" />
                    <path d="M10 20a2 2 0 0 0 4 0" />
                  </svg>
                </button>
                <div className="flex h-10 w-10 items-center justify-center rounded-full bg-[#f0f4ff] text-sm font-semibold text-slate-700 ring-2 ring-white">A</div>
              </div>
            </header>

            {activeSection === 'dashboard' && (
            <>
              <section className="mb-6 grid gap-4 md:grid-cols-4">
                {metrics.map((metric) => (
                  <div key={metric.label} className="rounded-3xl bg-white p-5 shadow-sm ring-1 ring-slate-200">
                    <div className="mb-3 flex items-center justify-between text-slate-500">
                      <span className="text-sm">{metric.label}</span>
                      <metric.icon size={18} className="text-cyan-600" />
                    </div>
                    <div className="text-3xl font-bold">{metric.value}</div>
                  </div>
                ))}
              </section>

              <section className="mb-6 grid gap-6 lg:grid-cols-[1.5fr_1fr]">
                <div className="rounded-3xl bg-white p-5 shadow-sm ring-1 ring-slate-200">
                  <div className="mb-4 flex items-center justify-between">
                    <h2 className="text-xl font-semibold">Visit trends</h2>
                    <span className="rounded-full bg-cyan-50 px-3 py-1 text-xs font-medium text-cyan-600">Live</span>
                  </div>
                  <div className="flex h-40 items-end gap-3">
                    {analytics.appointment_trends.map((value, index) => (
                      <div key={index} className="flex flex-1 flex-col items-center gap-2">
                        <div className="w-full rounded-t-2xl bg-cyan-500/90" style={{ height: `${Math.max(18, value * 26)}px` }} />
                        <span className="text-[10px] text-slate-500">{index + 1}</span>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="rounded-3xl bg-white p-5 shadow-sm ring-1 ring-slate-200">
                  <h2 className="mb-4 text-xl font-semibold">Voice automation</h2>
                  <ul className="space-y-3 text-sm text-slate-600">
                    <li className="rounded-2xl bg-slate-50 p-3">Booked {analytics.call_outcomes.booked} conversations this week.</li>
                    <li className="rounded-2xl bg-slate-50 p-3">Missed calls: {analytics.call_outcomes.missed}.</li>
                    <li className="rounded-2xl bg-slate-50 p-3">Follow-up requests: {analytics.call_outcomes.follow_up}.</li>
                  </ul>
                </div>
              </section>

              <section className="grid gap-6 lg:grid-cols-[1.3fr_1fr]">
                <div className="rounded-3xl bg-white p-5 shadow-sm ring-1 ring-slate-200">
                  <h2 className="mb-4 text-xl font-semibold">Recent appointments</h2>
                  <div className="space-y-3">
                    {filteredAppointments.slice(0, 6).map((appointment) => (
                      <div key={appointment.id} className="flex items-center justify-between rounded-2xl bg-slate-50 p-3 text-sm text-slate-700">
                        <div>
                          <div>{new Date(appointment.start_time).toLocaleString()}</div>
                          <div className="mt-1 inline-block rounded-full bg-cyan-50 px-2 py-1 text-[10px] uppercase tracking-wide text-cyan-600">{appointment.status}</div>
                        </div>
                        <button type="button" onClick={() => handleUpdateAppointment(appointment.id, 'confirmed')} className="rounded-xl bg-emerald-600 px-3 py-2 text-xs font-medium text-white">Confirm</button>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="rounded-3xl bg-white p-5 shadow-sm ring-1 ring-slate-200">
                  <h2 className="mb-4 text-xl font-semibold">Operations queue</h2>
                  <div className="space-y-3">
                    {calls.slice(0, 5).map((call) => (
                      <div key={call.id} className="rounded-2xl bg-slate-50 p-3 text-sm text-slate-700">
                        <div className="flex items-center justify-between gap-3">
                          <span className="font-semibold text-slate-900">{call.caller_number ?? 'Unknown caller'}</span>
                          <span className="rounded-full bg-cyan-50 px-2 py-1 text-[10px] uppercase tracking-wide text-cyan-600">{call.outcome ?? call.status ?? 'new'}</span>
                        </div>
                        <div className="mt-1">{call.summary ?? 'No summary available.'}</div>
                      </div>
                    ))}
                  </div>
                </div>
              </section>
            </>
          )}

          {activeSection === 'patients' && (
            <div className="grid gap-6 xl:grid-cols-[0.9fr_1.1fr]">
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
                <div className="mb-4 flex items-center justify-between gap-3">
                  <h2 className="text-xl font-semibold">Patient directory</h2>
                  <input value={patientSearch} onChange={(event) => setPatientSearch(event.target.value)} placeholder="Search patient..." className="w-52 rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm outline-none" />
                </div>
                <div className="overflow-hidden rounded-2xl border border-slate-200">
                  <table className="min-w-full text-left text-sm">
                    <thead className="bg-slate-50 text-slate-600">
                      <tr>
                        <th className="px-4 py-3 font-medium">Name</th>
                        <th className="px-4 py-3 font-medium">Contact</th>
                        <th className="px-4 py-3 font-medium">Preferred</th>
                        <th className="px-4 py-3 font-medium">Action</th>
                      </tr>
                    </thead>
                    <tbody>
                      {filteredPatients.map((patient) => (
                        <tr key={patient.id} className="border-t border-slate-200">
                          <td className="px-4 py-3">{patient.first_name} {patient.last_name}</td>
                          <td className="px-4 py-3">{patient.email ?? patient.phone ?? '—'}</td>
                          <td className="px-4 py-3">{patient.preferred_contact_method ?? 'phone'}</td>
                          <td className="px-4 py-3">
                            <button type="button" onClick={() => handleDeletePatient(patient.id)} className="rounded-lg bg-rose-600 px-2 py-1 text-xs font-medium text-white">Delete</button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}

          {activeSection === 'appointments' && (
            <div className="grid gap-6 xl:grid-cols-[0.9fr_1.1fr]">
              <div className="rounded-3xl bg-white p-5 shadow-sm ring-1 ring-slate-200">
                <h2 className="mb-4 text-xl font-semibold">Schedule visit</h2>
                <form className="space-y-3" onSubmit={handleCreateAppointment}>
                  <select value={bookingForm.patient_id} onChange={(event) => setBookingForm({ ...bookingForm, patient_id: event.target.value })} className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 outline-none">
                    <option value="">Select patient</option>
                    {patients.map((patient) => <option key={patient.id} value={patient.id}>{patient.first_name} {patient.last_name}</option>)}
                  </select>
                  <div className="grid gap-3 md:grid-cols-2">
                    <select value={bookingForm.provider_id} onChange={(event) => setBookingForm({ ...bookingForm, provider_id: event.target.value })} className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 outline-none">
                      <option value="">Select provider</option>
                      {providers.map((provider) => <option key={provider.id} value={provider.id}>{provider.name}</option>)}
                    </select>
                    <select value={bookingForm.service_id} onChange={(event) => setBookingForm({ ...bookingForm, service_id: event.target.value })} className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 outline-none">
                      <option value="">Select service</option>
                      {services.map((service) => <option key={service.id} value={service.id}>{service.name}</option>)}
                    </select>
                  </div>
                  <input type="datetime-local" value={bookingForm.start_time} onChange={(event) => setBookingForm({ ...bookingForm, start_time: event.target.value })} className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 outline-none" />
                  <textarea value={bookingForm.notes} onChange={(event) => setBookingForm({ ...bookingForm, notes: event.target.value })} placeholder="Visit notes" rows={3} className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 outline-none" />
                  <button type="submit" className="rounded-xl bg-slate-900 px-4 py-2 font-medium text-white">Book appointment</button>
                  {bookingStatus ? <p className="text-sm text-slate-600">{bookingStatus}</p> : null}
                </form>
              </div>

              <div className="rounded-3xl bg-white p-5 shadow-sm ring-1 ring-slate-200">
                <div className="mb-4 flex items-center justify-between gap-3">
                  <h2 className="text-xl font-semibold">Appointment board</h2>
                  <input value={appointmentSearch} onChange={(event) => setAppointmentSearch(event.target.value)} placeholder="Search status/date" className="w-52 rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm outline-none" />
                </div>
                <div className="space-y-3">
                  {filteredAppointments.map((appointment) => (
                    <div key={appointment.id} className="flex items-center justify-between rounded-2xl bg-slate-50 p-3 text-sm text-slate-700">
                      <div>
                        <div>{new Date(appointment.start_time).toLocaleString()}</div>
                        <div className="mt-1 inline-block rounded-full bg-cyan-50 px-2 py-1 text-[10px] uppercase tracking-wide text-cyan-600">{appointment.status}</div>
                      </div>
                      <div className="flex gap-2">
                        <button type="button" onClick={() => handleUpdateAppointment(appointment.id, 'confirmed')} className="rounded-xl bg-emerald-600 px-3 py-2 text-xs font-medium text-white">Confirm</button>
                        <button type="button" onClick={() => handleDeleteAppointment(appointment.id)} className="rounded-xl bg-rose-600 px-3 py-2 text-xs font-medium text-white">Cancel</button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {activeSection === 'providers' && (
            <div className="grid gap-6 xl:grid-cols-[0.9fr_1.1fr]">
              <div className="rounded-3xl bg-white p-5 shadow-sm ring-1 ring-slate-200">
                <h2 className="mb-4 text-xl font-semibold">Add provider</h2>
                <form className="space-y-3" onSubmit={handleCreateProvider}>
                  <input value={providerForm.name} onChange={(event) => setProviderForm({ ...providerForm, name: event.target.value })} placeholder="Provider name" className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 outline-none" />
                  <input value={providerForm.title} onChange={(event) => setProviderForm({ ...providerForm, title: event.target.value })} placeholder="Title" className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 outline-none" />
                  <input value={providerForm.specialty} onChange={(event) => setProviderForm({ ...providerForm, specialty: event.target.value })} placeholder="Specialty" className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 outline-none" />
                  <button type="submit" className="rounded-xl bg-slate-900 px-4 py-2 font-medium text-white">Save provider</button>
                </form>
              </div>

              <div className="rounded-3xl bg-white p-5 shadow-sm ring-1 ring-slate-200">
                <div className="mb-4 flex items-center justify-between gap-3">
                  <h2 className="text-xl font-semibold">Provider directory</h2>
                  <input value={providerSearch} onChange={(event) => setProviderSearch(event.target.value)} placeholder="Search provider..." className="w-52 rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm outline-none" />
                </div>
                <div className="space-y-3">
                  {filteredProviders.map((provider) => (
                    <div key={provider.id} className="flex items-center justify-between rounded-2xl bg-slate-50 p-3 text-sm text-slate-700">
                      <div>
                        <div className="font-semibold text-slate-900">{provider.name}</div>
                        <div>{provider.title ?? 'Provider'} · {provider.specialty ?? 'General care'}</div>
                      </div>
                      <button type="button" onClick={() => handleDeleteProvider(provider.id)} className="rounded-xl bg-rose-600 px-3 py-2 text-xs font-medium text-white">Delete</button>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {activeSection === 'services' && (
            <div className="grid gap-6 xl:grid-cols-[0.9fr_1.1fr]">
              <div className="rounded-3xl bg-white p-5 shadow-sm ring-1 ring-slate-200">
                <h2 className="mb-4 text-xl font-semibold">Add service</h2>
                <form className="space-y-3" onSubmit={handleCreateService}>
                  <input value={serviceForm.name} onChange={(event) => setServiceForm({ ...serviceForm, name: event.target.value })} placeholder="Service name" className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 outline-none" />
                  <textarea value={serviceForm.description} onChange={(event) => setServiceForm({ ...serviceForm, description: event.target.value })} placeholder="Description" rows={3} className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 outline-none" />
                  <div className="grid gap-3 md:grid-cols-2">
                    <input type="number" value={serviceForm.default_duration_minutes} onChange={(event) => setServiceForm({ ...serviceForm, default_duration_minutes: Number(event.target.value) })} placeholder="Duration minutes" className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 outline-none" />
                    <input type="number" step="0.01" value={serviceForm.indicative_price} onChange={(event) => setServiceForm({ ...serviceForm, indicative_price: Number(event.target.value) })} placeholder="Price" className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 outline-none" />
                  </div>
                  <button type="submit" className="rounded-xl bg-slate-900 px-4 py-2 font-medium text-white">Save service</button>
                </form>
              </div>

              <div className="rounded-3xl bg-white p-5 shadow-sm ring-1 ring-slate-200">
                <div className="mb-4 flex items-center justify-between gap-3">
                  <h2 className="text-xl font-semibold">Service catalog</h2>
                  <input value={serviceSearch} onChange={(event) => setServiceSearch(event.target.value)} placeholder="Search service..." className="w-52 rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm outline-none" />
                </div>
                <div className="space-y-3">
                  {filteredServices.map((service) => (
                    <div key={service.id} className="flex items-center justify-between rounded-2xl bg-slate-50 p-3 text-sm text-slate-700">
                      <div>
                        <div className="font-semibold text-slate-900">{service.name}</div>
                        <div>{service.description ?? 'No description'}</div>
                        <div className="mt-1 text-xs uppercase tracking-wide text-slate-500">{service.default_duration_minutes} min · ${service.indicative_price}</div>
                      </div>
                      <button type="button" onClick={() => handleDeleteService(service.id)} className="rounded-xl bg-rose-600 px-3 py-2 text-xs font-medium text-white">Delete</button>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {activeSection === 'insurance' && (
            <div className="rounded-3xl bg-white p-5 shadow-sm ring-1 ring-slate-200">
              <h2 className="mb-4 text-xl font-semibold">Insurance intake</h2>
              <form className="space-y-3" onSubmit={handleInsuranceSubmit}>
                <input value={insuranceForm.carrier_name} onChange={(event) => setInsuranceForm({ ...insuranceForm, carrier_name: event.target.value })} placeholder="Carrier name" className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 outline-none" />
                <div className="grid gap-3 md:grid-cols-2">
                  <input value={insuranceForm.policy_number} onChange={(event) => setInsuranceForm({ ...insuranceForm, policy_number: event.target.value })} placeholder="Policy number" className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 outline-none" />
                  <input value={insuranceForm.group_number} onChange={(event) => setInsuranceForm({ ...insuranceForm, group_number: event.target.value })} placeholder="Group number" className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 outline-none" />
                </div>
                <div className="grid gap-3 md:grid-cols-2">
                  <input value={insuranceForm.member_name} onChange={(event) => setInsuranceForm({ ...insuranceForm, member_name: event.target.value })} placeholder="Member name" className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 outline-none" />
                  <input value={insuranceForm.subscriber_dob} onChange={(event) => setInsuranceForm({ ...insuranceForm, subscriber_dob: event.target.value })} type="date" className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 outline-none" />
                </div>
                <input value={insuranceForm.relationship_to_patient} onChange={(event) => setInsuranceForm({ ...insuranceForm, relationship_to_patient: event.target.value })} placeholder="Relationship to patient" className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 outline-none" />
                <textarea value={insuranceForm.notes} onChange={(event) => setInsuranceForm({ ...insuranceForm, notes: event.target.value })} placeholder="Insurance notes" rows={4} className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 outline-none" />
                <button type="submit" className="rounded-xl bg-slate-900 px-4 py-2 font-medium text-white">Save insurance</button>
                {insuranceMessage ? <p className="text-sm text-slate-600">{insuranceMessage}</p> : null}
              </form>
            </div>
          )}

          {activeSection === 'calls' && (
            <div className="rounded-3xl bg-white p-5 shadow-sm ring-1 ring-slate-200">
              <h2 className="mb-4 text-xl font-semibold">Call center log</h2>
              <div className="space-y-3">
                {calls.map((call) => (
                  <div key={call.id} className="rounded-2xl bg-slate-50 p-4 text-sm text-slate-700">
                    <div className="flex items-center justify-between gap-3">
                      <div className="font-semibold text-slate-900">{call.caller_number ?? 'Unknown caller'}</div>
                      <span className="rounded-full bg-cyan-50 px-2 py-1 text-[10px] uppercase tracking-wide text-cyan-600">{call.outcome ?? call.status}</span>
                    </div>
                    <div className="mt-1">{call.summary ?? 'No summary available.'}</div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {activeSection === 'staff' && (
            <div className="rounded-3xl bg-white p-5 shadow-sm ring-1 ring-slate-200">
              <h2 className="mb-4 text-xl font-semibold">Clinic staff</h2>
              <div className="space-y-3">
                {staff.map((member) => (
                  <div key={member.id} className="flex items-center justify-between rounded-2xl bg-slate-50 p-4 text-sm text-slate-700">
                    <div>
                      <div className="font-semibold text-slate-900">{member.full_name}</div>
                      <div>{member.email ?? 'No email'}</div>
                    </div>
                    <span className="rounded-full bg-slate-200 px-2 py-1 text-[10px] uppercase tracking-wide text-slate-700">{member.role ?? 'staff'}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {activeSection === 'settings' && (
            <div className="rounded-3xl bg-white p-5 shadow-sm ring-1 ring-slate-200">
              <h2 className="mb-4 text-xl font-semibold">Management settings</h2>
              <div className="space-y-4 text-sm text-slate-700">
                <div className="rounded-2xl bg-slate-50 p-4">
                  <div className="font-semibold text-slate-900">Clinic configuration</div>
                  <div className="mt-2">Business hours, cancellations, and intake policies are managed centrally from the backend APIs.</div>
                </div>
                <div className="rounded-2xl bg-slate-50 p-4">
                  <div className="font-semibold text-slate-900">Automation rules</div>
                  <div className="mt-2">Retell AI booking, follow-up routing, and manual overrides are supported by the management backend.</div>
                </div>
              </div>
            </div>
          )}
          </main>
        </div>
      </div>
    </div>
  );
}
