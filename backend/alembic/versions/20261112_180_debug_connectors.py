"""Enroll scoped laptop connectors and persist retry-safe tool delivery and probes."""

from alembic import op

revision = "20261112_180"
down_revision = "20261112_179"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("SET LOCAL lock_timeout = '5s'")
    op.execute("""
CREATE TABLE debug_connectors (
	id UUID NOT NULL,
	actor_id UUID,
	name VARCHAR(80) NOT NULL,
	environment VARCHAR(64) NOT NULL,
	repository VARCHAR(200) NOT NULL,
	token_hash VARCHAR(64) NOT NULL,
	revoked BOOLEAN DEFAULT 'false' NOT NULL,
	capabilities JSON NOT NULL,
	last_seen TIMESTAMP WITH TIME ZONE,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(actor_id) REFERENCES users (id) ON DELETE SET NULL,
	UNIQUE (token_hash)
)
    """)
    op.execute("""
CREATE INDEX ix_debug_connectors_environment ON debug_connectors (environment)
    """)
    op.execute("""
CREATE TABLE debug_connector_calls (
	id UUID NOT NULL,
	connector_id UUID NOT NULL,
	run_id UUID NOT NULL,
	progress_sequence INTEGER DEFAULT '0' NOT NULL,
	call_key VARCHAR(128) NOT NULL,
	tool VARCHAR(80) NOT NULL,
	arguments JSON NOT NULL,
	state VARCHAR(32) NOT NULL,
	result JSON,
	lease_token UUID,
	lease_until TIMESTAMP WITH TIME ZONE,
	request_hash VARCHAR(64) NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT uq_debug_connector_run_call UNIQUE (run_id, call_key),
	FOREIGN KEY(connector_id) REFERENCES debug_connectors (id) ON DELETE RESTRICT,
	FOREIGN KEY(run_id) REFERENCES debug_runs (id) ON DELETE RESTRICT
)
    """)
    op.execute("""
CREATE INDEX ix_debug_connector_calls_connector_id ON debug_connector_calls (connector_id)
    """)
    op.execute("""
CREATE INDEX ix_debug_connector_calls_run_id ON debug_connector_calls (run_id)
    """)
    op.execute("""
CREATE TABLE debug_connector_probes (
	id UUID NOT NULL,
	connector_id UUID NOT NULL,
	actor_id UUID NOT NULL,
	model VARCHAR(300) NOT NULL,
	release_commit VARCHAR(40) NOT NULL,
	state VARCHAR(32) NOT NULL,
	result JSON,
	lease_token UUID,
	lease_until TIMESTAMP WITH TIME ZONE,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(connector_id) REFERENCES debug_connectors (id) ON DELETE RESTRICT,
	FOREIGN KEY(actor_id) REFERENCES users (id) ON DELETE RESTRICT
)
    """)
    op.execute("""
CREATE INDEX ix_debug_connector_probes_connector_id ON debug_connector_probes (connector_id)
    """)
    op.execute("""
CREATE UNIQUE INDEX uq_debug_probe_active_connector ON debug_connector_probes (connector_id) WHERE state IN ('queued','running')
    """)


def downgrade() -> None:
    op.drop_table("debug_connector_probes")
    op.drop_table("debug_connector_calls")
    op.drop_table("debug_connectors")
