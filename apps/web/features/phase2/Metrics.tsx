"use client";
import { useEffect, useState } from "react";
import { request, panel } from "./api";
export default function Metrics() {
  const [data, setData] = useState<Record<string, number | string> | null>(
      null,
    ),
    [error, setError] = useState("");
  useEffect(() => {
    request("/operations/capabilities")
      .then((c) => {
        if (c.permissions.includes("operations_report"))
          return request("/operations/metrics").then(setData);
      })
      .catch((e) => setError(e.message));
  }, []);
  if (error) return <p role="alert">{error}</p>;
  if (!data) return null;
  return (
    <section aria-label="Patient operations metrics" className="mb-5 space-y-2">
      <h2 className="text-xl font-semibold">Patient operations</h2>
      <p className="text-xs">
        Current clinic · {data.timezone} · registrations cover the last 30 days;
        other counts are current/all-time state
      </p>
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {Object.entries(data)
          .filter(([k]) => k !== "timezone")
          .map(([k, v]) => (
            <a
              className={panel}
              key={k}
              href={`/dashboard?section=${k.startsWith("estimates") ? "estimates" : k.startsWith("recalls") ? "recalls" : k.includes("followup") ? "follow-ups" : "patients"}${k.startsWith("estimates") ? "&status=" + k.replace("estimates_", "") : k === "overdue_followups" ? "&overdue=true" : ""}`}
            >
              <p className="text-sm capitalize">{k.replaceAll("_", " ")}</p>
              <p className="text-2xl font-semibold">{v}</p>
            </a>
          ))}
      </div>
    </section>
  );
}
