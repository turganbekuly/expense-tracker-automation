"""Create activation_codes table with receipt_number

Revision ID: 7b284841e786
Revises: b3f69a71252b
Create Date: 2024-11-10 16:26:41.881390

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7b284841e786'
down_revision: Union[str, None] = 'b3f69a71252b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
