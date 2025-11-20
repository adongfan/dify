-- LogStore Table Schema for Dify Workflow Execution Logs
-- 
-- These tables are designed for Alibaba Cloud LogStore with PostgreSQL protocol.
-- They use an append-only model with nanosecond timestamp versions.
--
-- Key Features:
-- 1. version: Nanosecond timestamp (BIGINT) for version control
-- 2. finished_at: NULL for running workflows, NOT NULL for completed workflows
-- 3. Indexes optimized for aggregate queries using finished_at
--
-- Performance Optimization:
-- - Use "finished_at IS NOT NULL" to filter completed workflows (10-100x faster)
-- - Only use window functions for running workflows (minimal performance impact)

-- ============================================================================
-- Table: workflow_runs
-- Stores workflow execution logs
-- ============================================================================

CREATE TABLE workflow_runs (
    -- Primary key and version control
    id VARCHAR(255) NOT NULL,
    version BIGINT NOT NULL,  -- Nanosecond timestamp version
    
    -- Tenant and app information
    tenant_id VARCHAR(255) NOT NULL,
    app_id VARCHAR(255) NOT NULL,
    workflow_id VARCHAR(255) NOT NULL,
    triggered_from VARCHAR(255) NOT NULL,
    
    -- Workflow definition
    type VARCHAR(50) NOT NULL,
    workflow_version VARCHAR(255) NOT NULL,
    graph TEXT,  -- JSON: workflow graph definition
    
    -- Execution data
    inputs TEXT,  -- JSON: workflow inputs
    outputs TEXT,  -- JSON: workflow outputs
    
    -- Execution state
    status VARCHAR(50) NOT NULL,  -- running, succeeded, failed, stopped, partial-succeeded
    error TEXT,  -- Error message if failed
    total_tokens INT DEFAULT 0,
    total_steps INT DEFAULT 0,
    exceptions_count INT DEFAULT 0,
    
    -- Creator information
    created_by VARCHAR(255) NOT NULL,
    created_by_role VARCHAR(50) NOT NULL,  -- account, end_user
    
    -- Timing information
    created_at TIMESTAMP NOT NULL,  -- Workflow start time (same for all versions)
    finished_at TIMESTAMP,  -- NULL for running, NOT NULL for completed (KEY FIELD)
    elapsed_time FLOAT DEFAULT 0
);

-- Indexes for workflow_runs
-- These indexes are critical for query performance

-- Index for getting latest version of a specific workflow
CREATE INDEX idx_workflow_runs_id_version ON workflow_runs(id, version DESC);

-- Index for optimized aggregate queries on completed workflows
CREATE INDEX idx_workflow_runs_finished_at ON workflow_runs(finished_at);

-- Index for tenant/app/trigger filtering
CREATE INDEX idx_workflow_runs_tenant_app_triggered ON workflow_runs(tenant_id, app_id, triggered_from);

-- Index for time-based queries
CREATE INDEX idx_workflow_runs_created_at ON workflow_runs(created_at);

-- Composite index for status-based aggregate queries
CREATE INDEX idx_workflow_runs_status_finished ON workflow_runs(status, finished_at);

-- ============================================================================
-- Table: workflow_node_executions
-- Stores workflow node execution logs
-- ============================================================================

CREATE TABLE workflow_node_executions (
    -- Primary key and version control
    id VARCHAR(255) NOT NULL,
    version BIGINT NOT NULL,  -- Nanosecond timestamp version
    
    -- Basic information
    tenant_id VARCHAR(255) NOT NULL,
    app_id VARCHAR(255) NOT NULL,
    workflow_id VARCHAR(255) NOT NULL,
    workflow_run_id VARCHAR(255),  -- NULL for single-step debugging
    
    -- Node information
    index INT NOT NULL,  -- Sequence number for display order
    predecessor_node_id VARCHAR(255),
    node_execution_id VARCHAR(255),
    node_id VARCHAR(255) NOT NULL,
    node_type VARCHAR(255) NOT NULL,
    title VARCHAR(255) NOT NULL,
    
    -- Execution data (may be truncated)
    inputs TEXT,  -- JSON: node inputs
    process_data TEXT,  -- JSON: intermediate processing data
    outputs TEXT,  -- JSON: node outputs
    
    -- Execution state
    status VARCHAR(255) NOT NULL,  -- running, succeeded, failed
    error TEXT,  -- Error message if failed
    elapsed_time FLOAT DEFAULT 0,
    execution_metadata TEXT,  -- JSON: metadata (tokens, cost, etc.)
    
    -- Creator information
    created_by VARCHAR(255) NOT NULL,
    created_by_role VARCHAR(255) NOT NULL,
    
    -- Timing information
    created_at TIMESTAMP NOT NULL,
    finished_at TIMESTAMP  -- NULL for running, NOT NULL for completed
);

-- Indexes for workflow_node_executions

-- Index for getting latest version of a specific node execution
CREATE INDEX idx_node_exec_id_version ON workflow_node_executions(id, version DESC);

-- Index for querying nodes by workflow run
CREATE INDEX idx_node_exec_workflow_run ON workflow_node_executions(workflow_run_id);

-- Index for time-based queries
CREATE INDEX idx_node_exec_created_at ON workflow_node_executions(created_at);

-- Index for tenant/app filtering
CREATE INDEX idx_node_exec_tenant_app ON workflow_node_executions(tenant_id, app_id);

-- Index for status-based queries
CREATE INDEX idx_node_exec_status_finished ON workflow_node_executions(status, finished_at);

-- ============================================================================
-- Query Examples
-- ============================================================================

-- Example 1: Get latest version of a specific workflow run
-- (Uses idx_workflow_runs_id_version)
/*
WITH latest AS (
    SELECT *,
           ROW_NUMBER() OVER (PARTITION BY id ORDER BY version DESC) AS rn
    FROM workflow_runs
    WHERE id = 'workflow-run-uuid'
)
SELECT * FROM latest WHERE rn = 1;
*/

-- Example 2: Count completed workflows by status (OPTIMIZED - No window function)
-- (Uses idx_workflow_runs_status_finished)
/*
SELECT status, COUNT(DISTINCT id) as count
FROM workflow_runs
WHERE tenant_id = 'tenant-uuid'
  AND app_id = 'app-uuid'
  AND finished_at IS NOT NULL
GROUP BY status;
*/

-- Example 3: Daily statistics for completed workflows (OPTIMIZED - No window function)
-- (Uses idx_workflow_runs_finished_at and idx_workflow_runs_created_at)
/*
SELECT
    DATE_TRUNC('day', created_at) as date,
    COUNT(DISTINCT id) as runs,
    SUM(total_tokens) as total_tokens
FROM workflow_runs
WHERE tenant_id = 'tenant-uuid'
  AND app_id = 'app-uuid'
  AND finished_at IS NOT NULL
  AND created_at >= '2024-01-01'
GROUP BY DATE_TRUNC('day', created_at)
ORDER BY date DESC;
*/

-- Example 4: Count running workflows (needs window function, but usually few records)
/*
WITH latest AS (
    SELECT id, status,
           ROW_NUMBER() OVER (PARTITION BY id ORDER BY version DESC) AS rn
    FROM workflow_runs
    WHERE tenant_id = 'tenant-uuid'
      AND app_id = 'app-uuid'
)
SELECT COUNT(*) as running_count
FROM latest
WHERE rn = 1 AND status = 'running';
*/

-- Example 5: Get all node executions for a workflow run
-- (Uses idx_node_exec_workflow_run and idx_node_exec_id_version)
/*
WITH latest_nodes AS (
    SELECT *,
           ROW_NUMBER() OVER (PARTITION BY id ORDER BY version DESC) AS rn
    FROM workflow_node_executions
    WHERE workflow_run_id = 'workflow-run-uuid'
)
SELECT * FROM latest_nodes
WHERE rn = 1
ORDER BY index ASC;
*/

-- ============================================================================
-- Notes
-- ============================================================================
--
-- 1. Version Management:
--    - Each save() operation creates a new version with a nanosecond timestamp
--    - version = int(time.time() * 1_000_000_000)
--    - No UPDATE or DELETE operations (append-only)
--
-- 2. Performance Optimization:
--    - finished_at IS NOT NULL identifies final versions of completed workflows
--    - This allows COUNT(DISTINCT id) without expensive window functions
--    - Performance improvement: 10-100x for aggregate queries
--
-- 3. Query Patterns:
--    - For completed workflows: Use finished_at IS NOT NULL (fast)
--    - For running workflows: Use window function (slow, but few records)
--    - For specific workflow: Use window function with id filter (fast with index)
--
-- 4. Index Usage:
--    - finished_at index: Critical for aggregate query performance
--    - (id, version DESC) index: Fast latest version lookup
--    - (status, finished_at) composite: Optimized status-based aggregations
--
-- 5. Data Retention:
--    - LogStore supports automatic data retention policies
--    - Configure retention period based on compliance requirements
--    - Old versions can be automatically purged by LogStore

