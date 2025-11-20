"""
LogStore client extension for Alibaba Cloud SLS.

This module provides a PostgreSQL protocol-based client for LogStore,
enabling workflow execution logs to be stored in a log-style storage system.
"""

import logging
import time
from typing import Any

import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor

from configs import dify_config

logger = logging.getLogger(__name__)


class LogStoreClient:
    """
    LogStore client using PostgreSQL protocol.

    This client connects to Alibaba Cloud LogStore through its PostgreSQL-compatible
    protocol endpoint. It provides connection pooling, query execution, and version
    management for append-only workflow execution logs.
    """

    def __init__(self):
        """Initialize LogStore client with configuration from dify_config."""
        self.config = dify_config.logstore
        self.connection_pool: pool.ThreadedConnectionPool | None = None

    def init_connection_pool(self) -> None:
        """
        Initialize the PostgreSQL connection pool.

        Creates a threaded connection pool with the configured size.
        The project name is used as the database name in the PG protocol.
        """
        if not self.config.LOGSTORE_ENABLED:
            logger.info("LogStore is disabled, skipping connection pool initialization")
            return

        if self.connection_pool is not None:
            logger.warning("LogStore connection pool already initialized")
            return

        try:
            self.connection_pool = pool.ThreadedConnectionPool(
                minconn=1,
                maxconn=self.config.LOGSTORE_CONNECTION_POOL_SIZE,
                host=self.config.LOGSTORE_PG_HOST,
                port=self.config.LOGSTORE_PG_PORT,
                user=self.config.LOGSTORE_PG_USER,
                password=self.config.LOGSTORE_PG_PASSWORD,
                database=self.config.LOGSTORE_PROJECT,  # Project name as database
                cursor_factory=RealDictCursor,  # Return rows as dictionaries
            )
            logger.info(
                "LogStore connection pool initialized: host=%s, port=%s, database=%s",
                self.config.LOGSTORE_PG_HOST,
                self.config.LOGSTORE_PG_PORT,
                self.config.LOGSTORE_PROJECT,
            )
        except Exception as e:
            logger.exception("Failed to initialize LogStore connection pool: %s", e)
            raise

    def close_connection_pool(self) -> None:
        """Close all connections in the pool."""
        if self.connection_pool is not None:
            self.connection_pool.closeall()
            self.connection_pool = None
            logger.info("LogStore connection pool closed")

    def get_version(self) -> int:
        """
        Generate a nanosecond-precision timestamp as version number.

        Returns:
            int: Nanosecond timestamp (e.g., 1732089600123456789)
        """
        return int(time.time() * 1_000_000_000)

    def execute_query(self, sql: str, params: tuple | None = None) -> list[dict[str, Any]]:
        """
        Execute a SELECT query and return results as a list of dictionaries.

        Args:
            sql: SQL query string
            params: Query parameters for parameterized queries

        Returns:
            List of result rows as dictionaries

        Raises:
            psycopg2.Error: If query execution fails
        """
        if self.connection_pool is None:
            raise RuntimeError("LogStore connection pool not initialized")

        conn = None
        try:
            conn = self.connection_pool.getconn()
            conn.set_session(autocommit=True)
            
            with conn.cursor() as cursor:
                cursor.execute(sql, params)
                results = cursor.fetchall()
                return results if results else []
        except psycopg2.Error as e:
            logger.exception("Failed to execute LogStore query: %s", e)
            raise
        finally:
            if conn is not None:
                self.connection_pool.putconn(conn)

    def execute_insert(self, sql: str, params: tuple) -> None:
        """
        Execute an INSERT statement.

        Args:
            sql: INSERT SQL statement
            params: Insert parameters

        Raises:
            psycopg2.Error: If insert execution fails
        """
        if self.connection_pool is None:
            raise RuntimeError("LogStore connection pool not initialized")

        conn = None
        try:
            conn = self.connection_pool.getconn()
            conn.set_session(autocommit=True)
            
            with conn.cursor() as cursor:
                cursor.execute(sql, params)
                logger.debug("LogStore insert executed successfully")
        except psycopg2.Error as e:
            logger.exception("Failed to execute LogStore insert: %s", e)
            raise
        finally:
            if conn is not None:
                self.connection_pool.putconn(conn)

    def init_logstore(self) -> None:
        """
        Initialize LogStore resources (project, logstores, indexes).

        This method should be called during application startup to ensure
        the necessary LogStore resources exist.

        Note: This is a placeholder for future implementation.
        Currently assumes the project and logstores are manually created.
        """
        if not self.config.LOGSTORE_ENABLED:
            return

        logger.info(
            "LogStore initialization: project=%s, workflow_runs=%s, node_executions=%s",
            self.config.LOGSTORE_PROJECT,
            self.config.LOGSTORE_WORKFLOW_RUNS,
            self.config.LOGSTORE_NODE_EXECUTIONS,
        )
        
        # TODO: Implement SLS API calls to:
        # 1. Create project if not exists
        # 2. Create logstores if not exist
        # 3. Create indexes for optimal query performance
        # For now, assume these are created manually through SLS console or CLI

    def health_check(self) -> bool:
        """
        Check if the LogStore connection is healthy.

        Returns:
            bool: True if connection is healthy, False otherwise
        """
        if not self.config.LOGSTORE_ENABLED:
            return True

        if self.connection_pool is None:
            return False

        try:
            result = self.execute_query("SELECT 1 as health")
            return len(result) > 0 and result[0].get("health") == 1
        except Exception as e:
            logger.exception("LogStore health check failed: %s", e)
            return False


# Global LogStore client instance
_logstore_client: LogStoreClient | None = None


def get_logstore_client() -> LogStoreClient:
    """
    Get the global LogStore client instance.

    Returns:
        LogStoreClient: The global client instance

    Raises:
        RuntimeError: If the client has not been initialized
    """
    if _logstore_client is None:
        raise RuntimeError("LogStore client not initialized. Call init_logstore_client() first.")
    return _logstore_client


def init_logstore_client() -> LogStoreClient:
    """
    Initialize the global LogStore client instance.

    Returns:
        LogStoreClient: The initialized client instance
    """
    global _logstore_client
    if _logstore_client is None:
        _logstore_client = LogStoreClient()
        _logstore_client.init_connection_pool()
        _logstore_client.init_logstore()
    return _logstore_client


def close_logstore_client() -> None:
    """Close the global LogStore client instance."""
    global _logstore_client
    if _logstore_client is not None:
        _logstore_client.close_connection_pool()
        _logstore_client = None


def is_enabled() -> bool:
    """Check if LogStore is enabled in configuration."""
    return dify_config.LOGSTORE_ENABLED


def init_app(app) -> None:
    """
    Initialize LogStore extension for Flask app.

    This function is called by app_factory during application startup.
    It initializes the LogStore client if enabled.

    Args:
        app: Flask application instance
    """
    if not is_enabled():
        logger.info("LogStore is disabled, skipping initialization")
        return

    try:
        client = init_logstore_client()
        app.extensions["logstore"] = client
        logger.info("LogStore extension initialized successfully")
    except Exception as e:
        logger.exception("Failed to initialize LogStore extension: %s", e)
        # Don't raise exception to allow app to start without LogStore
        logger.warning("Application will run without LogStore (using fallback storage)")

