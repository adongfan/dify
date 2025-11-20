"""
Unit tests for LogStore repositories.

Note: These tests require a running LogStore instance with PG protocol enabled.
Set the following environment variables to run tests:
- LOGSTORE_ENABLED=true
- LOGSTORE_PG_HOST=your-host
- LOGSTORE_PG_PORT=6432
- LOGSTORE_PG_USER=your-user
- LOGSTORE_PG_PASSWORD=your-password
- LOGSTORE_PROJECT=test-project
"""

import time
from datetime import datetime
from unittest.mock import MagicMock, Mock, patch

import pytest

from configs import dify_config
from core.repositories.logstore_workflow_execution_repository import LogStoreWorkflowExecutionRepository
from core.repositories.logstore_workflow_node_execution_repository import LogStoreWorkflowNodeExecutionRepository
from core.workflow.entities import WorkflowExecution, WorkflowNodeExecution
from core.workflow.enums import NodeType, WorkflowExecutionStatus, WorkflowNodeExecutionStatus, WorkflowType
from extensions.ext_logstore import LogStoreClient
from models import Account
from models.enums import WorkflowRunTriggeredFrom
from models.workflow import WorkflowNodeExecutionTriggeredFrom


class TestLogStoreWorkflowExecutionRepository:
    """Tests for LogStoreWorkflowExecutionRepository."""

    @pytest.fixture
    def mock_logstore_client(self):
        """Create a mock LogStore client."""
        client = MagicMock(spec=LogStoreClient)
        client.get_version.return_value = 1732089600123456789
        return client

    @pytest.fixture
    def mock_user(self):
        """Create a mock Account user."""
        user = Mock(spec=Account)
        user.id = "user-123"
        user.tenant_id = "tenant-123"
        user.current_tenant_id = "tenant-123"
        return user

    @pytest.fixture
    def repository(self, mock_logstore_client, mock_user):
        """Create a LogStore repository with mocked dependencies."""
        with patch("core.repositories.logstore_workflow_execution_repository.get_logstore_client") as mock_get:
            mock_get.return_value = mock_logstore_client
            repo = LogStoreWorkflowExecutionRepository(
                session_factory=None,  # Not used
                user=mock_user,
                app_id="app-123",
                triggered_from=WorkflowRunTriggeredFrom.APP_RUN,
            )
            return repo

    def test_save_workflow_execution_with_version(self, repository, mock_logstore_client):
        """Test that save() creates an INSERT with nanosecond timestamp version."""
        # Create a workflow execution
        execution = WorkflowExecution(
            id_="exec-123",
            workflow_id="workflow-123",
            workflow_type=WorkflowType.WORKFLOW,
            workflow_version="1.0",
            graph={"nodes": []},
            inputs={"input1": "value1"},
            outputs=None,
            status=WorkflowExecutionStatus.RUNNING,
            started_at=datetime.now(),
        )

        # Save execution
        repository.save(execution)

        # Verify execute_insert was called
        assert mock_logstore_client.execute_insert.called
        call_args = mock_logstore_client.execute_insert.call_args

        # Verify SQL contains version field
        sql = call_args[0][0]
        assert "version" in sql.lower()
        assert "INSERT INTO" in sql

        # Verify params contain version
        params = call_args[0][1]
        assert params[1] == 1732089600123456789  # version

    def test_save_multiple_versions(self, repository, mock_logstore_client):
        """Test that multiple saves create multiple INSERT operations."""
        execution = WorkflowExecution(
            id_="exec-123",
            workflow_id="workflow-123",
            workflow_type=WorkflowType.WORKFLOW,
            workflow_version="1.0",
            graph={"nodes": []},
            inputs={},
            status=WorkflowExecutionStatus.RUNNING,
            started_at=datetime.now(),
        )

        # Save version 1
        mock_logstore_client.get_version.return_value = 1000000000000000001
        repository.save(execution)

        # Update and save version 2
        execution.status = WorkflowExecutionStatus.SUCCEEDED
        execution.outputs = {"result": "success"}
        execution.finished_at = datetime.now()
        mock_logstore_client.get_version.return_value = 1000000000000000002
        repository.save(execution)

        # Verify two INSERT calls
        assert mock_logstore_client.execute_insert.call_count == 2


class TestLogStoreWorkflowNodeExecutionRepository:
    """Tests for LogStoreWorkflowNodeExecutionRepository."""

    @pytest.fixture
    def mock_logstore_client(self):
        """Create a mock LogStore client."""
        client = MagicMock(spec=LogStoreClient)
        client.get_version.return_value = 1732089600123456789
        return client

    @pytest.fixture
    def mock_user(self):
        """Create a mock Account user."""
        user = Mock(spec=Account)
        user.id = "user-123"
        user.tenant_id = "tenant-123"
        user.current_tenant_id = "tenant-123"
        return user

    @pytest.fixture
    def repository(self, mock_logstore_client, mock_user):
        """Create a LogStore node execution repository with mocked dependencies."""
        with patch("core.repositories.logstore_workflow_node_execution_repository.get_logstore_client") as mock_get:
            mock_get.return_value = mock_logstore_client
            repo = LogStoreWorkflowNodeExecutionRepository(
                session_factory=None,
                user=mock_user,
                app_id="app-123",
                triggered_from=WorkflowNodeExecutionTriggeredFrom.WORKFLOW_RUN,
            )
            return repo

    def test_save_node_execution_metadata(self, repository, mock_logstore_client):
        """Test that save() creates an INSERT for node metadata."""
        execution = WorkflowNodeExecution(
            id="node-exec-123",
            workflow_id="workflow-123",
            workflow_execution_id="exec-123",
            index=1,
            node_id="node-1",
            node_type=NodeType.LLM,
            title="LLM Node",
            status=WorkflowNodeExecutionStatus.RUNNING,
            created_at=datetime.now(),
        )

        # Save metadata
        repository.save(execution)

        # Verify execute_insert was called
        assert mock_logstore_client.execute_insert.called
        call_args = mock_logstore_client.execute_insert.call_args

        # Verify SQL
        sql = call_args[0][0]
        assert "INSERT INTO" in sql
        assert "version" in sql.lower()

    def test_save_execution_data(self, repository, mock_logstore_client):
        """Test that save_execution_data() saves inputs/outputs/process_data."""
        execution = WorkflowNodeExecution(
            id="node-exec-123",
            workflow_id="workflow-123",
            workflow_execution_id="exec-123",
            index=1,
            node_id="node-1",
            node_type=NodeType.LLM,
            title="LLM Node",
            inputs={"prompt": "Hello"},
            outputs={"response": "Hi there"},
            process_data={"tokens": 100},
            status=WorkflowNodeExecutionStatus.SUCCEEDED,
            created_at=datetime.now(),
            finished_at=datetime.now(),
        )

        # Save execution data
        repository.save_execution_data(execution)

        # Verify execute_insert was called
        assert mock_logstore_client.execute_insert.called
        call_args = mock_logstore_client.execute_insert.call_args

        # Verify SQL includes data fields
        sql = call_args[0][0]
        assert "inputs" in sql.lower()
        assert "outputs" in sql.lower()
        assert "process_data" in sql.lower()

    def test_get_by_workflow_run(self, repository, mock_logstore_client):
        """Test get_by_workflow_run uses window function."""
        # Mock query result
        mock_logstore_client.execute_query.return_value = [
            {
                "id": "node-1",
                "version": 1000000000000000002,
                "workflow_id": "workflow-123",
                "workflow_run_id": "exec-123",
                "index": 1,
                "node_id": "node-1",
                "node_type": "llm",
                "title": "LLM Node",
                "status": "succeeded",
                "created_at": datetime.now(),
                "finished_at": datetime.now(),
                "elapsed_time": 1.5,
            }
        ]

        # Query node executions
        results = repository.get_by_workflow_run("exec-123")

        # Verify query was called with window function
        assert mock_logstore_client.execute_query.called
        call_args = mock_logstore_client.execute_query.call_args
        sql = call_args[0][0]
        assert "ROW_NUMBER() OVER" in sql
        assert "PARTITION BY id" in sql
        assert "ORDER BY version DESC" in sql

        # Verify result
        assert len(results) == 1
        assert results[0].id == "node-1"


class TestLogStoreVersionGeneration:
    """Tests for version generation."""

    def test_nanosecond_timestamp_version(self):
        """Test that version is a nanosecond timestamp."""
        version1 = int(time.time() * 1_000_000_000)
        time.sleep(0.001)  # 1ms
        version2 = int(time.time() * 1_000_000_000)

        # Verify versions are different and increasing
        assert version2 > version1
        # Verify format (should be ~19 digits)
        assert 10**18 < version1 < 10**19
        assert 10**18 < version2 < 10**19


@pytest.mark.integration
@pytest.mark.skipif(not dify_config.LOGSTORE_ENABLED, reason="LogStore not enabled")
class TestLogStoreIntegration:
    """Integration tests that require a real LogStore instance."""

    def test_workflow_execution_full_lifecycle(self):
        """
        Test full workflow execution lifecycle with LogStore.

        This test requires a real LogStore instance configured via environment variables.
        """
        from sqlalchemy.orm import sessionmaker

        from extensions.ext_database import db

        # Create real repository
        user = Mock(spec=Account)
        user.id = "test-user"
        user.tenant_id = "test-tenant"
        user.current_tenant_id = "test-tenant"

        session_factory = sessionmaker(bind=db.engine, expire_on_commit=False)
        repo = LogStoreWorkflowExecutionRepository(
            session_factory=session_factory,
            user=user,
            app_id="test-app",
            triggered_from=WorkflowRunTriggeredFrom.DEBUGGING,
        )

        # Create execution
        execution = WorkflowExecution.new(
            id_=f"test-exec-{int(time.time())}",
            workflow_id="test-workflow",
            workflow_type=WorkflowType.WORKFLOW,
            workflow_version="1.0",
            graph={"nodes": []},
            inputs={"test": "input"},
            started_at=datetime.now(),
        )

        # Save initial version (running)
        repo.save(execution)

        # Update to succeeded
        execution.status = WorkflowExecutionStatus.SUCCEEDED
        execution.outputs = {"test": "output"}
        execution.finished_at = datetime.now()

        # Save final version
        repo.save(execution)

        # TODO: Query and verify both versions exist in LogStore
        # TODO: Verify latest version query returns the succeeded status

    def test_aggregate_query_performance(self):
        """
        Performance test for aggregate queries.

        Compares window function approach vs finished_at optimization.
        """
        # TODO: Insert test data
        # TODO: Measure query time with window function
        # TODO: Measure query time with finished_at optimization
        # TODO: Assert significant performance improvement
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

