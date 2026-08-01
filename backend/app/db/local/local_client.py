# -*- coding: utf-8 -*-
"""
钛星本地 SQLite 适配层（零第三方依赖，仅标准库 sqlite3）

模拟 supabase-py 链式 API 子集，覆盖 backend/app/db/*.py、
backend/app/ai_extractor.py、backend/app/routers/api.py 中用到的全部模式：

    sb.table(name)
      .select(*cols, count="exact")
      .eq(col, val) / .in_(col, vals) / .ilike(col, pat) / .or_("a.ilike.x,b.ilike.y")
      .order(col, desc=True|False)          # 可多次链式
      .limit(n) / .range(start, end)        # range 含端点，与 supabase 一致
      .execute()                            # -> result.data(list[dict]) / result.count(int|None)
    sb.table(name).insert(dict | list[dict]).execute()
    sb.table(name).update(dict).eq(...).in_(...).execute()
    sb.table(name).delete().eq(...).execute()

结果对象与 supabase 一致：.data 为行 dict 列表；count="exact" 时 .count 为过滤后总数。

类型约定见 local/schema.py：JSON 列自动序列化/反序列化，BOOLEAN 列存 0/1 读回 bool。
表不存在或列不存在时抛出带表名/列名的清晰错误，不静默吞掉。
"""
from __future__ import annotations

import json
import os
import sqlite3
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

from . import schema

# backend/app/db/local/local_client.py -> 项目根 = parents[4]
_PROJECT_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_DB_DIR = _PROJECT_ROOT / ".local"
DEFAULT_DB_PATH = DEFAULT_DB_DIR / "taixing.db"

# or_ 表达式内支持的操作符（PostgREST 风格）
_OR_OPS = {
    "eq": "=",
    "neq": "!=",
    "gt": ">",
    "gte": ">=",
    "lt": "<",
    "lte": "<=",
    "like": "LIKE",
    "ilike": "LIKE",
}


def get_db_path() -> Path:
    """数据库文件路径：环境变量 TAIXING_DB_PATH 可覆盖，默认项目根 .local/taixing.db"""
    return Path(os.environ.get("TAIXING_DB_PATH", str(DEFAULT_DB_PATH)))


class LocalResult:
    """模拟 supabase 查询结果：.data(list[dict]) / .count(int|None)"""

    def __init__(self, data: List[Dict[str, Any]], count: Optional[int] = None):
        self.data = data
        self.count = count

    def __repr__(self) -> str:  # pragma: no cover
        return f"LocalResult(data={self.data!r}, count={self.count!r})"


class LocalQuery:
    """链式查询构建器（一次 execute 后不可复用）"""

    def __init__(self, client: "LocalClient", table: str):
        self._client = client
        self._table = table
        self._columns: Optional[List[str]] = None        # None == "*"
        self._count_exact = False
        self._filters: List[Tuple] = []                  # (kind, ...) 见 _append_filter
        self._orders: List[Tuple[str, bool]] = []
        self._limit: Optional[int] = None
        self._range: Optional[Tuple[int, int]] = None    # (start, end) 含端点
        self._pending: Optional[Tuple[str, Any]] = None   # ("insert"/"update"/"delete", payload)

    # ---------------- 链式 API ----------------

    def select(self, *cols: str, count: Optional[str] = None) -> "LocalQuery":
        # "*" ?????? supabase ???????????
        if cols and cols != ("*",):
            self._columns = list(cols)
        if count == "exact":
            self._count_exact = True
        return self

    def eq(self, col: str, value: Any) -> "LocalQuery":
        self._check_column(col)
        self._filters.append(("eq", col, value))
        return self

    def in_(self, col: str, values: Sequence[Any]) -> "LocalQuery":
        self._check_column(col)
        self._filters.append(("in", col, list(values)))
        return self

    def ilike(self, col: str, pattern: str) -> "LocalQuery":
        self._check_column(col)
        self._filters.append(("like", col, pattern))
        return self

    def or_(self, expr: str) -> "LocalQuery":
        """PostgREST 风格 or 表达式：'col1.ilike.%x%,col2.ilike.%x%'（逗号 = OR）"""
        parts = [p.strip() for p in expr.split(",") if p.strip()]
        if not parts:
            return self
        fragments: List[str] = []
        params: List[Any] = []
        for part in parts:
            frag, frag_params = self._parse_or_condition(part)
            fragments.append(frag)
            params.extend(frag_params)
        self._filters.append(("or", " OR ".join(fragments), params))
        return self

    def order(self, col: str, desc: bool = False) -> "LocalQuery":
        self._check_column(col)
        self._orders.append((col, bool(desc)))
        return self

    def limit(self, n: int) -> "LocalQuery":
        self._limit = int(n)
        return self

    def range(self, start: int, end: int) -> "LocalQuery":
        self._range = (int(start), int(end))
        return self

    def insert(self, data: Union[Dict[str, Any], List[Dict[str, Any]]]) -> "LocalQuery":
        rows = data if isinstance(data, list) else [data]
        self._pending = ("insert", rows)
        return self

    def update(self, data: Dict[str, Any]) -> "LocalQuery":
        self._pending = ("update", dict(data))
        return self

    def delete(self) -> "LocalQuery":
        self._pending = ("delete", None)
        return self

    # ---------------- 执行 ----------------

    def execute(self) -> LocalResult:
        if self._pending is not None:
            kind, payload = self._pending
            if kind == "insert":
                return self._client._insert(self, payload)
            if kind == "update":
                return self._client._update(self, payload)
            if kind == "delete":
                return self._client._delete(self)
            raise RuntimeError(f"[local-db] 未知写操作: {kind!r}")
        return self._client._select(self)

    # ---------------- 内部 ----------------

    def _check_column(self, col: str) -> None:
        if col not in schema.get_column_map(self._table):
            raise RuntimeError(
                f"[local-db] 表 {self._table!r} 无此列: {col!r}（可用列: {sorted(schema.get_column_map(self._table))}）"
            )

    def _parse_or_condition(self, part: str) -> Tuple[str, List[Any]]:
        tokens = part.split(".", 2)
        if len(tokens) != 3:
            raise RuntimeError(f"[local-db] or_ 条件格式错误: {part!r}（应为 col.op.value，如 title.ilike.%x%）")
        col, op, raw_val = tokens
        self._check_column(col)
        op_lower = op.lower()
        if op_lower not in _OR_OPS:
            raise RuntimeError(f"[local-db] or_ 不支持的操作符: {op!r}")
        sql_op = _OR_OPS[op_lower]
        if op_lower in ("ilike", "like"):
            return f'"{col}" LIKE ? COLLATE NOCASE', [raw_val]
        return f'"{col}" {sql_op} ?', [self._client._to_storage(raw_val, schema.get_column_map(self._table).get(col, {}))]


class LocalClient:
    """本地 SQLite 客户端：内部持有一个 sqlite3 连接，多线程加锁"""

    def __init__(self, url: Optional[str] = None, key: Optional[str] = None, db_path: Optional[Union[str, Path]] = None):
        # url/key 仅作标识，本地模式不使用
        self.url = url
        self.key = key
        self.db_path = Path(db_path) if db_path else get_db_path()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._lock = threading.RLock()

    # ---------------- 初始化 ----------------

    def init_db(self) -> None:
        """建全部表（幂等：CREATE TABLE IF NOT EXISTS）"""
        with self._lock:
            schema.init_db(self._conn)

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    # ---------------- 链式入口 ----------------

    def table(self, name: str) -> LocalQuery:
        if name not in schema.TABLES:
            raise RuntimeError(
                f"[local-db] 表不存在: {name!r}（已建表: {sorted(schema.TABLES)}，如需新增请在 local/schema.py 定义）"
            )
        return LocalQuery(self, name)

    # ---------------- 读写实现 ----------------

    def _select(self, q: LocalQuery) -> LocalResult:
        table = q._table
        col_map = schema.get_column_map(table)
        with self._lock:
            if q._columns is not None:
                for c in q._columns:
                    if c not in col_map:
                        raise RuntimeError(
                            f"[local-db] 表 {table!r} 无此列: {c!r}（可用列: {sorted(col_map)}）"
                        )
            where_sql, params = self._build_where(q, col_map)

            count = None
            if q._count_exact:
                cur = self._conn.execute(f'SELECT COUNT(*) FROM "{table}"' + where_sql, params)
                count = int(cur.fetchone()[0])

            cols = ", ".join(f'"{c}"' for c in q._columns) if q._columns is not None else "*"
            sql = f'SELECT {cols} FROM "{table}"' + where_sql
            if q._orders:
                order_parts = [f'"{c}" {"DESC" if d else "ASC"}' for c, d in q._orders]
                sql += " ORDER BY " + ", ".join(order_parts)
            limit, offset = q._limit, 0
            if q._range is not None:
                start, end = q._range
                limit = end - start + 1
                offset = start
            exec_params = list(params)
            if limit is not None:
                sql += " LIMIT ?"
                exec_params.append(int(limit))
                if offset:
                    sql += " OFFSET ?"
                    exec_params.append(int(offset))
            rows = [self._row_to_dict(dict(r), col_map) for r in self._conn.execute(sql, exec_params).fetchall()]
            return LocalResult(rows, count)

    def _insert(self, q: LocalQuery, rows: List[Dict[str, Any]]) -> LocalResult:
        table = q._table
        col_map = schema.get_column_map(table)
        with self._lock:
            if not rows:
                return LocalResult([])
            col_set: List[str] = []
            for r in rows:
                for k in r:
                    if k not in col_map:
                        raise RuntimeError(
                            f"[local-db] ? {table!r} ????????: {k!r}????: {sorted(col_map)}?"
                        )
                    if k not in col_set:
                        col_set.append(k)
            marks = ", ".join(["?"] * len(col_set))
            col_sql = ", ".join(f'"{c}"' for c in col_set)
            sql = f'INSERT INTO "{table}" ({col_sql}) VALUES ({marks})'
            # ??????? rowid?executemany ??? Python ??? lastrowid ? None?
            rowids: List[int] = []
            for r in rows:
                params = tuple(self._to_storage(r.get(c), col_map.get(c, {})) for c in col_set)
                cur = self._conn.execute(sql, params)
                if cur.lastrowid is not None:
                    rowids.append(cur.lastrowid)
            self._conn.commit()
            inserted: List[Dict[str, Any]] = []
            for rid in rowids:
                cur = self._conn.execute(f'SELECT * FROM "{table}" WHERE rowid = ?', (rid,))
                row = cur.fetchone()
                if row is not None:
                    inserted.append(dict(row))
            return LocalResult([self._row_to_dict(r, col_map) for r in inserted])

    def _update(self, q: LocalQuery, data: Dict[str, Any]) -> LocalResult:
        table = q._table
        col_map = schema.get_column_map(table)
        with self._lock:
            if not data:
                return LocalResult([])
            for c in data:
                if c not in col_map:
                    raise RuntimeError(f"[local-db] 表 {table!r} 无此列，无法更新: {c!r}（可用列: {sorted(col_map)}）")
            where_sql, params = self._build_where(q, col_map)
            if not where_sql:
                raise RuntimeError(f"[local-db] update 必须带过滤条件（eq/in_ 等），表: {table!r}")
            set_sql = ", ".join(f'"{c}" = ?' for c in data)
            set_params = [self._to_storage(v, col_map.get(c, {})) for c, v in data.items()]
            self._conn.execute(f'UPDATE "{table}" SET {set_sql}' + where_sql, set_params + list(params))
            self._conn.commit()
            sel = f'SELECT * FROM "{table}"' + where_sql
            rows = [self._row_to_dict(dict(r), col_map) for r in self._conn.execute(sel, params).fetchall()]
            return LocalResult(rows)

    def _delete(self, q: LocalQuery) -> LocalResult:
        table = q._table
        col_map = schema.get_column_map(table)
        with self._lock:
            where_sql, params = self._build_where(q, col_map)
            if not where_sql:
                raise RuntimeError(f"[local-db] delete 必须带过滤条件（eq 等），表: {table!r}")
            sel = f'SELECT * FROM "{table}"' + where_sql
            deleted = [dict(r) for r in self._conn.execute(sel, params).fetchall()]
            self._conn.execute(f'DELETE FROM "{table}"' + where_sql, params)
            self._conn.commit()
            return LocalResult([self._row_to_dict(r, col_map) for r in deleted])

    # ---------------- 工具 ----------------

    def _build_where(self, q: LocalQuery, col_map: Dict[str, Dict]) -> Tuple[str, List[Any]]:
        fragments: List[str] = []
        params: List[Any] = []
        for f in q._filters:
            kind = f[0]
            if kind == "eq":
                _, col, val = f
                fragments.append(f'"{col}" = ?')
                params.append(self._to_storage(val, col_map.get(col, {})))
            elif kind == "in":
                _, col, vals = f
                if not vals:
                    fragments.append("0 = 1")
                else:
                    marks = ", ".join(["?"] * len(vals))
                    fragments.append(f'"{col}" IN ({marks})')
                    params.extend(self._to_storage(v, col_map.get(col, {})) for v in vals)
            elif kind == "like":
                _, col, pat = f
                fragments.append(f'"{col}" LIKE ? COLLATE NOCASE')
                params.append(pat)
            elif kind == "or":
                _, frag, frag_params = f
                fragments.append(f"({frag})")
                params.extend(frag_params)
            else:
                raise RuntimeError(f"[local-db] 不支持的过滤类型: {kind!r}")
        if not fragments:
            return "", []
        return " WHERE " + " AND ".join(fragments), params

    def _to_storage(self, value: Any, col_info: Dict[str, Any]) -> Any:
        """写入前转换：JSON 列序列化、BOOLEAN 列转 0/1、dict/list 兜底序列化"""
        if value is None:
            return None
        if col_info.get("json") and isinstance(value, (dict, list)):
            return json.dumps(value, ensure_ascii=False)
        if col_info.get("bool"):
            return 1 if value else 0
        if isinstance(value, (dict, list)):
            return json.dumps(value, ensure_ascii=False)
        return value

    def _row_to_dict(self, row: Dict[str, Any], col_map: Dict[str, Dict]) -> Dict[str, Any]:
        """读取后转换：JSON 列反序列化、BOOLEAN 列转 bool"""
        out: Dict[str, Any] = {}
        for k, v in row.items():
            info = col_map.get(k, {})
            if v is None:
                out[k] = None
            elif info.get("json"):
                try:
                    out[k] = json.loads(v)
                except (ValueError, TypeError):
                    out[k] = v
            elif info.get("bool"):
                out[k] = bool(v)
            else:
                out[k] = v
        return out


_client: Optional[LocalClient] = None


def create_client(url: Optional[str] = None, key: Optional[str] = None, db_path: Optional[Union[str, Path]] = None) -> LocalClient:
    """创建本地客户端（url/key 忽略或仅作标识）"""
    return LocalClient(url=url, key=key, db_path=db_path)


def get_client() -> LocalClient:
    """进程内单例本地客户端"""
    global _client
    if _client is None:
        _client = create_client()
    return _client


def init_db() -> None:
    """初始化（建表）本地数据库"""
    get_client().init_db()
