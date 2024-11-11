"""Add receipt_number column to activation_codes

Revision ID: b3f69a71252b
Revises: f14505b43dc8
Create Date: 2024-11-10 16:19:53.023703

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b3f69a71252b'
down_revision: Union[str, None] = 'f14505b43dc8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
