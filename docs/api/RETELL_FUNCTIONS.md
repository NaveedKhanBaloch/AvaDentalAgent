# Retell integration and manual test guide

## Configuration boundary

Existing endpoint names and aliases remain under `/api/v1/integrations/retell`. No live agent has been changed. The repository contains only a demo agent ID; it does not contain an agent export or establish whether the real agent is single prompt, legacy multi prompt, or conversation flow. Confirm its type/version in the Retell dashboard before applying these instructions. For conversation flow, configure the existing function nodes and global webhook settings; do not replace the agent.

Enable a `RetellIntegration` row through reviewed administrative database provisioning: its `tenant_id`, `clinic_id` and actual `agent_id` must match existing records. `enabled=true` is required. Each agent must resolve to exactly one enabled integration. Never select a clinic from LLM-supplied IDs, metadata, or caller ID. `configuration` may retain existing settings; it is not used to establish caller identity. Demo seeding deliberately does not activate a live integration.

Use the webhook-badged API key in private API configuration as `RETELL_API_KEY`. Do not send it to the LLM, use it as a function argument, or put it in frontend variables. Requests require `Content-Type: application/json` and Retell's `X-Retell-Signature`. Custom bearer/API-key headers from the old implementation are no longer sufficient. Optional `X-Integration-ID` can narrow an already signed agent context but cannot replace it.

Disable **Payload: args only**. The supported envelope is:

```json
{"name":"check_availability","call":{"agent_id":"agent_TEST","call_id":"call_TEST"},"args":{"preferred_date":"2026-11-10","provider_id":"PROVIDER_TEST","service_id":"SERVICE_TEST"}}
```

The `call` context must be signed, not generated inside `args`. No inbound-call routing endpoint was added. Existing inbound telephony configuration stays in Retell. Inbound routing webhooks and lifecycle webhooks are distinct; do not point an inbound routing URL at the lifecycle receiver.

## Functions

All methods are POST. Replace `https://api.example.test` with your HTTPS API origin. URLs are that origin plus `/api/v1/integrations/retell/functions/` plus the function name below.

| Function | Arguments | Result / description |
|---|---|---|
| `check_availability` | `preferred_date` (YYYY-MM-DD; legacy `date` accepted), optional `provider_id`, `service_id`, `time_preference` | `slots[{start_time,end_time,provider_id,timezone}]`, `timezone`; status available/unavailable. All eligible providers considered if omitted. |
| `book_appointment` | `first_name,last_name,phone,provider_id,service_id,start_time,confirmed,idempotency_key`; optional `end_time` | New intake and appointment committed together; returns appointment_id, times, timezone and actual status. Existing patient_id requires staff verification. |
| `lookup_patient` | No identifying arguments can establish verification | verification_required; no registration status or patient data is disclosed. |
| `get_appointment` | `appointment_id` is untrusted | verification_required; use staff assistance. |
| `reschedule_appointment` | IDs and times remain untrusted | verification_required until an approved caller-verification service exists. Staff uses the shared dashboard/API. |
| `cancel_appointment` | Appointment ID and confirmation cannot establish identity | verification_required; staff uses the shared dashboard/API. |
| `get_treatment_information` | optional `service_id` | Approved catalog information only; service or services. No patient-specific clinical advice. |
| `get_clinic_information` | none | Name, address, phone and timezone. |
| `request_human_assistance` | `phone,idempotency_key`; optional `first_name,reason` | Real followup_id, status created; records a callback without promising timing. |
| `verify-patient` (legacy) | none | verification_required; phone/email matching is not verification. |

Legacy callback endpoint `create-followup` remains; configure the Retell tool name as `request_human_assistance` (letters/underscores). Legacy aliases remain: `check-availability`, `create-appointment`, `get-patient`, `get-appointment`, `reschedule-appointment`, `cancel-appointment`, `get-treatment-information`, `get-clinic-information`.

Parameter schema pattern (use actual test catalog identifiers):

```json
{
  "type":"object",
  "required":["first_name","last_name","phone","provider_id","service_id","start_time","confirmed","idempotency_key"],
  "properties": {
    "first_name":{"type":"string","description":"Patient first name"},
    "last_name":{"type":"string","description":"Patient last name"},
    "phone":{"type":"string","description":"Callback number provided by caller"},
    "provider_id":{"type":"string","description":"Exact provider from availability"},
    "service_id":{"type":"string","description":"Exact service selected from catalog"},
    "start_time":{"type":"string","description":"Exact ISO timestamp including offset from availability"},
    "confirmed":{"type":"boolean","description":"True only after patient explicitly confirms the summarized appointment"},
    "idempotency_key":{"type":"string","description":"Stable key for this confirmed action; reuse unchanged on retry"}
  }
}
```

Boolean confirmation is strictly typed; string `"true"` is rejected. Booking arguments must not substitute a different provider if unavailable. Durations must meet the catalog minimum; omitted end_time is calculated from the service. Naive ambiguous/nonexistent local timestamps are rejected; always send returned offset-bearing timestamps.

Every function result has `success`, `status`, `message`, and `correlation_id`. Examples:

```json
{"success":true,"status":"scheduled","message":"Appointment created.","appointment_id":"DATABASE_GENERATED_ID","start_time":"2026-11-10T15:00:00+00:00","end_time":"2026-11-10T15:30:00+00:00","timezone":"America/New_York","correlation_id":"REQUEST_ID"}
```

```json
{"success":false,"status":"verification_required","message":"A staff member must verify your identity. Use request_human_assistance to request assistance.","human_assistance_required":true,"correlation_id":"REQUEST_ID"}
```

Statuses include validation_error, confirmation_required, unavailable, verification_required and temporary_failure. HTTP errors remain predictable FastAPI `detail` responses: 401 signature, 403 integration/clinic context, 422 malformed input/missing key, 409 changed arguments under the same key, 429 rate limit, 503 unavailable rate-limit infrastructure. Business failures normally return HTTP 200 with success=false so the agent can respond safely. Never speak a booking confirmation solely because the HTTP status was 200.

## Conversation and retries

Identify clinic, service and eligible provider; check availability; present exact returned slots; collect minimum new-intake details; summarize provider/service/date/time/timezone; obtain explicit confirmation; write once using a stable key. Only confirm verbally after success=true and a committed appointment_id. If the caller changes their mind before the write, do not submit. After submission or timeout, the write may have completed: repeat the same function with identical arguments, call ID and key to retrieve its committed result. Never create a new key merely because the first response timed out. A changed decision needs a new confirmed action; existing appointments require staff verification.

Keys are scoped by clinic, call, operation and caller-supplied key, then hashed in storage. Repeated key with different arguments is HTTP 409. Different calls cannot retrieve one another's results. Record the key in call context across retries. No separate unverified lookup endpoint exposes booking results.

If missing details, unknown service, contradictory choices, disconnect or backend errors prevent completion, do not claim success. Offer staff assistance. The agent must not diagnose or promise that a clinician has been contacted.

## Webhooks and transfers

Set lifecycle URL to `https://api.example.test/api/v1/integrations/retell/webhooks`; enable call_started, call_ended and call_analyzed for the test agent. Agent-level webhook configuration takes precedence over account-level configuration. Record the effective URL, event selection and test agent version during manual acceptance; none can be inferred from this repository.

The receiver validates raw-body timestamped signatures using the Retell API key, rejects invalid/replayed timestamps, and durably deduplicates clinic/call/event. Webhooks never create appointments. See [call processing](../architecture/phase1-call-processing.md).

Configure the existing Retell Transfer Call tool with a clinic-approved static E.164/SIP destination for phone calls, or the existing transfer node for conversation flow. Web calls do not exercise phone transfer. Live transfer is not invoked or reported successful by this backend. When no transfer destination exists or transfer fails, use request_human_assistance after obtaining the callback number. Emergency wording and destinations require clinic approval before launch.

## Local integration tests

From apps/api run `.venv/bin/python -m pytest tests/test_retell_phase1.py -q`. Tests generate valid signatures over synthetic JSON and exercise both functions and lifecycle events; no real patient data is used. For a live test expose the isolated API using a temporary HTTPS tunnel; configure only a test agent/integration. Retell does not call localhost/private IPs directly.

Manual acceptance must include: test-agent call through availability/confirmed booking; dashboard observation; repeated booking key; competing dashboard/phone booking; verified staff reschedule/cancel; callback fallback; phone transfer success/failure; duplicate and out-of-order event delivery; two clinic-scoped calls; and invalid signature rejection. Record call IDs and results without transcript/PHI in shared logs. Live acceptance is pending, not satisfied by mocks.

Troubleshooting: 401 means wrong webhook-badged key, altered raw bytes, missing signature or clock skew; 403 means disabled/ambiguous agent mapping or clinic mismatch; no slots means check actual clinic/provider hours, exceptions, service mapping and timezone; unavailable after selection means a competing booking won; verification_required is intentional until approved infrastructure exists. Redis outage fails function limiting closed with 503. A pending/uncertain write must use the original key.

## Official sources reviewed 2026-10-23

- [Custom function envelope, signatures and retries](https://docs.retellai.com/build/single-multi-prompt/custom-function)
- [Raw-body signature protocol](https://docs.retellai.com/features/secure-webhook)
- [Lifecycle events and webhook precedence](https://docs.retellai.com/features/register-webhook)
- [Call transfer configuration](https://docs.retellai.com/build/single-multi-prompt/transfer-call)
- [Inbound routing webhook](https://docs.retellai.com/features/inbound-call-webhook) — overview accessible; detailed second retrieval failed. No inbound routing schema was implemented or assumed.
