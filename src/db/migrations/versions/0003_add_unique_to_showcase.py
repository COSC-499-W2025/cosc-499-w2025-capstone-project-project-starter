from alembic import op
import sqlalchemy as sa

revision = "0003_add_unique_to_showcase"
down_revision = "0002_auth_accounts_sessions"
branch_labels = None
depends_on = None

def upgrade():
    op.create_unique_constraint(
        "uq_portfolio_showcases_project_id", 
        "portfolio_showcases", 
        ["project_id"]
    )

def downgrade():
    op.drop_constraint(
        "uq_portfolio_showcases_project_id", 
        "portfolio_showcases", 
        type_="unique"
    )