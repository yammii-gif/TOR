"""Public evidence provenance and licensed source access status."""
from alembic import op
from app.db import EvidenceRecord
revision='004'
down_revision='003'
branch_labels=None
depends_on=None
def upgrade():EvidenceRecord.__table__.create(op.get_bind(),checkfirst=True)
def downgrade():op.drop_table('evidence_records')
