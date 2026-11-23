"""Add durable issue conversations, run leases and sequenced progress events."""

from alembic import op

revision = "20261112_178"
down_revision = "20261112_177"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("SET LOCAL lock_timeout = '5s'")
    op.execute("""
    CREATE TABLE debug_threads (
            id UUID NOT NULL,
            issue_id UUID NOT NULL,
            environment VARCHAR(64) NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
            PRIMARY KEY (id),
            CONSTRAINT uq_debug_thread_issue_env UNIQUE (issue_id,  environment),
            FOREIGN KEY(issue_id) REFERENCES diagnostic_issues (id) ON DELETE RESTRICT
    )
    """)
    op.execute("CREATE INDEX ix_debug_threads_issue_id ON debug_threads (issue_id)")
    op.execute("""
    CREATE TABLE debug_messages (
            id UUID NOT NULL,
            thread_id UUID NOT NULL,
            actor_id UUID,
            role VARCHAR(16) NOT NULL,
            content TEXT NOT NULL,
            submission_key VARCHAR(128),
            request_hash VARCHAR(64),
            created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
            PRIMARY KEY (id),
            CONSTRAINT uq_debug_message_submission UNIQUE (thread_id,  submission_key),
            FOREIGN KEY(thread_id) REFERENCES debug_threads (id) ON DELETE RESTRICT,
            FOREIGN KEY(actor_id) REFERENCES users (id) ON DELETE SET NULL
    )
    """)
    op.execute("CREATE INDEX ix_debug_messages_thread_id ON debug_messages (thread_id)")
    op.execute("""
    CREATE TABLE debug_runs (
            id UUID NOT NULL,
            thread_id UUID NOT NULL,
            message_id UUID NOT NULL,
            state VARCHAR(32) NOT NULL,
            action VARCHAR(32) NOT NULL,
            evidence JSON NOT NULL,
            config_snapshot JSON NOT NULL,
            cancel_requested BOOLEAN DEFAULT 'false' NOT NULL,
            lease_token UUID,
            lease_until TIMESTAMP WITH TIME ZONE,
            attempt INTEGER DEFAULT '0' NOT NULL,
            error_code VARCHAR(64),
            created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
            PRIMARY KEY (id),
            FOREIGN KEY(thread_id) REFERENCES debug_threads (id) ON DELETE RESTRICT,
            UNIQUE (message_id),
            FOREIGN KEY(message_id) REFERENCES debug_messages (id) ON DELETE RESTRICT
    )
    """)
    op.execute("CREATE INDEX ix_debug_runs_thread_id ON debug_runs (thread_id)")
    op.execute("""
    CREATE UNIQUE INDEX uq_debug_run_active_thread ON debug_runs (thread_id) WHERE state IN
    ('queued', 'investigating', 'editing', 'testing', 'awaiting_authorization', 'deploying',
    'verifying')
    """)
    op.execute("""
    CREATE TABLE debug_run_events (
            id UUID NOT NULL,
            run_id UUID NOT NULL,
            sequence INTEGER NOT NULL,
            kind VARCHAR(32) NOT NULL,
            payload JSON NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
            PRIMARY KEY (id),
            CONSTRAINT uq_debug_run_sequence UNIQUE (run_id,  sequence),
            FOREIGN KEY(run_id) REFERENCES debug_runs (id) ON DELETE RESTRICT
    )
    """)
    op.execute("CREATE INDEX ix_debug_run_events_run_id ON debug_run_events (run_id)")


def downgrade() -> None:
    op.drop_table("debug_run_events")
    op.drop_table("debug_runs")
    op.drop_table("debug_messages")
    op.drop_table("debug_threads")
