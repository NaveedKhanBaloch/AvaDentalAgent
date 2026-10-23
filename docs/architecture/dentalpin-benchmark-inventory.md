# DentalPin Capability Inventory (Benchmark Reference)

## Scope

This document records DentalPin’s published platform capabilities from its public documentation and module references. It is used as a benchmark for product planning only, not as a source to copy implementation details.

The reference documentation states a modular architecture, a product/UX documentation model, and module-based deep dives. It also notes the project is structured around modules and technical docs rather than a single app file.

Year and source status note: this inventory is based on publicly documented product references and module taxonomy, not on source code extraction from the DentalPin repository itself.

---

## 1. Benchmark context and legal framing

DentalPin is an OSS project with a Business Source License 1.1 model and a stated conversion to Apache 2.0 after a waiting period. The project includes product docs, module docs, and technical reference docs.

This project uses the DentalPin documentation only for:

- feature benchmarking
- business capability comparison
- architecture planning
- module scoping reference

It does not copy implementation details, protected assets, or source code.

---

## 2. Documented platform intent

From the documentation structure, DentalPin is intended to be a broad dental practice management platform, with documentation organized into:

- user-manual/ — end-user/operator guides
- features/ — product and UX briefs
- technical/ — architecture and engineering references
- modules/ — module-specific deep dives
- adr/ — architecture decisions
- checklists/ — implementation processes
- workflows/ — runbooks and operational steps

This signals a product design around a modular, enterprise-grade dental system rather than a one-off booking tool.

---

## 3. Capability inventory by area

### A. Front desk and appointment operations

Business purpose:
- manage patient appointments and visit flow
- coordinate provider schedules
- handle front-desk operations efficiently

Intended users:
- receptionists
- schedulers
- clinic managers
- clinicians

Main entities:
- patient
- appointment
- provider
- visit room / schedule slot
- schedule exceptions

Key actions:
- book appointment
- reschedule or cancel
- search patient
- check availability
- designate provider/time slot
- confirm booking

Business rules:
- no appointment overlap per provider
- clinic business hours apply
- exceptions and closures override schedule
- time slots can be filtered by patient preference or provider availability

Expected outputs:
- appointment list
- daily calendar view
- confirmation records
- missed or rescheduled entries

External integrations:
- communications
- reminders
- AI or call-center automation

---

### B. Patient management

Business purpose:
- maintain patient master records
- capture intake data and contact preferences
- support follow-up and recall workflows

Information collected:
- demographics
- contact details
- preferred communication method
- insurance information
- treatment history or visit narrative

Main entities:
- patient
- insurance profile
- contact records
- family or guarantor relationships (likely depending on module scope)

User-visible screens:
- patient list
- patient detail
- insurance tab
- notes or record history

Business rules:
- only one patient canonical record per person per clinic
- contact details must be accurate for reminder workflows
- insurance status can be tracked separately

Expected reports:
- patient roster
- active patients
- follow-up queue

---

### C. Clinical record and treatment workflow

Business purpose:
- support patient treatment progression and clinician documentation

Intended users:
- dentists
- hygienists
- clinical assistants
- office managers

Main entities:
- treatment plan
- procedure
- clinical notes
- tooth chart / odontogram
- treatment estimate / quote

Relationships:
- patient has many treatment episodes
- treatment plan contains procedures
- appointments are linked to treatment and clinical notes

User-visible pages:
- clinical tab
- treatment plan list
- tooth chart or odontogram views
- procedure documentation screens

Business rules:
- treatment must be linked to a patient and a treatment plan
- clinical notes are tied to authorized clinician workflow
- treatment plans may evolve over time

Expected reports:
- treatment history
- active cases
- treatment plan acceptance / estimate tracking

Security considerations:
- clinician-only access to certain clinical data
- auditability of notes and changes
- explicit patient consent or treatment acknowledgement flow

---

### D. Budget and treatment quote management

Business purpose:
- estimate treatment costs and produce versioned quotes
- record signatures and approvals
- support PDF output

Documented module reference:
- `budget` module

Main entities:
- treatment quote
- quote version
- patient
- treatment plan or procedure
- authorized signatory

User actions:
- create quote
- update quote version
- sign document
- export PDF
- approve / send to patient

Business rules:
- quote changes must preserve version history
- signatures must be linked to approval scope
- financial approvals can be tracked separately from clinical notes

---

### E. Billing and financial operations

Business purpose:
- manage charges, receipts, and financial status
- track patient balances and collections

Intended users:
- front office staff
- billing managers
- clinic owner

Main entities:
- invoice
- payment
- ledger entry
- claim / reimbursement record
- refund / adjustment

Business rules:
- financial operations must be auditable
- treatment and payment records must reconcile
- role permissions restrict financial access

Expected reports:
- receivables
- payments by day
- outstanding balances
- revenue summaries

---

### F. Reporting, dashboards, and analytics

Business purpose:
- operational visibility for clinic management
- executive reporting and KPI measurement

Key metrics likely covered:
- visits by day/week/month
- no-show and cancellation rates
- provider productivity
- treatment volume
- revenue and collection trends
- call outcomes and conversion metrics

User-visible pages:
- executive dashboard
- daily operations view
- operational KPI cards
- filtered reporting screens

---

### G. Staff and role-based access

Business purpose:
- secure role-based access across clinic operations

Documented technical references indicate RBAC and permissions are important cross-cutting concerns.

Main entities:
- user
- team member
- role
- permission
- membership

Business rules:
- access must be scoped by tenant and clinic
- clinicians and management may have different permissions
- audit trail should record actions

---

### H. External integrations and automation

Documented modules and technical references suggest a platform that extends beyond core booking, including:

- AI call automation / receptionist flows
- messaging integrations
- external accounting or compliance exports
- import systems and migration tooling
- reporting and compliance modules

These are relevant to strategic expansion but not necessarily core MVP features for a small clinic.

---

## 4. Documented current functionality vs planned functionality

### Documented current functionality (verified at a high level)

- appointment scheduling and patient records
- clinical record and treatment plan patterns
- budget / quote workflows
- module-based product architecture
- technical reference for shared concerns such as RBAC, APIs, and testing
- billing and accounting-related modules are mentioned in module docs

### Planned functionality

- specialized compliance modules
- deeper production integrations
- accounting export modules
- extended clinical workflows and odontogram-related features
- automation and telephony integrations

### Functionality not directly verified

- exact UI screens for every module
- full financial ledger implementation details
- complete patient journey rules
- exact import/export integration contracts
- all pricing modules
- all country-specific compliance logic

This inventory is intentionally conservative: only capabilities that are directly indicated in the public documentation are recorded.

---

## 5. Key benchmark takeaways for this project

The DentalPin benchmark shows a broader product platform than the existing repo has today. The current app already has the foundations of front-desk operations, patient records, scheduling, and AI call support. The missing work is not a total rebuild; it is a structured expansion into more complete dental practice management features.

Main missing strategic areas relative to the benchmark:

1. deeper clinical treatment workflow
2. richer treatment estimate / budget workflows
3. financial and billing ledger features
4. stronger role segmentation and policy enforcement
5. production reporting, analytics, and exports
6. additional integration modules and compliance support

