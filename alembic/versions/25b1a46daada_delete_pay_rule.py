"""delete pay_rule

Revision ID: 25b1a46daada
Revises: 29c4cc50c373
Create Date: 2025-08-29 00:58:40.890484

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '25b1a46daada'
down_revision: Union[str, Sequence[str], None] = '29c4cc50c373'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.execute("UPDATE pay_rates SET end_date = NULL WHERE end_date = DATE '9999-12-31';")
    op.alter_column(
        "pay_rates",
        "end_date",
        existing_type=sa.Date(),
        nullable=True,
        existing_nullable=False,
    )


def downgrade():
    op.execute("UPDATE pay_rates SET end_date = DATE '9999-12-31' WHERE end_date IS NULL;")

    op.alter_column(
        "pay_rates",
        "end_date",
        existing_type=sa.Date(),
        nullable=False,
        existing_nullable=True,
    )
