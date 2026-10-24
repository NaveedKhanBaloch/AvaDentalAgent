export const API =
  process.env.NEXT_PUBLIC_API_URL ??
  process.env.NEXT_PUBLIC_API_BASE_URL ??
  "http://localhost:8000";
export async function request(path: string, method = "GET", body?: unknown) {
  const token = localStorage.getItem("dentalvoice_token");
  const response = await fetch(API + "/api/v1" + path, {
    method,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    ...(body !== undefined ? { body: JSON.stringify(body) } : {}),
  });
  if (!response.ok) {
    let detail: unknown;
    try {
      detail = (await response.json()).detail;
    } catch {
      detail = "Request failed";
    }
    throw new Error(
      typeof detail === "string" ? detail : "Please check the form fields.",
    );
  }
  if (response.headers.get("content-type")?.includes("application/pdf"))
    return response.blob();
  return response.json();
}
export const input =
  "w-full rounded-xl border border-slate-300 bg-white p-2 text-slate-900 dark:bg-slate-900 dark:text-slate-100";
export const button =
  "rounded-xl bg-cyan-700 px-3 py-2 text-sm font-medium text-white disabled:opacity-40";
export const panel =
  "rounded-2xl border border-slate-200 bg-white p-4 text-slate-800 dark:bg-slate-900 dark:text-slate-100";
export function display(value: unknown): string {
  return value == null ? "—" : String(value);
}
