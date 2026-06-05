"""Tiny pyodbc helper shared by the pipeline steps."""

import os

import pyodbc


def get_connection() -> pyodbc.Connection:
    """Open a connection using the ODBC connection string app setting."""
    return pyodbc.connect(os.environ["SqlOdbcConnectionString"])
