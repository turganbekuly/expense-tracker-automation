"""Add unique constraint to receipt_number

Revision ID: 9d99c1cd451c
Revises: 7b284841e786
Create Date: 2024-11-10 18:30:22.166182

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9d99c1cd451c'
down_revision: Union[str, None] = '7b284841e786'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
