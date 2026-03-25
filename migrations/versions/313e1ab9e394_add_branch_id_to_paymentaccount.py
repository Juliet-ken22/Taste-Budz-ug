"""Add branch_id to PaymentAccount

Revision ID: 313e1ab9e394
Revises: bd3760ab6a9a
Create Date: 2025-10-25 11:23:24.708566

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '313e1ab9e394'
down_revision = 'bd3760ab6a9a'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('payment_account', schema=None) as batch_op:
        # 1️⃣ Drop existing foreign key first (if it exists)
        batch_op.drop_constraint('fk_payment_account_branch', type_='foreignkey')

        # 2️⃣ Drop old column if it exists
        batch_op.drop_column('branch_id')

        # 3️⃣ Add column with correct type
        batch_op.add_column(sa.Column('branch_id', sa.String(length=36), nullable=True))

        # 4️⃣ Create the foreign key again
        batch_op.create_foreign_key(
            'fk_payment_account_branch',
            'branch',
            ['branch_id'],
            ['id']
        )


def downgrade():
    with op.batch_alter_table('payment_account', schema=None) as batch_op:
        # Drop FK first
        batch_op.drop_constraint('fk_payment_account_branch', type_='foreignkey')

        # Drop the column
        batch_op.drop_column('branch_id')
