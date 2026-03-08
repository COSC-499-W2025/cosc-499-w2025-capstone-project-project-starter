from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0004_dashboard_publications"
down_revision = "0003_add_unique_to_showcase"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "dashboard_publications",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("portfolio_id", sa.UUID(as_uuid=True), sa.ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column(
            "frozen_config_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "frozen_dashboard_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "filter_spec_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("created_by_user_id", sa.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_unique_constraint(
        "uq_dashboard_publications_portfolio_version",
        "dashboard_publications",
        ["portfolio_id", "version"],
    )
    op.create_index(
        "ix_dashboard_publications_portfolio_created",
        "dashboard_publications",
        ["portfolio_id", "created_at"],
        unique=False,
    )

    op.create_table(
        "portfolio_dashboards",
        sa.Column(
            "portfolio_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("portfolios.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("mode", sa.String(length=16), nullable=False, server_default="private"),
        sa.Column("public_slug", sa.String(length=64), nullable=False),
        sa.Column(
            "active_publication_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("dashboard_publications.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.CheckConstraint("mode IN ('private', 'public')", name="ck_portfolio_dashboards_mode"),
    )
    op.create_unique_constraint("uq_portfolio_dashboards_public_slug", "portfolio_dashboards", ["public_slug"])
    op.create_index("ix_portfolio_dashboards_mode", "portfolio_dashboards", ["mode"], unique=False)


def downgrade():
    op.drop_index("ix_portfolio_dashboards_mode", table_name="portfolio_dashboards")
    op.drop_constraint("uq_portfolio_dashboards_public_slug", "portfolio_dashboards", type_="unique")
    op.drop_table("portfolio_dashboards")

    op.drop_index("ix_dashboard_publications_portfolio_created", table_name="dashboard_publications")
    op.drop_constraint("uq_dashboard_publications_portfolio_version", "dashboard_publications", type_="unique")
    op.drop_table("dashboard_publications")
