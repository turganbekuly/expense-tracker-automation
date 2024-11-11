"""Add unique constraint to receipt_number

Revision ID: b072679e187a
Revises: 9d99c1cd451c
Create Date: 2024-11-10 18:53:49.956494

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b072679e187a'
down_revision: Union[str, None] = '9d99c1cd451c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
