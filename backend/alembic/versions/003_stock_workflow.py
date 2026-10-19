"""Physician finalization and pharmacist stock alternatives."""
from alembic import op
import sqlalchemy as sa
from app.db import StockAlternative
revision='003'
down_revision='002'
branch_labels=None
depends_on=None

def upgrade():
    bind=op.get_bind()
    inspector=sa.inspect(bind)
    if 'stock_status' not in {c['name'] for c in inspector.get_columns('drugs')}:
        op.add_column('drugs',sa.Column('stock_status',sa.String(),nullable=False,server_default='IN_STOCK'))
    StockAlternative.__table__.create(bind,checkfirst=True)
    columns={c['name'] for c in sa.inspect(bind).get_columns('prescriptions')}
    if 'finalized_at' not in columns:
        op.add_column('prescriptions',sa.Column('finalized_at',sa.DateTime(timezone=True),nullable=True))
    if 'stock_alternative_id' not in columns:
        op.add_column('prescriptions',sa.Column('stock_alternative_id',sa.Integer(),nullable=True))
    foreign_keys=sa.inspect(bind).get_foreign_keys('prescriptions')
    if not any('stock_alternative_id' in f['constrained_columns'] for f in foreign_keys):
        with op.batch_alter_table('prescriptions') as batch:
            batch.create_foreign_key('fk_prescription_stock_alternative','stock_alternatives',['stock_alternative_id'],['id'])

def downgrade():
    with op.batch_alter_table('prescriptions') as batch:
        batch.drop_constraint('fk_prescription_stock_alternative',type_='foreignkey')
        batch.drop_column('stock_alternative_id')
        batch.drop_column('finalized_at')
    op.drop_table('stock_alternatives')
    op.drop_column('drugs','stock_status')
