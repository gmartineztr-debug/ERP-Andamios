import os
import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
from contextlib import contextmanager
import streamlit as st

load_dotenv()

# ================================================
# CONNECTION POOLING
# ================================================

@st.cache_resource
def get_connection_pool():
    """
    Creates a connection pool for the Supabase database.
    Cached as a resource to persist across Streamlit reloads.
    """
    return pool.ThreadedConnectionPool(
        minconn=1,
        maxconn=20,
        host=os.getenv('SUPABASE_HOST'),
        port=os.getenv('SUPABASE_PORT'),
        database=os.getenv('SUPABASE_DB'),
        user=os.getenv('SUPABASE_USER'),
        password=os.getenv('SUPABASE_PASSWORD')
    )

def get_connection():
    """Gets a connection from the pool"""
    return get_connection_pool().getconn()

def release_connection(conn):
    """Returns a connection to the pool"""
    get_connection_pool().putconn(conn)

# ================================================
# CONTEXT MANAGER
# ================================================

@contextmanager
def get_cursor(dict_cursor=True):
    """
    Context manager for database cursors.
    Usage:
        with get_cursor() as (cur, conn):
            cur.execute("SELECT...")
            result = cur.fetchall()
            conn.commit()
    """
    conn = None
    cur = None
    try:
        conn = get_connection()
        # Basic health check: if connection is closed or broken, try once to recreate the pool
        if conn.closed:
            st.warning("Re-estableciendo conexión con la base de datos...")
            get_connection_pool.clear()
            conn = get_connection()

        cursor_factory = RealDictCursor if dict_cursor else None
        cur = conn.cursor(cursor_factory=cursor_factory)
        yield cur, conn
    except Exception as e:
        if conn:
            conn.rollback()
        st.error(f"Error de base de datos: {str(e)}")
        # Raise for the function to handle if needed, but the UI should show the error
        raise e
    finally:
        if cur:
            cur.close()
        if conn:
            release_connection(conn)
