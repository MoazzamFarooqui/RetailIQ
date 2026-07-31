"""One-command dev runner — installs deps, sets up DB, and starts both servers."""
import subprocess, sys, os, shutil

ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(ROOT)

print("=" * 60)
print("  RetailIQ v2.0 — Development Setup")
print("=" * 60)

# ── 1. Backend dependencies ──────────────────────────────────────────────────
print("\n[1/4] Installing backend dependencies...")
subprocess.run([sys.executable, "-m", "pip", "install", "-r", "backend/requirements.txt", "-q"], check=True)

# ── 2. Environment file ──────────────────────────────────────────────────────
print("\n[2/4] Setting up environment...")
env_path = os.path.join(ROOT, ".env")
if not os.path.exists(env_path):
    with open(env_path, "w") as f:
        f.write("""APP_NAME=RetailIQ API
APP_VERSION=2.0.0
ENVIRONMENT=development
DEBUG=true
DATABASE_URL=sqlite+aiosqlite:///data/retailiq_v2.db
REDIS_URL=
SECRET_KEY=dev-secret-key-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRE_DAYS=7
OPENWEATHER_API_KEY=
HOLIDAY_API_KEY=
CELERY_BROKER_URL=
CELERY_RESULT_BACKEND=
CORS_ORIGINS=["http://localhost:3000","http://localhost:5173"]
""")
    print("  Created .env for local development")
else:
    print("  .env already exists, skipping")

# ── 3. Create admin user ────────────────────────────────────────────────────
print("\n[3/4] Creating database + admin user...")

# Install aiosqlite for SQLite dev mode
subprocess.run([sys.executable, "-m", "pip", "install", "aiosqlite", "-q"], check=True)

# Run a quick init script
init_code = """
import asyncio, os
os.environ["ENVIRONMENT"] = "development"
from app.core.database import engine, Base, async_session_factory
from app.core.security import hash_password
from app.models.user import User, UserRole
from sqlalchemy import select

async def init():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with async_session_factory() as session:
        result = await session.execute(select(User).where(User.username == "admin"))
        if not result.scalar_one_or_none():
            admin = User(
                email="admin@retailiq.com",
                username="admin",
                hashed_password=hash_password("admin123"),
                role=UserRole.ADMIN,
            )
            session.add(admin)
            await session.commit()
            print("  ✓ Admin user created: admin / admin123")
        else:
            print("  ✓ Admin user already exists")
    await engine.dispose()

asyncio.run(init())
"""

subprocess.run([sys.executable, "-c", init_code], cwd=ROOT, check=True)

print("\n[4/4] Setup complete!")
print()
print("=" * 60)
print("  TO RUN THE APP:")
print("=" * 60)
print()
print("  Open TWO terminals:")
print()
print("  Terminal 1 — Backend API:")
print(f"    cd {ROOT}")
print('    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000')
print()
print("  Terminal 2 — React Frontend:")
print(f"    cd {ROOT}\\client")
print("    npm run dev")
print()
print("  Then open:  http://localhost:3000")
print("  Login:     admin / admin123")
print("  API docs:  http://localhost:8000/docs")
print("=" * 60)
