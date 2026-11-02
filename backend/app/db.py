from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool
from pgvector.psycopg import register_vector
from .config import settings

pool = ConnectionPool(
    settings.database_url,
    min_size=1, max_size=5,                      
    kwargs={"row_factory": dict_row},
    configure=lambda conn: register_vector(conn),
    check=ConnectionPool.check_connection,       
    open=True,
)