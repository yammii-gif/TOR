"""Use hospital products for prescribing and freeze stock-offer provenance."""
import sqlalchemy as sa
from alembic import op
revision='006'
down_revision='005'
branch_labels=None
depends_on=None

def upgrade():
    bind=op.get_bind()
    if 'formulary_code' not in {c['name'] for c in sa.inspect(bind).get_columns('drugs')}:
        with op.batch_alter_table('drugs') as batch:
            batch.alter_column('name',existing_type=sa.String(100),type_=sa.String(500))
            batch.add_column(sa.Column('formulary_code',sa.String(100),nullable=True))
            batch.create_foreign_key('fk_drug_formulary','formulary_items',['formulary_code'],['code'])
            batch.create_unique_constraint('uq_drug_formulary',['formulary_code'])
    if 'formulary_snapshot' not in {c['name'] for c in sa.inspect(bind).get_columns('stock_alternatives')}:
        op.add_column('stock_alternatives',sa.Column('formulary_snapshot',sa.Text(),nullable=False,server_default='{}'))

def downgrade():
    op.drop_column('stock_alternatives','formulary_snapshot')
    with op.batch_alter_table('drugs') as batch:
        batch.drop_constraint('uq_drug_formulary',type_='unique')
        batch.drop_constraint('fk_drug_formulary',type_='foreignkey')
        batch.drop_column('formulary_code')
