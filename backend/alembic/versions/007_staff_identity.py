"""Individual staff accounts, revocable shared sessions and persistent login throttling."""
from alembic import op
import sqlalchemy as sa
from app.db import StaffUser,StaffSession,AuthAttempt
revision='007'
down_revision='006'
branch_labels=None
depends_on=None

def upgrade():
    if 'request_key' not in {c['name'] for c in sa.inspect(op.get_bind()).get_columns('prescriptions')}:
        with op.batch_alter_table('prescriptions') as batch:
            batch.add_column(sa.Column('request_key',sa.String(64),nullable=True))
            batch.create_unique_constraint('uq_prescription_request_key',['request_key'])
    for table in (StaffUser.__table__,StaffSession.__table__,AuthAttempt.__table__):table.create(op.get_bind(),checkfirst=True)
    if op.get_bind().dialect.name=='postgresql':
        op.execute("CREATE OR REPLACE FUNCTION renal_audit_immutable() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'Audit records are append-only'; END; $$")
        op.execute("CREATE TRIGGER audit_no_mutation BEFORE UPDATE OR DELETE ON audit FOR EACH ROW EXECUTE FUNCTION renal_audit_immutable()")
        op.execute("CREATE TRIGGER audit_no_truncate BEFORE TRUNCATE ON audit FOR EACH STATEMENT EXECUTE FUNCTION renal_audit_immutable()")

def downgrade():
    with op.batch_alter_table('prescriptions') as batch:
        batch.drop_constraint('uq_prescription_request_key',type_='unique');batch.drop_column('request_key')
    if op.get_bind().dialect.name=='postgresql':
        op.execute('DROP TRIGGER IF EXISTS audit_no_mutation ON audit');op.execute('DROP TRIGGER IF EXISTS audit_no_truncate ON audit');op.execute('DROP FUNCTION IF EXISTS renal_audit_immutable()')
    for name in ('staff_sessions','auth_attempts','staff_users'):op.drop_table(name)
