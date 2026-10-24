"use client";

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { LockKeyhole, Mail } from 'lucide-react';

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000';

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState('admin@harbordentaldemo.local');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError('');

    try {
      const response = await fetch(`${API_URL}/api/v1/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      });

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail ?? 'Login failed');
      }

      localStorage.setItem('dentalvoice_token', data.access_token);
      router.push('/dashboard');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Login failed');
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-[#edf1f6] p-6">
      <div className="w-full max-w-md rounded-[28px] border border-[#e5e7eb] bg-white p-8 shadow-[0_18px_45px_rgba(15,23,42,0.08)]">
        <div className="mb-8 flex items-center gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-[#2563eb] text-sm font-bold text-white shadow-lg shadow-blue-200/70">A</div>
          <div>
            <div className="text-lg font-bold text-slate-900">DentalVoice AI</div>
            <div className="text-xs text-slate-500">Clinic login</div>
          </div>
        </div>

        <h1 className="mb-2 text-[28px] font-bold tracking-[-0.04em] text-slate-900">Welcome back</h1>
        <p className="mb-6 text-sm text-slate-600">Sign in to the Harbor Dental Demo workspace.</p>

        <form className="space-y-4" onSubmit={handleSubmit}>
          <label className="block">
            <span className="mb-2 block text-sm font-medium text-slate-700">Email</span>
            <div className="flex items-center gap-2 rounded-xl border border-slate-200 bg-[#f8fafc] px-3 py-2.5">
              <Mail size={16} className="text-slate-400" />
              <input
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                className="w-full bg-transparent text-sm text-slate-900 outline-none placeholder:text-slate-400"
              />
            </div>
          </label>

          <label className="block">
            <span className="mb-2 block text-sm font-medium text-slate-700">Password</span>
            <div className="flex items-center gap-2 rounded-xl border border-slate-200 bg-[#f8fafc] px-3 py-2.5">
              <LockKeyhole size={16} className="text-slate-400" />
              <input
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                className="w-full bg-transparent text-sm text-slate-900 outline-none placeholder:text-slate-400"
              />
            </div>
          </label>

          {error ? <p className="text-sm text-red-600">{error}</p> : null}

          <button
            type="submit"
            disabled={loading}
            className="mt-2 w-full rounded-xl bg-[#2563eb] px-4 py-3 font-medium text-white shadow-[0_8px_16px_rgba(37,99,235,0.28)] transition hover:bg-[#1d4ed8] disabled:cursor-not-allowed disabled:opacity-70"
          >
            {loading ? 'Signing in...' : 'Login'}
          </button>
        </form>
      </div>
    </main>
  );
}
