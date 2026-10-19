# Architecture and boundaries

Browser (Next.js/React/TypeScript/Recharts) → FastAPI deterministic service → SQLAlchemy → SQLite demo / PostgreSQL. Alembic manages schema. Clinical engine is separate from HTTP and contains no generative AI. Drug rules remain inactive; evidence import only writes draft provenance. A licensed adapter without authorized integration returns LICENSE_REQUIRED.

Patient records are seeded synthetic JSON; prescription holds source snapshot and calculated renal function. Physician proposals require pharmacist review. Pharmacist may reject; no automatic approval or HOSxP writeback exists. Audit entries link to prescription IDs. Analytics derive rates from persisted decisions; unavailable metrics remain null.

Role selection with shared demo password is an explicit research simulation. Production requires a distinct identity provider and user-specific authorization, database-level audit immutability, external audit export, TLS ingress, deployment hardening and institutional signoff. This implementation does not claim PDPA certification.
