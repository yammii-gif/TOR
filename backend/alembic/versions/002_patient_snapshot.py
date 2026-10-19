"""Persist source context and link audit to prescription."""
from alembic import op
import sqlalchemy as sa
from app.db import Patient
revision='002'
down_revision='001'
branch_labels=None
depends_on=None
def upgrade():
    bind=op.get_bind()
    # Initial 001 metadata includes these columns for fresh installations.
    Patient.__table__.create(bind,checkfirst=True)
    inspector=sa.inspect(bind)
    if 'source_snapshot' not in {c['name'] for c in inspector.get_columns('prescriptions')}:
        op.add_column('prescriptions',sa.Column('source_snapshot',sa.Text(),nullable=False,server_default='{}'))
    if 'record_id' not in {c['name'] for c in inspector.get_columns('audit')}:
        op.add_column('audit',sa.Column('record_id',sa.Integer(),nullable=True))
def downgrade():
    op.drop_column('audit','record_id');op.drop_column('prescriptions','source_snapshot');op.drop_table('patients')
