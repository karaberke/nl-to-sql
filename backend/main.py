import os
import re
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Optional

import requests
import sqlglot
from cachetools import TTLCache, cached
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import create_engine, inspect
from sqlalchemy.engine import URL
from sqlglot import exp
from starlette.concurrency import run_in_threadpool

load_dotenv()

# ── Supported databases ───────────────────────────────────────────────────────
# The only place that knows about individual databases. To add one: add an entry
# here plus its SQLAlchemy driver in pyproject.toml.
DIALECTS = {
    "mssql": {
        "driver": "mssql+pyodbc",
        "query":  {"driver": "ODBC Driver 18 for SQL Server", "TrustServerCertificate": "yes",
                   "Connection Timeout": "30"},
        "sqlglot": "tsql",
        "label":   "T-SQL / SQL Server",
        "rules": (
            "Use TOP N (not LIMIT) for row limits.\n"
            "For dates use GETDATE(), DATEADD(), DATEDIFF() — not NOW().\n"
            "Use TRY_CAST or TRY_CONVERT when casting values that may be null or mixed type.\n"
            "Wrap identifiers that contain spaces or are reserved words in square brackets."
        ),
    },
    "postgresql": {
        "driver": "postgresql+psycopg2",
        "query":  {"connect_timeout": "30"},
        "sqlglot": "postgres",
        "label":   "PostgreSQL",
        "rules": (
            "Use LIMIT N for row limits.\n"
            "For dates use NOW(), CURRENT_DATE, INTERVAL and DATE_TRUNC().\n"
            "Cast with CAST(x AS type) or x::type.\n"
            "Wrap identifiers that contain capitals, spaces or are reserved words in double quotes."
        ),
    },
    "mysql": {
        "driver": "mysql+pymysql",
        "query":  {"connect_timeout": "30"},
        "sqlglot": "mysql",
        "label":   "MySQL",
        "rules": (
            "Use LIMIT N for row limits.\n"
            "For dates use NOW(), CURDATE(), DATE_SUB(), DATE_ADD(), DATEDIFF().\n"
            "Cast with CAST(x AS type).\n"
            "Wrap identifiers that contain spaces or are reserved words in backticks."
        ),
    },
}

# ── Config ────────────────────────────────────────────────────────────────────
DB_TYPE      = os.getenv("DB_TYPE", "").lower()
DB_HOST      = os.getenv("DB_HOST")
DB_PORT      = os.getenv("DB_PORT")
DB_USER      = os.getenv("DB_USER")
DB_PASS      = os.getenv("DB_PASSWORD")
DB_NAME      = os.getenv("DB_NAME")
DB_SCHEMA    = os.getenv("DB_SCHEMA") or None
DB_TABLES    = [t.strip() for t in os.getenv("DB_TABLES", "").split(",") if t.strip()]
LLM_URL      = os.getenv("LLM_URL", "http://localhost:8080/v1/chat/completions")
LLM_MODEL    = os.getenv("LLM_MODEL")
CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",") if o.strip()]
MEMORY_FILE  = Path("memory.md")
MAX_ATTEMPTS = 5

for _name, _val in (("DB_TYPE", DB_TYPE), ("DB_NAME", DB_NAME), ("LLM_MODEL", LLM_MODEL)):
    if not _val:
        raise RuntimeError(f"{_name} environment variable is required.")
if DB_TYPE not in DIALECTS:
    raise RuntimeError(f"DB_TYPE must be one of: {', '.join(DIALECTS)}.")
DIALECT = DIALECTS[DB_TYPE]

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

engine = create_engine(
    URL.create(
        DIALECT["driver"], username=DB_USER, password=DB_PASS, host=DB_HOST,
        port=int(DB_PORT) if DB_PORT else None, database=DB_NAME, query=DIALECT["query"],
    ),
    pool_pre_ping=True,   # validates connections before handing them out
    pool_size=8,
    max_overflow=4,
    pool_timeout=10,      # wait max 10s for a free connection
    pool_recycle=300,     # recycle connections every 5 min to avoid stale handles
)

# ── Caches ────────────────────────────────────────────────────────────────────
# Query cache: only touched on the event loop. Schema cache: filled from worker
# threads, hence the lock.
_query_cache  = TTLCache(maxsize=200, ttl=600)
_schema_cache = TTLCache(maxsize=1, ttl=300)
_schema_lock  = Lock()


# ── Schema introspection ──────────────────────────────────────────────────────
@cached(_schema_cache, lock=_schema_lock)
def get_schema() -> str:
    insp = inspect(engine)
    if DB_TABLES:
        targets = [tuple(t.rsplit(".", 1)) if "." in t else (DB_SCHEMA, t) for t in DB_TABLES]
    else:
        names = insp.get_table_names(schema=DB_SCHEMA) + insp.get_view_names(schema=DB_SCHEMA)
        targets = [(DB_SCHEMA, n) for n in sorted(names)]
    if not targets:
        raise RuntimeError("No tables or views found. Check DB_NAME, DB_SCHEMA and DB_TABLES.")

    blocks = []
    for schema, name in targets:
        qualifier = schema or insp.default_schema_name
        cols  = ", ".join(f"{c['name']} ({c['type']})" for c in insp.get_columns(name, schema=schema))
        pk    = insp.get_pk_constraint(name, schema=schema)["constrained_columns"]
        lines = [f"Table {qualifier}.{name}" + (f" (PK: {', '.join(pk)})" if pk else "") + f": {cols}"]
        for fk in insp.get_foreign_keys(name, schema=schema):
            ref = f"{fk['referred_schema'] or qualifier}.{fk['referred_table']}"
            lines.append(f"  FK: {', '.join(fk['constrained_columns'])} -> {ref}({', '.join(fk['referred_columns'])})")
        blocks.append("\n".join(lines))
    return "\n".join(blocks)


# ── Prompt ────────────────────────────────────────────────────────────────────
DEFAULT_SYSTEM_PROMPT_TEMPLATE = """
You are an expert {dialect} query writer.
Given the schema and a user question, return ONLY a valid {dialect} SELECT query — no explanation, no markdown, no code fences, no semicolons at the end.
Schema:
{schema}

The database is {db_name}. Use only the tables and columns listed in the schema.
Only SELECT queries. Never INSERT, UPDATE, DELETE, DROP, ALTER, EXEC, or xp_ calls.
{dialect_rules}
When the user asks about counts or trends, include a meaningful GROUP BY.
When the user says "recent" or "latest", find the most relevant date column in the schema and default to the last 30 days unless they specify otherwise.
When a question is ambiguous, pick the columns whose names and types best match the wording, and never invent columns.
Never add comments or explanation in the output — only the raw SQL query.

Rules:
- When the user asks for "top N per group" — always use ROW_NUMBER() OVER (PARTITION BY ...) in a subquery, then filter WHERE rn <= N.
- Always cast text columns to a numeric type before any SUM/AVG.
- Always check GROUP BY includes all non-aggregated SELECT columns.
- Never use column aliases in WHERE clauses.
- When a question says "most" or "highest", use ORDER BY ... DESC with a row limit.
"""

# Override via the SYSTEM_PROMPT_TEMPLATE env var.
# Placeholders: {dialect}, {dialect_rules}, {db_name}, {schema}.
# Substituted with str.replace (not str.format) so other literal braces are safe.
SYSTEM_PROMPT_TEMPLATE = os.getenv("SYSTEM_PROMPT_TEMPLATE") or DEFAULT_SYSTEM_PROMPT_TEMPLATE

def build_system_prompt(schema: str) -> str:
    values = {
        "dialect_rules": DIALECT["rules"], "dialect": DIALECT["label"],
        "db_name": DB_NAME, "schema": schema,   # schema last: it must not be re-scanned
    }
    prompt = SYSTEM_PROMPT_TEMPLATE
    for key, value in values.items():
        prompt = prompt.replace("{" + key + "}", value)
    memory = load_memory()
    return f"{prompt}\n\n## Learned examples\n{memory}" if memory else prompt


# ── Chain-of-thought ──────────────────────────────────────────────────────────
COT_KEYWORDS = {
    "highest", "most", "total", "average", "least", "lowest",
    "sum", "count", "rank", "top", "bottom", "per", "by",
}

def build_user_message(question: str) -> str:
    if len(set(question.lower().split()) & COT_KEYWORDS) < 2:
        return question
    return (
        f"{question}\n\n"
        "Before writing the SQL:\n"
        "Step 1 — identify the relevant table(s) from the schema.\n"
        "Step 2 — identify the exact column names for grouping and aggregation.\n"
        "Step 3 — write the final SELECT statement only (no explanation)."
    )


# ── Error hints (matched against the lowercased database error) ───────────────
ERROR_HINTS = [
    (r"ambiguous",
     "A column name exists in multiple tables. Qualify it with the table alias, e.g. t.column_name."),
    (r"invalid column name|unknown column|column .* does not exist",
     "The column name you used does not exist. Check the schema carefully and use the exact column name shown."),
    (r"invalid object name|relation .* does not exist|table .* doesn't exist",
     "The table name you used does not exist. Use only the table names shown in the schema."),
    (r"multi-part identifier",
     "A qualified column reference is wrong. Check table alias and column name match the schema."),
    (r"8117|data type|operator does not exist|function .* does not exist|invalid input syntax",
     "A column has the wrong data type for this operation. Cast text columns to a numeric type before SUM/AVG or arithmetic."),
    (r"divide by zero|division by zero",
     "Add a NULLIF guard: divide by NULLIF(denominator, 0)."),
    (r"group by|only_full_group_by",
     "All non-aggregated columns in SELECT must appear in GROUP BY."),
    (r"syntax error|incorrect syntax|error in your sql syntax",
     "There is a SQL syntax error. Check parentheses, commas, and keyword spelling."),
]

def classify_error(error_msg: str) -> str:
    low = error_msg.lower()
    for pattern, hint in ERROR_HINTS:
        if re.search(pattern, low):
            return hint
    return "Rewrite the query from scratch using only the column names visible in the schema."


# ── SQL validation ────────────────────────────────────────────────────────────
# Guardrail, not a substitute for permissions: connect with a read-only DB login.
FORBIDDEN_NODES = (
    exp.Insert, exp.Update, exp.Delete, exp.Merge, exp.Drop, exp.Alter, exp.Create,
    exp.TruncateTable, exp.Copy, exp.Command, exp.Into,
)

def check_sql(sql: str) -> Optional[str]:
    """Parse locally (no DB round-trip). Returns an error message, or None if the SQL is a single read-only SELECT."""
    try:
        statements = sqlglot.parse(sql, dialect=DIALECT["sqlglot"])
    except sqlglot.errors.SqlglotError as e:
        return f"SQL syntax error detected locally (no DB call made): {e}"
    if len(statements) != 1 or statements[0] is None:
        return "Return exactly one SQL statement."
    tree = statements[0]
    if not isinstance(tree, (exp.Select, exp.Union)):
        return "Only SELECT statements are allowed. Rewrite as a valid SELECT."
    if tree.find(*FORBIDDEN_NODES):
        return "Only read-only SELECT statements are allowed (no INSERT/UPDATE/DELETE/DDL/SELECT INTO)."
    return None

def strip_fences(sql: str) -> str:
    sql = re.sub(r"^```[a-z]*\n?", "", sql, flags=re.IGNORECASE).strip("`").strip()
    if ";" in sql:
        sql = sql[:sql.index(";") + 1]
    elif "\n\n" in sql:
        sql = sql[:sql.index("\n\n")]
    return sql.strip()


# ── Memory: queries that needed a retry are fed back as examples ──────────────
def load_memory() -> str:
    return MEMORY_FILE.read_text(encoding="utf-8").strip() if MEMORY_FILE.exists() else ""

def append_memory(question: str, sql: str, attempts: int) -> None:
    if question in load_memory():
        return
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
    entry = (
        f"### Example (fixed after {attempts} attempts)\n"
        f"**Question:** {question}\n"
        f"**SQL:**\n```sql\n{sql}\n```\n"
        f"*(recorded {stamp} UTC)*\n"
    )
    is_new = not MEMORY_FILE.exists() or MEMORY_FILE.stat().st_size == 0
    with MEMORY_FILE.open("a", encoding="utf-8") as f:
        if is_new:
            f.write("# SQL Agent Memory\nLearned examples and patterns.\n")
        f.write("\n" + entry)


# ── LLM + database calls ──────────────────────────────────────────────────────
def ask_llm(messages: list[dict]) -> str:
    res = requests.post(LLM_URL, json={
        "model":       LLM_MODEL,
        "messages":    messages,
        "stream":      False,
        "temperature": 0.1,
        "max_tokens":  600,
    }, timeout=60)
    if not res.ok:
        raise RuntimeError(f"LLM {res.status_code}: {res.text}")
    return res.json()["choices"][0]["message"]["content"].strip()

def _jsonable(v):
    return v if v is None or isinstance(v, (int, float, bool, str)) else str(v)

def run_sql(sql: str) -> list[dict]:
    # exec_driver_sql (not text()) so a ":word" inside generated SQL isn't parsed as a bind parameter
    with engine.connect() as conn:
        rows = conn.exec_driver_sql(sql).mappings().all()
    return [{k: _jsonable(v) for k, v in row.items()} for row in rows]


# ── Agentic retry loop ────────────────────────────────────────────────────────
def agentic_query(schema: str, question: str) -> tuple[str, list, int]:
    messages = [
        {"role": "system", "content": build_system_prompt(schema)},
        {"role": "user",   "content": build_user_message(question)},
    ]
    sql, last_error = "", ""

    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            raw = ask_llm(messages)
        except Exception as e:
            raise HTTPException(502, f"LLM unreachable: {e}")
        sql = strip_fences(raw)

        problem = check_sql(sql)
        if problem is None:
            try:
                return sql, run_sql(sql), attempt
            except Exception as e:
                err = str(getattr(e, "orig", e))
                problem = f"Attempt {attempt} produced a database error.\nError: {err}\nHint: {classify_error(err)}"

        last_error = problem
        messages += [
            {"role": "assistant", "content": raw},
            {"role": "user", "content":
                f"OBSERVATION: {problem}\nFailed SQL:\n{sql}\n\n"
                "Return a corrected single SELECT statement only."},
        ]

    raise HTTPException(
        500,
        f"Query failed after {MAX_ATTEMPTS} attempts. Last error: {last_error}. Last SQL: {sql}",
    )


# ── API ───────────────────────────────────────────────────────────────────────
class QueryRequest(BaseModel):
    question: str

@app.get("/health")
def health():
    return {"status": "ok", "cache_size": len(_query_cache), "schema_cached": len(_schema_cache) > 0}

@app.post("/cache/clear")
def clear_cache():
    _query_cache.clear()
    with _schema_lock:
        _schema_cache.clear()
    return {"status": "cleared"}

@app.post("/query")
async def query(req: QueryRequest):
    question = req.question.strip()
    if not question:
        raise HTTPException(400, "Question cannot be empty.")

    key = question.lower()
    hit = _query_cache.get(key)
    if hit:
        return {**hit, "cached": True}

    try:
        schema = await run_in_threadpool(get_schema)
    except Exception as e:
        raise HTTPException(500, f"Could not read the database schema: {e}")

    sql, results, attempts = await run_in_threadpool(agentic_query, schema, question)

    if attempts > 1:
        try:
            append_memory(question, sql, attempts)
        except Exception as e:
            print(f"[memory] write failed: {e}")

    result = {"sql": sql, "results": results, "attempts": attempts}
    _query_cache[key] = result
    return {**result, "cached": False}
