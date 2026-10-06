"""Unified Quality owner and bounded operational observations."""
from alembic import op
revision = "20261006_69"
down_revision = "20261005_68"
branch_labels = None
depends_on = None

DDL = [
    """CREATE TABLE quality_cases (
	id UUID NOT NULL,
	key VARCHAR(160) NOT NULL,
	lifecycle VARCHAR(20) NOT NULL,
	cohorts JSONB NOT NULL,
	aliases JSONB NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	CONSTRAINT pk_quality_cases PRIMARY KEY (id),
	CONSTRAINT ck_quality_case_lifecycle CHECK (lifecycle IN ('ACTIVE','RETIRED')),
	CONSTRAINT uq_quality_cases_key UNIQUE (key)
)""",
    """CREATE TABLE quality_case_versions (
	id UUID NOT NULL,
	case_id UUID NOT NULL,
	version INTEGER NOT NULL,
	fingerprint VARCHAR(64) NOT NULL,
	definition JSONB NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	CONSTRAINT pk_quality_case_versions PRIMARY KEY (id),
	CONSTRAINT uq_quality_case_version UNIQUE (case_id, version),
	CONSTRAINT uq_quality_case_fingerprint UNIQUE (case_id, fingerprint),
	CONSTRAINT fk_quality_case_versions_case_id_quality_cases FOREIGN KEY(case_id) REFERENCES quality_cases (id)
)""",
    """CREATE TABLE quality_campaigns (
	id UUID NOT NULL,
	key VARCHAR(160) NOT NULL,
	version INTEGER NOT NULL,
	name VARCHAR(200) NOT NULL,
	fingerprint VARCHAR(64) NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	CONSTRAINT pk_quality_campaigns PRIMARY KEY (id),
	CONSTRAINT uq_quality_campaign_version UNIQUE (key, version),
	CONSTRAINT uq_quality_campaign_fingerprint UNIQUE (key, fingerprint)
)""",
    """CREATE TABLE quality_campaign_members (
	campaign_id UUID NOT NULL,
	case_version_id UUID NOT NULL,
	ordinal INTEGER NOT NULL,
	cohorts JSONB NOT NULL,
	CONSTRAINT pk_quality_campaign_members PRIMARY KEY (campaign_id, case_version_id),
	CONSTRAINT fk_quality_campaign_members_campaign_id_quality_campaigns FOREIGN KEY(campaign_id) REFERENCES quality_campaigns (id),
	CONSTRAINT fk_quality_campaign_members_case_version_id_quality_cas_f24c FOREIGN KEY(case_version_id) REFERENCES quality_case_versions (id)
)""",
    """CREATE TABLE quality_experiments (
	id UUID NOT NULL,
	case_id UUID NOT NULL,
	case_version_id UUID NOT NULL,
	version INTEGER NOT NULL,
	fingerprint VARCHAR(64) NOT NULL,
	definition JSONB NOT NULL,
	authority_identity VARCHAR(255) NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	CONSTRAINT pk_quality_experiments PRIMARY KEY (id),
	CONSTRAINT uq_quality_experiment_version UNIQUE (case_id, version),
	CONSTRAINT fk_quality_experiments_case_id_quality_cases FOREIGN KEY(case_id) REFERENCES quality_cases (id),
	CONSTRAINT fk_quality_experiments_case_version_id_quality_case_versions FOREIGN KEY(case_version_id) REFERENCES quality_case_versions (id)
)""",
    """CREATE TABLE quality_campaign_runs (
	id UUID NOT NULL,
	campaign_id UUID NOT NULL,
	experiment_id UUID,
	variant_key VARCHAR(80),
	watt_revision VARCHAR(64) NOT NULL,
	policy_fingerprint VARCHAR(64) NOT NULL,
	configuration JSONB NOT NULL,
	state VARCHAR(20) NOT NULL,
	authority_identity VARCHAR(255) NOT NULL,
	lease_token UUID,
	lease_expires_at TIMESTAMP WITH TIME ZONE,
	finished_at TIMESTAMP WITH TIME ZONE,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	CONSTRAINT pk_quality_campaign_runs PRIMARY KEY (id),
	CONSTRAINT ck_quality_run_state CHECK (state IN ('QUEUED','RUNNING','PASS','FAIL','BLOCKED')),
	CONSTRAINT fk_quality_campaign_runs_campaign_id_quality_campaigns FOREIGN KEY(campaign_id) REFERENCES quality_campaigns (id),
	CONSTRAINT fk_quality_campaign_runs_experiment_id_quality_experiments FOREIGN KEY(experiment_id) REFERENCES quality_experiments (id)
)""",
    """CREATE TABLE quality_case_runs (
	id UUID NOT NULL,
	campaign_run_id UUID NOT NULL,
	case_version_id UUID NOT NULL,
	attempt INTEGER NOT NULL,
	state VARCHAR(20) NOT NULL,
	lineage JSONB NOT NULL,
	elapsed_seconds FLOAT,
	finished_at TIMESTAMP WITH TIME ZONE,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	CONSTRAINT pk_quality_case_runs PRIMARY KEY (id),
	CONSTRAINT uq_quality_case_attempt UNIQUE (campaign_run_id, case_version_id, attempt),
	CONSTRAINT fk_quality_case_runs_campaign_run_id_quality_campaign_runs FOREIGN KEY(campaign_run_id) REFERENCES quality_campaign_runs (id),
	CONSTRAINT fk_quality_case_runs_case_version_id_quality_case_versions FOREIGN KEY(case_version_id) REFERENCES quality_case_versions (id)
)""",
    """CREATE TABLE quality_evaluations (
	id UUID NOT NULL,
	case_run_id UUID NOT NULL,
	evaluator VARCHAR(20) NOT NULL,
	outcome VARCHAR(20) NOT NULL,
	record JSONB NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	CONSTRAINT pk_quality_evaluations PRIMARY KEY (id),
	CONSTRAINT fk_quality_evaluations_case_run_id_quality_case_runs FOREIGN KEY(case_run_id) REFERENCES quality_case_runs (id)
)""",
    """CREATE TABLE quality_findings (
	id UUID NOT NULL,
	case_run_id UUID NOT NULL,
	cluster_key VARCHAR(64) NOT NULL,
	stage VARCHAR(40),
	finding_code VARCHAR(100) NOT NULL,
	certainty VARCHAR(30) NOT NULL,
	state VARCHAR(20) NOT NULL,
	evidence_refs JSONB NOT NULL,
	regression_case_id UUID,
	regression_promotion JSONB,
	closure JSONB,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	CONSTRAINT pk_quality_findings PRIMARY KEY (id),
	CONSTRAINT fk_quality_findings_case_run_id_quality_case_runs FOREIGN KEY(case_run_id) REFERENCES quality_case_runs (id),
	CONSTRAINT fk_quality_findings_regression_case_id_quality_cases FOREIGN KEY(regression_case_id) REFERENCES quality_cases (id)
)""",
    """CREATE TABLE quality_preferences (
	id UUID NOT NULL,
	experiment_id UUID NOT NULL,
	case_id UUID NOT NULL,
	record JSONB NOT NULL,
	authority_identity VARCHAR(255) NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	CONSTRAINT pk_quality_preferences PRIMARY KEY (id),
	CONSTRAINT fk_quality_preferences_experiment_id_quality_experiments FOREIGN KEY(experiment_id) REFERENCES quality_experiments (id),
	CONSTRAINT fk_quality_preferences_case_id_quality_cases FOREIGN KEY(case_id) REFERENCES quality_cases (id)
)""",
    """CREATE TABLE quality_learning_signals (
	id UUID NOT NULL,
	case_id UUID NOT NULL,
	source_kind VARCHAR(20) NOT NULL,
	source_id UUID NOT NULL,
	owner VARCHAR(40) NOT NULL,
	record JSONB NOT NULL,
	authority_identity VARCHAR(255) NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	CONSTRAINT pk_quality_learning_signals PRIMARY KEY (id),
	CONSTRAINT fk_quality_learning_signals_case_id_quality_cases FOREIGN KEY(case_id) REFERENCES quality_cases (id)
)""",
    """CREATE TABLE quality_promotion_decisions (
	id UUID NOT NULL,
	experiment_id UUID NOT NULL,
	variant_key VARCHAR(80) NOT NULL,
	record JSONB NOT NULL,
	authority_identity VARCHAR(255) NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	CONSTRAINT pk_quality_promotion_decisions PRIMARY KEY (id),
	CONSTRAINT uq_quality_promotion_decision UNIQUE (experiment_id, variant_key),
	CONSTRAINT fk_quality_promotion_decisions_experiment_id_quality_ex_c2b1 FOREIGN KEY(experiment_id) REFERENCES quality_experiments (id)
)""",
    """CREATE TABLE operations_metric_samples (
	id UUID NOT NULL,
	node_id VARCHAR(160) NOT NULL,
	record JSONB NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	CONSTRAINT pk_operations_metric_samples PRIMARY KEY (id)
)""",
    """CREATE INDEX ix_quality_runs_queue ON quality_campaign_runs (state, created_at)""",
    """CREATE INDEX ix_quality_finding_cluster ON quality_findings (cluster_key)""",
    """CREATE INDEX ix_operations_sample_time ON operations_metric_samples (node_id, created_at)""",
]

def upgrade():
    for statement in DDL:
        op.execute(statement)

def downgrade():
    op.drop_table('operations_metric_samples')
    op.drop_table('quality_promotion_decisions')
    op.drop_table('quality_learning_signals')
    op.drop_table('quality_preferences')
    op.drop_table('quality_findings')
    op.drop_table('quality_evaluations')
    op.drop_table('quality_case_runs')
    op.drop_table('quality_campaign_runs')
    op.drop_table('quality_experiments')
    op.drop_table('quality_campaign_members')
    op.drop_table('quality_campaigns')
    op.drop_table('quality_case_versions')
    op.drop_table('quality_cases')
