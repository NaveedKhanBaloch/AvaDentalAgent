# Call processing and human escalation

The call-event endpoint accepts the documented `event` and `call` envelope. It verifies the exact raw bytes with the webhook-badged Retell API key and a timestamped HMAC signature. An enabled, unambiguous agent-to-clinic integration is mandatory; metadata is never a tenant or patient credential.

The same PostgreSQL transaction takes a clinic/call advisory lock, checks a durable event key, updates the call and records the processed event. Event identity is clinic + call ID + event type. Repeated deliveries are acknowledged as duplicate. Rank is monotonic: registered (0), ongoing (1), ended (2), analyzed (3). Missing timings may be filled by late events; lifecycle cannot move backwards. This intentionally treats one analyzed event as final: corrected analysis for the same call/event requires a future reviewed versioning policy.

No transcript, recording URL or analysis text is persisted by this handler. No patient is inferred from caller ID. No appointment is created from call events. An event cannot establish that a booking occurred. Booking tools attach their committed appointment and `booked` outcome in the booking transaction. Call outcomes and lifecycle are separate.

Existing outcomes `booked`, `missed`, `follow_up` remain. New `unresolved` indicates an ended/analyzed call without a transaction-derived outcome. `rescheduled`, `cancelled`, `information_provided`, `human_transfer`, and `technical_failure` are reserved for future authoritative events, not synthesized from LLM analysis. The backend does not claim a live transfer occurred.

`create-followup` uses the existing FollowUp queue, requires a callback phone and a stable idempotency key, and never links an unverified patient. It records the call's escalation as `requested`; staff review it in the existing queue. Retry uses the same key. A caller requesting a human, failed verification, unsupported treatment, insurance/billing complexity, complaints or repeated misunderstanding should be offered this callback route. A configured Retell transfer tool may be used for phone calls; failed/unavailable transfer falls back to the callback tool. No immediate response time is promised.

Sensitive clinical questions require a clinician. Do not diagnose or provide patient-specific treatment instructions. An emergency script must be approved by the clinic before live use; no clinician contact may be claimed unless it actually occurred. This code does not supply an unapproved clinical script.

All current webhook work is short database work and executes in a thread pool outside the async event loop. There are no slow notification or analysis jobs, so no unnecessary queue was added. The existing worker now remains alive with a Redis heartbeat and bounded connection timeouts; it is explicitly an idle maintenance process, not a fabricated job processor. Bookings remain synchronous.

Official references reviewed on 2026-10-23:

- [Retell event webhooks](https://docs.retellai.com/features/register-webhook)
- [Retell signature verification](https://docs.retellai.com/features/secure-webhook)
- [Transfer Call tool](https://docs.retellai.com/build/single-multi-prompt/transfer-call)
