import sqlite3
import os
import logging
import pandas as pd

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """初始化数据库，执行 schema.sql + 迁移"""
        if not os.path.exists(os.path.dirname(self.db_path)):
            os.makedirs(os.path.dirname(self.db_path))

        schema_path = os.path.join(os.getcwd(), 'database', 'schema.sql')
        if not os.path.exists(schema_path):
            logger.error(f"Schema file not found at {schema_path}")
            return

        with open(schema_path, 'r', encoding='utf-8') as f:
            schema_sql = f.read()

        with sqlite3.connect(self.db_path) as conn:
            conn.executescript(schema_sql)
            logger.info("Database schema initialized.")
            self._migrate_schema(conn)

    def _migrate_schema(self, conn):
        """schema 版本迁移（PRAGMA user_version 追踪版本号）"""
        version = conn.execute("PRAGMA user_version").fetchone()[0]

        if version < 1:
            cursor = conn.execute("PRAGMA table_info(screen_results)")
            columns = [row[1] for row in cursor.fetchall()]
            if 'strategy' not in columns:
                logger.info("Migrating screen_results: adding strategy column...")
                conn.executescript("""
                    BEGIN;
                    CREATE TABLE screen_results_v2 (
                        trade_date TEXT,
                        ts_code TEXT,
                        strategy TEXT NOT NULL DEFAULT 'breakout_30',
                        name TEXT,
                        qfq_close REAL,
                        turnover_rate REAL,
                        ma200 REAL,
                        high60 REAL,
                        high30 REAL,
                        is_first_break INTEGER,
                        vol REAL,
                        vol_ma3 REAL,
                        vol_ma7 REAL,
                        vol_ratio_3 REAL,
                        vol_ratio_7 REAL,
                        PRIMARY KEY (trade_date, ts_code, strategy)
                    );
                    INSERT INTO screen_results_v2
                        (trade_date, ts_code, strategy, name, qfq_close, turnover_rate,
                         ma200, high60, is_first_break, vol_ratio_3, vol_ratio_7)
                    SELECT
                        trade_date, ts_code, 'breakout_30', name, qfq_close, turnover_rate,
                        ma200, high60, is_first_break, vol_ratio_3, vol_ratio_7
                    FROM screen_results;
                    DROP TABLE screen_results;
                    ALTER TABLE screen_results_v2 RENAME TO screen_results;
                    PRAGMA user_version = 1;
                    COMMIT;
                """)
                logger.info("Migration v1 completed (strategy column added).")
            else:
                conn.execute("PRAGMA user_version = 1")

    def get_connection(self):
        return sqlite3.connect(self.db_path)

    def save_df(self, table_name: str, df: pd.DataFrame, if_exists: str = 'append'):
        """保存 DataFrame 到数据库，仅保留表中存在的列"""
        if df is None or df.empty:
            return
        
        with self.get_connection() as conn:
            # 获取数据库表中已有的列名
            try:
                cursor = conn.execute(f"SELECT * FROM {table_name} LIMIT 0")
                existing_cols = [description[0] for description in cursor.description]
                # 仅保留 df 中在表中存在的列
                cols_to_keep = [col for col in df.columns if col in existing_cols]
                df_to_save = df[cols_to_keep]
            except:
                # 如果表不存在，则由 to_sql 创建
                df_to_save = df
            
            if if_exists == 'append':
                # 使用临时表实现 INSERT OR REPLACE
                df_to_save.to_sql(f"tmp_{table_name}", conn, if_exists='replace', index=False)
                # 获取列名
                cols = ", ".join(df_to_save.columns)
                conn.execute(f"INSERT OR REPLACE INTO {table_name} ({cols}) SELECT {cols} FROM tmp_{table_name}")
                conn.execute(f"DROP TABLE tmp_{table_name}")
            else:
                df_to_save.to_sql(table_name, conn, if_exists=if_exists, index=False)

    def execute_query(self, sql: str, params: tuple = ()):
        with self.get_connection() as conn:
            return pd.read_sql_query(sql, conn, params=params)

    def execute_non_query(self, sql: str, params: tuple = ()):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, params)
            conn.commit()
            return cursor.lastrowid
