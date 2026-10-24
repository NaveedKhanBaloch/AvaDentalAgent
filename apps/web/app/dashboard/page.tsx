"use client";
import Patients from '../../features/phase2/Patients';
import Tasks from '../../features/phase2/Tasks';
import Estimates from '../../features/phase2/Estimates';
import Metrics from '../../features/phase2/Metrics';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { Activity, CalendarCheck2, LogOut, MessageSquareText, MoonStar, SunMedium, Users } from 'lucide-react';
import { useRouter } from 'next/navigation';

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000';

type Summary = {
  appointments_today: number;
  upcoming: number;
  pending_confirmations: number;
  cancelled: number;
  new_patients: number;
  calls_handled: number;
  missed_calls: number;
  follow_up_requests: number;
  ai_bookings?: number;
  unresolved_calls?: number;
  rescheduled?: number;
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
  patient_id?: string;
  service_id?: string;
  provider_id?: string;
  source?: string;
  timezone?: string;
  end_time?: string;
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
  appointment_id?: string | null;
  escalation_status?: string | null;
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
  const [theme, setTheme] = useState<'light' | 'dark'>(() => {
    if (typeof window === 'undefined') {
      return 'light';
    }

    const storedTheme = window.localStorage.getItem('dental_dashboard_theme');
    if (storedTheme === 'light' || storedTheme === 'dark') {
      return storedTheme;
    }

    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  });

  useEffect(() => {
    document.documentElement.style.colorScheme = theme;
    document.documentElement.classList.toggle('dark', theme === 'dark');
    window.localStorage.setItem('dental_dashboard_theme', theme);
  }, [theme]);

  const isDark = theme === 'dark';

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
  const [editingAppointment, setEditingAppointment] = useState<string | null>(null);
  const [loadError, setLoadError] = useState('');
  const [availabilityDate, setAvailabilityDate] = useState('');
  const [availableSlots, setAvailableSlots] = useState<{start_time: string; end_time: string; provider_id: string; service_id?: string}[]>([]);
  const [selectedSlot, setSelectedSlot] = useState<{start_time: string; end_time: string; provider_id: string; service_id?: string} | null>(null);
  const [clinicTimezone, setClinicTimezone] = useState('');
  const [appointmentHistory, setAppointmentHistory] = useState<{action: string; timestamp: string; actor_type: string}[]>([]);
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
  const [insurancePatientId, setInsurancePatientId] = useState('');
  const [bookingPatientSearch, setBookingPatientSearch] = useState('');
  const [insuranceMessage, setInsuranceMessage] = useState('');
  const [phase2Permissions, setPhase2Permissions] = useState<string[]>([]);
  const [activeSection, setActiveSection] = useState<'dashboard' | 'patients' | 'appointments' | 'providers' | 'services' | 'insurance' | 'calls' | 'staff' | 'settings' | 'follow-ups' | 'recalls' | 'estimates'>('dashboard');
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
      fetch(`${API_URL}/api/v1/dashboard/summary`, { headers: getAuthHeaders() }),
      fetch(`${API_URL}/api/v1/dashboard/analytics`, { headers: getAuthHeaders() }),
      fetch(`${API_URL}/api/v1/patients`, { headers: getAuthHeaders() }),
      fetch(`${API_URL}/api/v1/appointments`, { headers: getAuthHeaders() }),
      fetch(`${API_URL}/api/v1/providers`, { headers: getAuthHeaders() }),
      fetch(`${API_URL}/api/v1/services`, { headers: getAuthHeaders() }),
      fetch(`${API_URL}/api/v1/staff`, { headers: getAuthHeaders() }),
      fetch(`${API_URL}/api/v1/operations/calls`, { headers: getAuthHeaders() }),
      fetch(`${API_URL}/api/v1/operations/follow-ups`, { headers: getAuthHeaders() }),
    ]);

    const responses = [summaryRes, analyticsRes, patientsRes, appointmentsRes, providersRes, servicesRes, staffRes, callsRes, followUpsRes];
    if (responses.some((response) => response.status === 401)) {
      router.push('/login');
      return;
    }
    setLoadError(responses.some((response) => !response.ok) ? 'Some clinic data could not be loaded. Please refresh to retry.' : '');
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
    const section=new URLSearchParams(window.location.search).get('section');if(section && ['patients','follow-ups','recalls','estimates','appointments','calls'].includes(section))setActiveSection(section as 'patients'|'follow-ups'|'recalls'|'estimates'|'appointments'|'calls');
    fetch(`${API_URL}/api/v1/operations/capabilities`,{headers:getAuthHeaders()}).then(r=>r.json()).then(d=>setPhase2Permissions(d.permissions??[])).catch(()=>{});
    void loadDashboard().catch(() => setLoadError('Unable to connect to the clinic system. Please refresh to retry.'));
  }, [loadDashboard]);

  async function checkAvailability() {
    if (!availabilityDate || !bookingForm.provider_id || !bookingForm.service_id) {
      setBookingStatus('Select a date, provider and service.');
      return;
    }
    setSelectedSlot(null);
    setAvailableSlots([]);
    try {
      const response = await fetch(`${API_URL}/api/v1/appointments/availability`, {
        method: 'POST', headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
        body: JSON.stringify({preferred_date: availabilityDate, provider_id: bookingForm.provider_id, service_id: bookingForm.service_id}),
      });
      const data = await response.json();
      if (!response.ok) { setBookingStatus(data.detail ?? 'Availability could not be loaded.'); return; }
      setAvailableSlots((data.slots ?? []).map((slot: {start_time: string; end_time: string; provider_id: string}) => ({...slot, service_id: bookingForm.service_id})));
      setClinicTimezone(data.timezone ?? '');
      setBookingStatus(data.slots?.length ? 'Select an available time.' : 'No available times for this provider and date.');
    } catch { setBookingStatus('Availability could not be loaded. Please retry.'); }
  }

  function rescheduleAppointment(appointment: AppointmentRow) {
    setEditingAppointment(appointment.id);
    setBookingForm({patient_id: appointment.patient_id ?? '', provider_id: appointment.provider_id ?? '', service_id: appointment.service_id ?? '', start_time: '', notes: ''});
    setSelectedSlot(null);
    setAvailableSlots([]);
    setBookingStatus('Choose and confirm a new time for this appointment.');
  }

  async function showHistory(id: string) {
    try {
      const response = await fetch(`${API_URL}/api/v1/appointments/${id}/history`, {headers: getAuthHeaders()});
      if (!response.ok) { setBookingStatus('Booking history could not be loaded.'); return; }
      setAppointmentHistory((await response.json()).items ?? []);
    } catch { setBookingStatus('Booking history could not be loaded.'); }
  }

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

    if (selectedSlot && (selectedSlot.provider_id !== bookingForm.provider_id || selectedSlot.service_id !== bookingForm.service_id)) {
      setBookingStatus('Provider or service changed. Please check availability again.');
      return;
    }
    const service = services.find((item) => item.id === bookingForm.service_id);
    const start = new Date(selectedSlot?.start_time ?? bookingForm.start_time);
    const durationMs = ((service?.default_duration_minutes ?? 30) * 60 * 1000);
    const payload = {
      patient_id: bookingForm.patient_id,
      provider_id: bookingForm.provider_id,
      service_id: bookingForm.service_id,
      start_time: selectedSlot?.start_time ?? start.toISOString(),
      end_time: selectedSlot?.end_time ?? new Date(start.getTime() + durationMs).toISOString(),
      ...(!editingAppointment ? {status: 'scheduled', source: 'dashboard'} : {}),
      notes: bookingForm.notes,
    };

    const response = await fetch(`${API_URL}/api/v1/appointments${editingAppointment ? `/${editingAppointment}` : ''}`, {
      method: editingAppointment ? 'PATCH' : 'POST',
      headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
      body: JSON.stringify(payload),
    });

    if (response.ok) {
      setBookingForm({ ...defaultBookingForm, provider_id: providers[0]?.id ?? '', service_id: services[0]?.id ?? '' });
      setBookingStatus(editingAppointment ? 'Appointment rescheduled successfully.' : 'Appointment scheduled successfully.');
      setEditingAppointment(null);
      setSelectedSlot(null);
      setAvailableSlots([]);
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
    if (!insurancePatientId) {
      setInsuranceMessage('Select a patient before submitting insurance details.');
      return;
    }

    const response = await fetch(`${API_URL}/api/v1/patients/${insurancePatientId}/insurance`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
      body: JSON.stringify({
        ...insuranceForm,
        member_name: insuranceForm.member_name || `${patients.find(p=>p.id===insurancePatientId)?.first_name ?? ''} ${patients.find(p=>p.id===insurancePatientId)?.last_name ?? ''}`,
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
    { id: 'estimates', label: 'Estimates', icon: CalendarCheck2 },
    { id: 'follow-ups', label: 'Follow-ups', icon: MessageSquareText },
    { id: 'recalls', label: 'Recalls', icon: CalendarCheck2 },
    { id: 'insurance', label: 'Insurance', icon: MessageSquareText },
    { id: 'calls', label: 'Calls', icon: MessageSquareText },
    { id: 'staff', label: 'Staff', icon: Users },
    { id: 'settings', label: 'Settings', icon: Activity },
  ] as const;

  return (
    <div className={`dashboard-shell min-h-screen p-4 md:p-6 ${isDark ? 'dark bg-slate-950 text-slate-100' : 'bg-[#e8ebf0] text-slate-900'}`}>
      <div className={`mx-auto max-w-[1600px] overflow-hidden rounded-[28px] border shadow-[0_20px_60px_rgba(15,23,42,0.08)] ${isDark ? 'border-slate-800 bg-slate-950' : 'border-[#dfe5ee] bg-[#f4f6fa]'}`}>
        <div className={`flex flex-col md:flex-row min-h-[calc(100vh-48px)] ${isDark ? 'bg-slate-950' : 'bg-[#f4f6fa]'}`}>
          <aside className={`w-full md:w-[268px] shrink-0 border-b md:border-b-0 md:border-r p-4 ${isDark ? 'border-slate-800 bg-[#111827] text-slate-100' : 'border-[#e7ebf1] bg-[#f3f5f8] text-slate-900'}`}>
            <div className="mb-2 md:mb-6 flex items-center gap-3 px-2 py-2">
              <div className={`flex h-8 w-8 items-center justify-center rounded-full text-xs font-bold ${isDark ? 'bg-cyan-500/20 text-cyan-300' : 'bg-[#0f172a] text-white'}`}>A</div>
              <div className={`text-xl font-bold tracking-[-0.03em] ${isDark ? 'text-white' : 'text-slate-900'}`}>Ava Dental</div>
            </div>

            <nav aria-label="Dashboard sections" className="grid grid-cols-2 gap-1.5 md:block md:space-y-1.5">
              {navItems.filter(item=>item.id!=='estimates'||phase2Permissions.includes('estimate_read')).map(({ id, label, icon: Icon }) => (
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

            <div className="hidden md:block mt-8 rounded-[22px] bg-[#0b7fdc] p-4 text-white shadow-[0_12px_25px_rgba(37,99,235,0.28)]">
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
            <button className="mt-3 md:hidden rounded-xl border px-3 py-2 text-sm" onClick={handleLogout}>Log out</button>
          </aside>

          <main className="min-w-0 flex-1 bg-[#f4f6fa] px-3 md:px-5 py-4">
            <header className={`mb-5 flex items-center justify-between gap-4 rounded-[18px] border px-4 py-3 shadow-[0_1px_0_rgba(15,23,42,0.02)] ${isDark ? 'border-slate-800 bg-slate-900' : 'border-[#e5e7eb] bg-[#f8fafc]'}`}>
              <div className="flex items-center gap-3">
                <div className={`flex h-10 w-10 items-center justify-center rounded-xl border ${isDark ? 'border-slate-700 bg-slate-800 text-slate-400' : 'border-[#e5e7eb] bg-white text-slate-400'}`}>
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="h-4 w-4">
                    <circle cx="11" cy="11" r="6" />
                    <path d="M16 16L21 21" />
                  </svg>
                </div>
<div className={`hidden xl:flex h-10 w-[360px] items-center gap-2 rounded-xl border px-3 text-sm shadow-sm ${isDark ? 'border-slate-700 bg-slate-800 text-slate-300' : 'border-[#e5e7eb] bg-white text-slate-500'}`}>
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className={`h-4 w-4 ${isDark ? 'text-slate-400' : 'text-slate-400'}`}>
                    <circle cx="11" cy="11" r="6" />
                    <path d="M16 16L21 21" />
                  </svg>
                  <span>Search anything...</span>
                  <span className={`ml-auto rounded-md border px-1.5 py-0.5 text-[10px] font-semibold ${isDark ? 'border-slate-700 bg-slate-900 text-slate-300' : 'border-[#e5e7eb] bg-slate-50 text-slate-500'}`}>⌘K</span>
                </div>
              </div>

              <div className="flex items-center gap-3">
                <button
                  type="button"
                  onClick={() => setTheme(isDark ? 'light' : 'dark')}
                  className={`flex h-10 w-10 items-center justify-center rounded-full border transition ${isDark ? 'border-slate-700 bg-slate-800 text-slate-200 hover:text-white' : 'border-[#e5e7eb] bg-white text-slate-500 hover:text-slate-700'}`}
                  aria-label="Toggle dashboard theme"
                  title={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
                >
                  {isDark ? <SunMedium className="h-4 w-4" /> : <MoonStar className="h-4 w-4" />}
                </button>
                <button type="button" className={`flex h-10 w-10 items-center justify-center rounded-full border transition ${isDark ? 'border-slate-700 bg-slate-800 text-slate-200 hover:text-white' : 'border-[#e5e7eb] bg-white text-slate-500 hover:text-slate-700'}`} aria-label="Notifications">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="h-4 w-4">
                    <path d="M15 17h5l-1.4-1.4A2 2 0 0 1 18 14.2V11a6 6 0 0 0-12 0v3.2a2 2 0 0 1-.6 1.4L4 17h5" />
                    <path d="M10 20a2 2 0 0 0 4 0" />
                  </svg>
                </button>
                <div className={`flex h-10 w-10 items-center justify-center rounded-full text-sm font-semibold ring-2 ring-white ${isDark ? 'bg-[#f0f4ff] text-slate-700' : 'bg-[#f0f4ff] text-slate-700'}`}>A</div>
              </div>
            </header>

            {activeSection === 'dashboard' && (
            <>
              <Metrics />
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
                      <div key={appointment.id} data-testid={`appointment-${appointment.id}`} className="flex items-center justify-between rounded-2xl bg-slate-50 p-3 text-sm text-slate-700">
                        <div>
                          <div>{new Date(appointment.start_time).toLocaleString([], {timeZone: appointment.timezone})} {appointment.timezone}</div>
                        <div className="text-xs">{providers.find((p) => p.id === appointment.provider_id)?.name ?? 'Provider unavailable'} · {appointment.source ?? 'Unknown source'}</div>
                          <div className="mt-1 inline-block rounded-full bg-cyan-50 px-2 py-1 text-[10px] uppercase tracking-wide text-cyan-600">{appointment.status}</div>
                        </div>
                        <button type="button" disabled={appointment.status !== 'scheduled'} onClick={() => handleUpdateAppointment(appointment.id, 'confirmed')} className="rounded-xl bg-emerald-600 px-3 py-2 text-xs font-medium text-white disabled:opacity-40 disabled:cursor-not-allowed">Confirm</button>
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
                        {call.appointment_id && <div className="mt-1 text-xs">Appointment: {call.appointment_id}</div>}
                    {call.escalation_status && <div className="mt-1 font-medium">Human assistance: {call.escalation_status}</div>}
                    <div className="mt-1">{call.summary ?? 'No summary available.'}</div>
                      </div>
                    ))}
                  </div>
                </div>
              </section>
            </>
          )}

          {loadError && <p role="alert" className="mb-4 rounded-xl bg-rose-50 p-3 text-rose-700">{loadError}</p>}
          {activeSection === 'patients' && <Patients />}
          {activeSection === 'estimates' && <Estimates />}
          {activeSection === 'follow-ups' && <Tasks key="follow-ups" kind="follow-ups" />}
          {activeSection === 'recalls' && <Tasks key="recalls" kind="recalls" />}

          {activeSection === 'appointments' && (
            <div className="grid gap-6 xl:grid-cols-[0.9fr_1.1fr]">
              <div className="rounded-3xl bg-white p-5 shadow-sm ring-1 ring-slate-200">
                <h2 className="mb-4 text-xl font-semibold">{editingAppointment ? 'Reschedule visit' : 'Schedule visit'}</h2>
                <form className="space-y-3" onSubmit={handleCreateAppointment}>
                  <label>Find patient<input className="w-full rounded-xl border p-2" value={bookingPatientSearch} onChange={async e=>{const value=e.target.value;setBookingPatientSearch(value);try{const response=await fetch(`${API_URL}/api/v1/patients?search=${encodeURIComponent(value)}&status=active&page_size=100`,{headers:getAuthHeaders()});if(response.ok)setPatients((await response.json()).items);}catch{setBookingStatus('Patient search unavailable.')}}}/></label>
                  <select aria-label="Booking patient" value={bookingForm.patient_id} onChange={(event) => setBookingForm({ ...bookingForm, patient_id: event.target.value })} className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 outline-none">
                    <option value="">Select patient</option>
                    {patients.map((patient) => <option key={patient.id} value={patient.id}>{patient.first_name} {patient.last_name}</option>)}
                  </select>
                  <div className="grid gap-3 md:grid-cols-2">
                    <select value={bookingForm.provider_id} onChange={(event) => {setSelectedSlot(null); setAvailableSlots([]); setBookingForm({ ...bookingForm, provider_id: event.target.value });}} className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 outline-none">
                      <option value="">Select provider</option>
                      {providers.map((provider) => <option key={provider.id} value={provider.id}>{provider.name}</option>)}
                    </select>
                    <select value={bookingForm.service_id} onChange={(event) => {setSelectedSlot(null); setAvailableSlots([]); setBookingForm({ ...bookingForm, service_id: event.target.value });}} className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 outline-none">
                      <option value="">Select service</option>
                      {services.map((service) => <option key={service.id} value={service.id}>{service.name}</option>)}
                    </select>
                  </div>
                  <label className="block text-sm">Check clinic availability
                    <input aria-label="Appointment date" type="date" value={availabilityDate} onChange={(event) => {setAvailabilityDate(event.target.value); setSelectedSlot(null); setAvailableSlots([]);}} className="mt-1 w-full rounded-xl border border-slate-200 px-3 py-2" />
                  </label>
                  <button type="button" onClick={checkAvailability} className="rounded-xl bg-cyan-700 px-4 py-2 text-white">Check availability</button>
                  {clinicTimezone && <p className="text-sm">Clinic timezone: {clinicTimezone}</p>}
                  <div className="flex flex-wrap gap-2">{availableSlots.map((slot) => <button type="button" key={slot.start_time} aria-pressed={selectedSlot?.start_time === slot.start_time} onClick={() => {setSelectedSlot(slot); setBookingForm({...bookingForm, start_time: new Date(new Date(slot.start_time).getTime() - new Date(slot.start_time).getTimezoneOffset()*60000).toISOString().slice(0,16)});}} className={`rounded-lg border px-3 py-2 text-sm ${selectedSlot?.start_time === slot.start_time ? 'bg-cyan-700 text-white' : 'bg-slate-50'}`}>{new Date(slot.start_time).toLocaleTimeString([], {timeZone: clinicTimezone || undefined, hour: '2-digit', minute: '2-digit'})} ({slot.start_time.slice(-6)})</button>)}</div>
                  <label className="block text-sm">Manual time (your device timezone: {Intl.DateTimeFormat().resolvedOptions().timeZone})</label>
                  <input aria-label="Manual appointment time" type="datetime-local" value={bookingForm.start_time} onChange={(event) => {setSelectedSlot(null); setBookingForm({ ...bookingForm, start_time: event.target.value });}} className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 outline-none" />
                  <textarea value={bookingForm.notes} onChange={(event) => setBookingForm({ ...bookingForm, notes: event.target.value })} placeholder="Visit notes" rows={3} className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 outline-none" />
                  <button type="submit" className="rounded-xl bg-slate-900 px-4 py-2 font-medium text-white">{editingAppointment ? 'Save reschedule' : 'Book appointment'}</button>
                  {editingAppointment && <button type="button" onClick={() => {setEditingAppointment(null); setBookingForm(defaultBookingForm); setSelectedSlot(null);}}>Cancel editing</button>}
                  {bookingStatus ? <p className="text-sm text-slate-600">{bookingStatus}</p> : null}
                </form>
              </div>

              <div className="rounded-3xl bg-white p-5 shadow-sm ring-1 ring-slate-200">
                <div className="mb-4 flex items-center justify-between gap-3">
                  <h2 className="text-xl font-semibold">Appointment board</h2>
                  <input value={appointmentSearch} onChange={(event) => setAppointmentSearch(event.target.value)} placeholder="Search status/date" className="w-52 rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm outline-none" />
                </div>
                <div className="space-y-3">
                  {filteredAppointments.length === 0 && <p>No appointments match the current filter.</p>}
                  {appointmentHistory.length > 0 && <div aria-live="polite" className="rounded-xl border p-3 text-sm"><button type="button" onClick={() => setAppointmentHistory([])}>Close history</button>{appointmentHistory.map((entry, i) => <p key={i}>{entry.action} · {entry.actor_type} · {new Date(entry.timestamp).toLocaleString()}</p>)}</div>}
                  {filteredAppointments.map((appointment) => (
                    <div key={appointment.id} data-testid={`appointment-${appointment.id}`} className="flex items-center justify-between rounded-2xl bg-slate-50 p-3 text-sm text-slate-700">
                      <div>
                        <div>{new Date(appointment.start_time).toLocaleString([], {timeZone: appointment.timezone})} {appointment.timezone}</div>
                        <div className="text-xs">{providers.find((p) => p.id === appointment.provider_id)?.name ?? 'Provider unavailable'} · {appointment.source ?? 'Unknown source'}</div>
                        <div className="mt-1 inline-block rounded-full bg-cyan-50 px-2 py-1 text-[10px] uppercase tracking-wide text-cyan-600">{appointment.status}</div>
                      </div>
                      <div className="flex flex-wrap gap-2">
                        <button type="button" disabled={['completed','cancelled','no_show'].includes(appointment.status)} onClick={() => rescheduleAppointment(appointment)} className="rounded-xl border px-3 py-2 text-xs disabled:opacity-40 disabled:cursor-not-allowed">Reschedule</button>
                        <button type="button" onClick={() => showHistory(appointment.id)} className="rounded-xl border px-3 py-2 text-xs">History</button>
                        <button type="button" disabled={appointment.status !== 'scheduled'} onClick={() => handleUpdateAppointment(appointment.id, 'confirmed')} className="rounded-xl bg-emerald-600 px-3 py-2 text-xs font-medium text-white disabled:opacity-40 disabled:cursor-not-allowed">Confirm</button>
                        <button type="button" disabled={['completed', 'cancelled', 'no_show'].includes(appointment.status)} onClick={() => handleDeleteAppointment(appointment.id)} className="rounded-xl bg-rose-600 px-3 py-2 text-xs font-medium text-white disabled:opacity-40 disabled:cursor-not-allowed">Cancel</button>
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
                <label>Patient<select className="w-full rounded-xl border p-2" required value={insurancePatientId} onChange={e=>setInsurancePatientId(e.target.value)}><option value="">Select patient</option>{patients.map(p=><option key={p.id} value={p.id}>{p.first_name} {p.last_name}</option>)}</select></label>
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
              <p className="mb-4 text-sm">AI bookings: {summary.ai_bookings ?? 0} · Unresolved calls: {summary.unresolved_calls ?? 0} · Rescheduled: {summary.rescheduled ?? 0}</p>
              <div className="space-y-3">
                {calls.length === 0 && <p>No call records yet.</p>}
                {calls.map((call) => (
                  <div key={call.id} className="rounded-2xl bg-slate-50 p-4 text-sm text-slate-700">
                    <div className="flex items-center justify-between gap-3">
                      <div className="font-semibold text-slate-900">{call.caller_number ?? 'Unknown caller'}</div>
                      <span className="rounded-full bg-cyan-50 px-2 py-1 text-[10px] uppercase tracking-wide text-cyan-600">{call.status ?? 'Unknown status'} · {call.outcome ?? 'Outcome pending'}</span>
                    </div>
                    {call.appointment_id && <div className="mt-1 text-xs">Appointment: {call.appointment_id}</div>}
                    {call.escalation_status && <div className="mt-1 font-medium">Human assistance: {call.escalation_status}</div>}
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
