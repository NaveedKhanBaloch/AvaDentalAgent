from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.models import Appointment, Clinic, ClinicBusinessHours, DentalService, Membership, Patient, Provider, Tenant, User

settings = get_settings()


def seed_demo_data() -> None:
    db: Session = SessionLocal()
    try:
        tenant = db.query(Tenant).filter(Tenant.slug == "harbor-dental-demo").first()
        if tenant is None:
            tenant = Tenant(name="Harbor Dental Group", slug="harbor-dental-demo")
            db.add(tenant)
            db.flush()

        clinic = db.query(Clinic).filter(Clinic.tenant_id == tenant.id, Clinic.name == "Harbor Dental Demo").first()
        if clinic is None:
            clinic = Clinic(
                tenant_id=tenant.id,
                name="Harbor Dental Demo",
                address="125 Shoreline Ave",
                city="Boston",
                state="MA",
                country="US",
                timezone="America/New_York",
                phone="(617) 555-0100",
                email="frontdesk@harbordentaldemo.local",
                currency="USD",
            )
            db.add(clinic)
            db.flush()

        user = db.query(User).filter(User.email == settings.demo_admin_email.lower()).first()
        if user is None:
            user = User(
                email=settings.demo_admin_email.lower(),
                password_hash=hash_password(settings.demo_admin_password),
                full_name="Harbor Dental Admin",
                status="active",
            )
            db.add(user)
            db.flush()

        membership = db.query(Membership).filter(Membership.user_id == user.id, Membership.tenant_id == tenant.id).first()
        if membership is None:
            db.add(Membership(user_id=user.id, tenant_id=tenant.id, clinic_id=clinic.id, role="Clinic Owner", status="active"))

        if db.query(Provider).filter(Provider.clinic_id == clinic.id).count() == 0:
            db.add_all([
                Provider(tenant_id=tenant.id, clinic_id=clinic.id, name="Dr. Reed Lee", title="Lead Dentist", specialty="General Dentistry"),
                Provider(tenant_id=tenant.id, clinic_id=clinic.id, name="Dr. Sofia Park", title="Orthodontist", specialty="Clear Aligners"),
            ])

        if db.query(DentalService).filter(DentalService.clinic_id == clinic.id).count() == 0:
            db.add_all([
                DentalService(tenant_id=tenant.id, clinic_id=clinic.id, name="New Patient Exam", default_duration_minutes=45, indicative_price=185.00),
                DentalService(tenant_id=tenant.id, clinic_id=clinic.id, name="Dental Cleaning", default_duration_minutes=30, indicative_price=120.00),
                DentalService(tenant_id=tenant.id, clinic_id=clinic.id, name="Teeth Whitening", default_duration_minutes=60, indicative_price=420.00),
            ])

        if db.query(ClinicBusinessHours).filter(ClinicBusinessHours.clinic_id == clinic.id).count() == 0:
            db.add_all([
                ClinicBusinessHours(clinic_id=clinic.id, weekday=0, opening_time="08:00", closing_time="17:00", is_closed=False),
                ClinicBusinessHours(clinic_id=clinic.id, weekday=1, opening_time="08:00", closing_time="17:00", is_closed=False),
                ClinicBusinessHours(clinic_id=clinic.id, weekday=2, opening_time="08:00", closing_time="17:00", is_closed=False),
                ClinicBusinessHours(clinic_id=clinic.id, weekday=3, opening_time="08:00", closing_time="17:00", is_closed=False),
                ClinicBusinessHours(clinic_id=clinic.id, weekday=4, opening_time="08:00", closing_time="17:00", is_closed=False),
                ClinicBusinessHours(clinic_id=clinic.id, weekday=5, opening_time="09:00", closing_time="13:00", is_closed=False),
                ClinicBusinessHours(clinic_id=clinic.id, weekday=6, opening_time="00:00", closing_time="00:00", is_closed=True),
            ])

        if db.query(Patient).filter(Patient.clinic_id == clinic.id).count() == 0:
            patient_rows = [
                Patient(tenant_id=tenant.id, clinic_id=clinic.id, first_name="Maya", last_name="Chen", phone="555-0102", email="maya.chen@example.com", preferred_contact_method="phone", notes="Interested in hygiene visit"),
                Patient(tenant_id=tenant.id, clinic_id=clinic.id, first_name="Daniel", last_name="Ramirez", phone="555-0103", email="daniel.ramirez@example.com", preferred_contact_method="text", notes="Needs whitening consultation"),
                Patient(tenant_id=tenant.id, clinic_id=clinic.id, first_name="Olivia", last_name="Baker", phone="555-0104", email="olivia.baker@example.com", preferred_contact_method="email", notes="Follow-up after implant consult"),
            ]
            db.add_all(patient_rows)
            db.flush()

            now = datetime.now()
            provider = db.query(Provider).filter(Provider.clinic_id == clinic.id).first()
            service = db.query(DentalService).filter(DentalService.clinic_id == clinic.id).first()
            for idx, patient in enumerate(patient_rows):
                appointment_time = now + timedelta(days=idx + 1, hours=9 + idx)
                db.add(Appointment(
                    tenant_id=tenant.id,
                    clinic_id=clinic.id,
                    patient_id=patient.id,
                    provider_id=provider.id,
                    service_id=service.id,
                    start_time=appointment_time,
                    end_time=appointment_time + timedelta(minutes=30),
                    status="scheduled" if idx % 2 == 0 else "confirmed",
                    source="dashboard",
                    notes="Demo appointment",
                ))

        db.commit()
    finally:
        db.close()
