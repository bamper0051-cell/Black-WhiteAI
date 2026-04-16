#!/usr/bin/env python3
"""
Database Migration Script for BlackBugsAI v4.0

This script initializes the PostgreSQL database schema for:
- Skill memory (successful tool executions)
- Failure memory (failed tool executions)
- User statistics
- Agent sessions
- Task queue
"""
import os
import sys
import psycopg2
from psycopg2 import sql
from datetime import datetime

# Database connection parameters from environment
DB_CONFIG = {
    'host': os.getenv('POSTGRES_HOST', 'localhost'),
    'port': int(os.getenv('POSTGRES_PORT', '5432')),
    'database': os.getenv('POSTGRES_DB', 'blackbugsai'),
    'user': os.getenv('POSTGRES_USER', 'blackbugs'),
    'password': os.getenv('POSTGRES_PASSWORD', ''),
}


def get_connection():
    """Create database connection"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        print(f"❌ Failed to connect to database: {e}")
        sys.exit(1)


def run_migration(conn, version, description, sql_statements):
    """Run a single migration"""
    cursor = conn.cursor()

    try:
        print(f"📦 Running migration {version}: {description}")

        for statement in sql_statements:
            cursor.execute(statement)

        # Record migration
        cursor.execute(
            """
            INSERT INTO schema_migrations (version, description, applied_at)
            VALUES (%s, %s, %s)
            ON CONFLICT (version) DO NOTHING
            """,
            (version, description, datetime.now())
        )

        conn.commit()
        print(f"✅ Migration {version} completed successfully")

    except Exception as e:
        conn.rollback()
        print(f"❌ Migration {version} failed: {e}")
        raise


def init_migrations_table(conn):
    """Initialize migrations tracking table"""
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version VARCHAR(50) PRIMARY KEY,
            description TEXT NOT NULL,
            applied_at TIMESTAMP DEFAULT NOW()
        )
    """)

    conn.commit()
    print("✅ Migrations table initialized")


def migration_001_initial_schema(conn):
    """Initial database schema"""
    statements = [
        # Skill Memory Table
        """
        CREATE TABLE IF NOT EXISTS skill_memory (
            id SERIAL PRIMARY KEY,
            user_id VARCHAR(255) NOT NULL,
            tool_name VARCHAR(255) NOT NULL,
            input_params JSONB NOT NULL,
            output_result JSONB,
            timestamp TIMESTAMP DEFAULT NOW(),
            success_count INTEGER DEFAULT 1,
            CONSTRAINT unique_skill UNIQUE (user_id, tool_name, input_params)
        )
        """,

        # Indexes for skill_memory
        """
        CREATE INDEX IF NOT EXISTS idx_skill_user_tool
        ON skill_memory(user_id, tool_name)
        """,

        """
        CREATE INDEX IF NOT EXISTS idx_skill_timestamp
        ON skill_memory(timestamp DESC)
        """,

        # Failure Memory Table
        """
        CREATE TABLE IF NOT EXISTS failure_memory (
            id SERIAL PRIMARY KEY,
            user_id VARCHAR(255) NOT NULL,
            tool_name VARCHAR(255) NOT NULL,
            error_message TEXT NOT NULL,
            input_params JSONB NOT NULL,
            timestamp TIMESTAMP DEFAULT NOW(),
            retry_count INTEGER DEFAULT 0
        )
        """,

        # Indexes for failure_memory
        """
        CREATE INDEX IF NOT EXISTS idx_failure_user_tool
        ON failure_memory(user_id, tool_name)
        """,

        """
        CREATE INDEX IF NOT EXISTS idx_failure_timestamp
        ON failure_memory(timestamp DESC)
        """,

        # User Statistics Table
        """
        CREATE TABLE IF NOT EXISTS user_stats (
            user_id VARCHAR(255) PRIMARY KEY,
            total_tasks INTEGER DEFAULT 0,
            successful_tasks INTEGER DEFAULT 0,
            failed_tasks INTEGER DEFAULT 0,
            total_tools_used INTEGER DEFAULT 0,
            last_active TIMESTAMP DEFAULT NOW(),
            created_at TIMESTAMP DEFAULT NOW()
        )
        """,
    ]

    run_migration(conn, "001", "Initial schema with memory tables", statements)


def migration_002_agent_sessions(conn):
    """Add agent sessions tracking"""
    statements = [
        # Agent Sessions Table
        """
        CREATE TABLE IF NOT EXISTS agent_sessions (
            id SERIAL PRIMARY KEY,
            session_id VARCHAR(255) UNIQUE NOT NULL,
            user_id VARCHAR(255) NOT NULL,
            agent_name VARCHAR(255) NOT NULL,
            started_at TIMESTAMP DEFAULT NOW(),
            ended_at TIMESTAMP,
            status VARCHAR(50) DEFAULT 'active',
            context JSONB,
            result JSONB
        )
        """,

        # Indexes
        """
        CREATE INDEX IF NOT EXISTS idx_session_user
        ON agent_sessions(user_id, started_at DESC)
        """,

        """
        CREATE INDEX IF NOT EXISTS idx_session_status
        ON agent_sessions(status)
        """,
    ]

    run_migration(conn, "002", "Add agent sessions tracking", statements)


def migration_003_task_queue(conn):
    """Add task queue tables"""
    statements = [
        # Task Queue Table
        """
        CREATE TABLE IF NOT EXISTS task_queue (
            id SERIAL PRIMARY KEY,
            task_id VARCHAR(255) UNIQUE NOT NULL,
            user_id VARCHAR(255) NOT NULL,
            agent_name VARCHAR(255) NOT NULL,
            task_data JSONB NOT NULL,
            status VARCHAR(50) DEFAULT 'pending',
            priority INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT NOW(),
            started_at TIMESTAMP,
            completed_at TIMESTAMP,
            result JSONB,
            error TEXT
        )
        """,

        # Indexes
        """
        CREATE INDEX IF NOT EXISTS idx_task_status_priority
        ON task_queue(status, priority DESC, created_at)
        """,

        """
        CREATE INDEX IF NOT EXISTS idx_task_user
        ON task_queue(user_id, created_at DESC)
        """,
    ]

    run_migration(conn, "003", "Add task queue tables", statements)


def migration_004_n8n_schema(conn):
    """Create n8n schema (separate from main schema)"""
    statements = [
        # Create n8n schema
        """
        CREATE SCHEMA IF NOT EXISTS n8n
        """,

        # Grant permissions
        f"""
        GRANT ALL PRIVILEGES ON SCHEMA n8n TO {DB_CONFIG['user']}
        """,
    ]

    run_migration(conn, "004", "Create n8n schema", statements)


def migration_005_add_indexes(conn):
    """Add additional performance indexes"""
    statements = [
        # Skill memory additional indexes
        """
        CREATE INDEX IF NOT EXISTS idx_skill_success_count
        ON skill_memory(success_count DESC)
        WHERE success_count > 1
        """,

        # Failure memory additional indexes
        """
        CREATE INDEX IF NOT EXISTS idx_failure_recent
        ON failure_memory(timestamp DESC)
        WHERE timestamp > NOW() - INTERVAL '7 days'
        """,

        # User stats index
        """
        CREATE INDEX IF NOT EXISTS idx_user_active
        ON user_stats(last_active DESC)
        """,
    ]

    run_migration(conn, "005", "Add performance indexes", statements)


def check_migration_status(conn):
    """Check which migrations have been applied"""
    cursor = conn.cursor()

    cursor.execute("""
        SELECT version, description, applied_at
        FROM schema_migrations
        ORDER BY version
    """)

    migrations = cursor.fetchall()

    if migrations:
        print("\n📋 Applied migrations:")
        for version, description, applied_at in migrations:
            print(f"  ✓ {version}: {description} (applied {applied_at})")
    else:
        print("\n📋 No migrations applied yet")


def main():
    """Run all migrations"""
    print("🚀 BlackBugsAI Database Migration Tool v4.0")
    print(f"📊 Target database: {DB_CONFIG['database']}@{DB_CONFIG['host']}")
    print()

    # Connect to database
    conn = get_connection()

    # Initialize migrations tracking
    init_migrations_table(conn)

    # Check current status
    check_migration_status(conn)
    print()

    # Run migrations
    try:
        migration_001_initial_schema(conn)
        migration_002_agent_sessions(conn)
        migration_003_task_queue(conn)
        migration_004_n8n_schema(conn)
        migration_005_add_indexes(conn)

        print("\n✅ All migrations completed successfully!")

        # Show final status
        check_migration_status(conn)

    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        sys.exit(1)

    finally:
        conn.close()


if __name__ == "__main__":
    main()
