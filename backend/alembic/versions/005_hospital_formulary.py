"""Hospital formulary kept separate from synthetic drug knowledge and stock."""
from alembic import op
from app.db import FormularyItem
revision='005'
down_revision='004'
branch_labels=None
depends_on=None

def upgrade():
    FormularyItem.__table__.create(op.get_bind(),checkfirst=True)

def downgrade():
    op.drop_table('formulary_items')
