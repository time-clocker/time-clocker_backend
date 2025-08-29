"""make pay_rates.end_date nullable

Revision ID: 29c4cc50c373
Revises: 741b7e0f847b
Create Date: 2025-08-29 00:47:48.834000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '29c4cc50c373'
down_revision: Union[str, Sequence[str], None] = '741b7e0f847b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # Si antes usaste una fecha centinela (ej: 9999-12-31), la puedes convertir en NULL
    op.execute("UPDATE pay_rates SET end_date = NULL WHERE end_date = DATE '9999-12-31';")

    # Hacer la columna nullable
    op.alter_column(
        "pay_rates",
        "end_date",
        existing_type=sa.Date(),
        nullable=True,
        existing_nullable=False,
    )


def downgrade():
    # Si haces rollback, asigna centinela a los NULL antes de volver a NOT NULL
    op.execute("UPDATE pay_rates SET end_date = DATE '9999-12-31' WHERE end_date IS NULL;")

    op.alter_column(
        "pay_rates",
        "end_date",
        existing_type=sa.Date(),
        nullable=False,
        existing_nullable=True,
    )
