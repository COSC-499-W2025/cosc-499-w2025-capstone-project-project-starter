from alembic import op
import sqlalchemy as sa

revision = "0003_add_unique_to_showcase"
down_revision = "0002_auth_accounts_sessions"
branch_labels = None
depends_on = None

def upgrade():
    # Data-fix: Delete duplicates, keeping the most recent entry
    op.execute("""
        DELETE FROM portfolio_showcases
        WHERE id IN (
            SELECT id
            FROM (
                SELECT id,
                       ROW_NUMBER() OVER (
                           PARTITION BY project_id 
                           ORDER BY id DESC
                       ) as row_num
                FROM portfolio_showcases
            ) t
            WHERE t.row_num > 1
        )
    """)

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