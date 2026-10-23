from app.db.init_db import seed_demo_data


if __name__ == "__main__":
    from app.core.config import get_settings
    if get_settings().app_env == "production":
        raise RuntimeError("Demo seed is disabled in production")
    seed_demo_data()
    print("Demo data seeded successfully.")
