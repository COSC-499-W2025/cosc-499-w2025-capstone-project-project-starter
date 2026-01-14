from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto;")

    # Users + config + consents
    op.create_table(
        "users",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )

    op.create_table(
        "user_config",
        sa.Column("user_id", sa.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("config_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )

    op.create_table(
        "privacy_consents",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", sa.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("consent_type", sa.String(length=64), nullable=False),  # data_access | external_services
        sa.Column("granted", sa.Boolean(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("granted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("ix_privacy_consents_user_type", "privacy_consents", ["user_id", "consent_type"], unique=False)

    # Portfolio -> Project -> Snapshot
    op.create_table(
        "portfolios",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", sa.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False, server_default="default"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("ix_portfolios_user", "portfolios", ["user_id"], unique=False)

    op.create_table(
        "projects",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("portfolio_id", sa.UUID(as_uuid=True), sa.ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("project_type", sa.String(length=32), nullable=False, server_default="code"),  # code | document | image | mixed
        sa.Column("collaboration_type", sa.String(length=32), nullable=False, server_default="individual"),  # individual | collaborative
        sa.Column("user_role", sa.String(length=128), nullable=True),
        sa.Column("evidence_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("ix_projects_portfolio", "projects", ["portfolio_id"], unique=False)

    op.create_table(
        "snapshots",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("project_id", sa.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_zip_name", sa.String(length=512), nullable=False),
        sa.Column("source_zip_sha256", sa.String(length=64), nullable=False),
        sa.Column("ingested_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("snapshot_label", sa.String(length=128), nullable=True),
    )
    op.create_index("ix_snapshots_project_time", "snapshots", ["project_id", "ingested_at"], unique=False)
    op.create_index("ux_snapshots_project_ziphash", "snapshots", ["project_id", "source_zip_sha256"], unique=True)

    # Content-addressed file store (dedupe + safe deletion)
    op.create_table(
        "file_blobs",
        sa.Column("sha256", sa.String(length=64), primary_key=True),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("mime_type", sa.String(length=128), nullable=True),
        sa.Column("stored_path", sa.String(length=1024), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )

    op.create_table(
        "snapshot_files",
        sa.Column("snapshot_id", sa.UUID(as_uuid=True), sa.ForeignKey("snapshots.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("relative_path", sa.String(length=1024), primary_key=True),
        sa.Column("file_sha256", sa.String(length=64), sa.ForeignKey("file_blobs.sha256", ondelete="RESTRICT"), nullable=False),
        sa.Column("last_modified_ts", sa.DateTime(timezone=True), nullable=True),
        sa.Column("file_mode", sa.Integer(), nullable=True),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
    )
    op.create_index("ix_snapshot_files_sha", "snapshot_files", ["file_sha256"], unique=False)

    # Analyses (local ML vs external LLM vs parsers vs git metrics)
    op.create_table(
        "analyses",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("snapshot_id", sa.UUID(as_uuid=True), sa.ForeignKey("snapshots.id", ondelete="CASCADE"), nullable=False),
        sa.Column("analysis_type", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("output_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("provenance_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("ix_analyses_snapshot_type", "analyses", ["snapshot_id", "analysis_type"], unique=False)

    op.create_table(
        "skills",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("skill_name", sa.String(length=200), nullable=False, unique=True),
        sa.Column("category", sa.String(length=128), nullable=True),
    )

    op.create_table(
        "analysis_skills",
        sa.Column("analysis_id", sa.UUID(as_uuid=True), sa.ForeignKey("analyses.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("skill_id", sa.UUID(as_uuid=True), sa.ForeignKey("skills.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("evidence_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
    )

    # Collaboration / contributions
    op.create_table(
        "contributors",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("canonical_name", sa.String(length=256), nullable=False),
        sa.Column("email", sa.String(length=256), nullable=True),
    )
    op.create_index("ix_contributors_name", "contributors", ["canonical_name"], unique=False)

    op.create_table(
        "project_contributors",
        sa.Column("project_id", sa.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("contributor_id", sa.UUID(as_uuid=True), sa.ForeignKey("contributors.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("is_user", sa.Boolean(), nullable=False, server_default=sa.text("FALSE")),
    )

    op.create_table(
        "contribution_events",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("snapshot_id", sa.UUID(as_uuid=True), sa.ForeignKey("snapshots.id", ondelete="CASCADE"), nullable=False),
        sa.Column("contributor_id", sa.UUID(as_uuid=True), sa.ForeignKey("contributors.id", ondelete="CASCADE"), nullable=False),
        sa.Column("activity_type", sa.String(length=64), nullable=False),  # code | test | doc | design | other
        sa.Column("commit_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("file_change_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("lines_added", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("lines_deleted", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("ix_contrib_snapshot", "contribution_events", ["snapshot_id"], unique=False)

    # Resume / portfolio textual representations (Milestone 2)
    op.create_table(
        "resume_items",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("project_id", sa.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("content_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )

    op.create_table(
        "portfolio_showcases",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("project_id", sa.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("thumbnail_blob_sha256", sa.String(length=64), sa.ForeignKey("file_blobs.sha256", ondelete="SET NULL"), nullable=True),
        sa.Column("content_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )


def downgrade():
    op.drop_table("portfolio_showcases")
    op.drop_table("resume_items")
    op.drop_index("ix_contrib_snapshot", table_name="contribution_events")
    op.drop_table("contribution_events")
    op.drop_table("project_contributors")
    op.drop_index("ix_contributors_name", table_name="contributors")
    op.drop_table("contributors")
    op.drop_table("analysis_skills")
    op.drop_table("skills")
    op.drop_index("ix_analyses_snapshot_type", table_name="analyses")
    op.drop_table("analyses")
    op.drop_index("ix_snapshot_files_sha", table_name="snapshot_files")
    op.drop_table("snapshot_files")
    op.drop_table("file_blobs")
    op.drop_index("ux_snapshots_project_ziphash", table_name="snapshots")
    op.drop_index("ix_snapshots_project_time", table_name="snapshots")
    op.drop_table("snapshots")
    op.drop_index("ix_projects_portfolio", table_name="projects")
    op.drop_table("projects")
    op.drop_index("ix_portfolios_user", table_name="portfolios")
    op.drop_table("portfolios")
    op.drop_index("ix_privacy_consents_user_type", table_name="privacy_consents")
    op.drop_table("privacy_consents")
    op.drop_table("user_config")
    op.drop_table("users")
