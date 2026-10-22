# Retell Function Configuration

The following are the Retell custom-function instructions planned for the production integration.

## Function: check-availability

- Method: POST
- URL: https://api.example.com/api/v1/integrations/retell/functions/check-availability
- Expected headers: Authorization, X-Retell-Signature
- Input schema: service_type, preferred_date, time_preference
- Response: success, status, slots[]

## Function: create-appointment

- Method: POST
- URL: https://api.example.com/api/v1/integrations/retell/functions/create-appointment
- Input: patient details, service type, preferred time, provider preference
- Response: success, status, appointment_id

## Webhook endpoint

- Method: POST
- URL: https://api.example.com/api/v1/integrations/retell/webhooks
- Purpose: receive call events, webhook duplicates, and status changes
- Verification: use Retell signature verification if supported by the provider

## Security notes

- Keep all Retell credentials in environment variables.
- Never expose keys in browser code.
- Use idempotency keys for booking and reschedule actions.
