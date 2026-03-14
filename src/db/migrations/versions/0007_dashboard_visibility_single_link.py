from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0007_dashboard_visibility"
down_revision = "0006_dashboard_link_types"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "portfolio_dashboards",
        sa.Column(
            "visibility_config_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text(
                "'{\"projects\": true, \"skills_timeline\": true, \"top_projects\": true, \"activity_heatmap\": true, \"showcases\": true}'::jsonb"
            ),
        ),
    )

    op.drop_constraint("uq_portfolio_dashboards_editor_slug", "portfolio_dashboards", type_="unique")
    op.drop_constraint("ck_portfolio_dashboards_last_generated_link_type", "portfolio_dashboards", type_="check")
    op.drop_column("portfolio_dashboards", "last_generated_link_type")
    op.drop_column("portfolio_dashboards", "editor_slug")


def downgrade():
    op.add_column(
        "portfolio_dashboards",
        sa.Column("editor_slug", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "portfolio_dashboards",
        sa.Column("last_generated_link_type", sa.String(length=16), nullable=False, server_default="public"),
    )

    op.execute("UPDATE portfolio_dashboards SET editor_slug = public_slug WHERE editor_slug IS NULL")

    op.alter_column("portfolio_dashboards", "editor_slug", nullable=False)
    op.create_unique_constraint("uq_portfolio_dashboards_editor_slug", "portfolio_dashboards", ["editor_slug"])
    op.create_check_constraint(
        "ck_portfolio_dashboards_last_generated_link_type",
        "portfolio_dashboards",
        "last_generated_link_type IN ('public', 'editor')",
    )

    op.drop_column("portfolio_dashboards", "visibility_config_json")
