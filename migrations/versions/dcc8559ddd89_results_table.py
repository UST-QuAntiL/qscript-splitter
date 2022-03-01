"""results table

Revision ID: dcc8559ddd89
Revises: 
Create Date: 2021-12-07 12:49:11.814138

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'dcc8559ddd89'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('result',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('program', sa.LargeBinary(), nullable=True),
    sa.Column('agent', sa.LargeBinary(), nullable=True),
    sa.Column('error', sa.String(length=1200), nullable=True),
    sa.Column('complete', sa.Boolean(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('result')
    # ### end Alembic commands ###
