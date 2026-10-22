import Link from 'next/link';
import { ArrowRight, CalendarDays, MessageSquareText, ShieldCheck, Stethoscope } from 'lucide-react';

export default function HomePage() {
  return (
    <main className="min-h-screen bg-slate-100 text-slate-900">
      <div className="mx-auto max-w-6xl px-6 py-10">
        <header className="mb-8 flex items-center justify-between rounded-full border border-slate-200 bg-white px-5 py-3 shadow-sm">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-full bg-brand-600 text-sm font-semibold text-white">A</div>
            <div>
              <div className="text-sm font-bold text-slate-900">DentalVoice AI</div>
              <div className="text-xs text-slate-500">Harbor Dental Demo</div>
            </div>
          </div>
          <Link href="/login" className="inline-flex items-center gap-2 rounded-full bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-500">
            Staff login <ArrowRight size={16} />
          </Link>
        </header>

        <section className="grid gap-8 rounded-3xl bg-white p-8 shadow-sm md:grid-cols-2 md:p-12">
          <div>
            <span className="mb-4 inline-flex rounded-full bg-brand-50 px-3 py-1 text-xs font-semibold uppercase tracking-[0.2em] text-brand-600">
              Multi-tenant dental SaaS
            </span>
            <h1 className="mb-4 text-4xl font-bold tracking-tight text-slate-900 md:text-5xl">
              AI-powered front desk for modern dental clinics.
            </h1>
            <p className="mb-6 max-w-xl text-lg text-slate-600">
              Manage patients, appointments, scheduling rules, and AI receptionist workflows from one secure dashboard built for dental practices.
            </p>
            <div className="flex flex-wrap gap-4">
              <Link href="/login" className="rounded-full bg-slate-900 px-5 py-3 font-medium text-white hover:bg-slate-800">
                Access dashboard
              </Link>
              <Link href="/dashboard" className="rounded-full border border-slate-200 px-5 py-3 font-medium text-slate-700 hover:bg-slate-50">
                Preview demo
              </Link>
            </div>
          </div>
          <div className="grid gap-4 rounded-2xl bg-slate-50 p-5">
            <div className="rounded-2xl bg-white p-4 shadow-sm">
              <div className="mb-2 flex items-center justify-between text-sm text-slate-500">
                <span>Appointments today</span>
                <CalendarDays className="text-brand-600" size={18} />
              </div>
              <div className="text-3xl font-bold text-slate-900">24</div>
            </div>
            <div className="rounded-2xl bg-white p-4 shadow-sm">
              <div className="mb-2 flex items-center justify-between text-sm text-slate-500">
                <span>AI calls handled</span>
                <MessageSquareText className="text-brand-600" size={18} />
              </div>
              <div className="text-3xl font-bold text-slate-900">18</div>
            </div>
            <div className="rounded-2xl bg-white p-4 shadow-sm">
              <div className="mb-2 flex items-center justify-between text-sm text-slate-500">
                <span>Compliance & security</span>
                <ShieldCheck className="text-brand-600" size={18} />
              </div>
              <div className="text-3xl font-bold text-slate-900">Active</div>
            </div>
          </div>
        </section>

        <section className="mt-10 grid gap-6 md:grid-cols-4">
          {[
            { icon: Stethoscope, title: 'Patient care', text: 'Track patient records and treatment history.' },
            { icon: CalendarDays, title: 'Smart scheduling', text: 'Availability and conflict checks built in.' },
            { icon: MessageSquareText, title: 'AI receptionist', text: 'Retell-ready appointment and follow-up flows.' },
            { icon: ShieldCheck, title: 'Secure access', text: 'Role-based access and tenant isolation.' },
          ].map((item) => (
            <div key={item.title} className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
              <item.icon className="mb-3 text-brand-600" size={20} />
              <h3 className="mb-2 font-semibold text-slate-900">{item.title}</h3>
              <p className="text-sm text-slate-600">{item.text}</p>
            </div>
          ))}
        </section>
      </div>
    </main>
  );
}
