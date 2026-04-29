-- 1. 股票基础信息表
CREATE TABLE IF NOT EXISTS stock_master (
    ts_code TEXT PRIMARY KEY,
    symbol TEXT,
    name TEXT,
    area TEXT,
    industry TEXT,
    market TEXT,
    list_date TEXT,
    is_hs TEXT,
    list_status TEXT DEFAULT 'L'
);

-- 2. 交易日历表
CREATE TABLE IF NOT EXISTS trade_calendar (
    exchange TEXT,
    cal_date TEXT,
    is_open INTEGER,
    pretrade_date TEXT,
    PRIMARY KEY (exchange, cal_date)
);

-- 3. 原始未复权日线行情表
CREATE TABLE IF NOT EXISTS daily_raw (
    ts_code TEXT,
    trade_date TEXT,
    open REAL,
    high REAL,
    low REAL,
    close REAL,
    pre_close REAL,
    change REAL,
    pct_chg REAL,
    vol REAL,
    amount REAL,
    PRIMARY KEY (ts_code, trade_date)
);

-- 4. 复权因子表
CREATE TABLE IF NOT EXISTS adj_factor (
    ts_code TEXT,
    trade_date TEXT,
    adj_factor REAL,
    PRIMARY KEY (ts_code, trade_date)
);

-- 5. 日指标表
CREATE TABLE IF NOT EXISTS daily_basic (
    ts_code TEXT,
    trade_date TEXT,
    turnover_rate REAL,
    volume_ratio REAL,
    pe REAL,
    pb REAL,
    total_mv REAL,
    PRIMARY KEY (ts_code, trade_date)
);

-- 6. 计算后的特征表 (前复权及均线等)
CREATE TABLE IF NOT EXISTS daily_features (
    ts_code TEXT,
    trade_date TEXT,
    qfq_close REAL,
    qfq_high REAL,
    ma200 REAL,
    high60 REAL,
    vol_ma3 REAL,
    vol_ma7 REAL,
    PRIMARY KEY (ts_code, trade_date)
);

-- 7. 每日筛选结果表（按策略区分）
CREATE TABLE IF NOT EXISTS screen_results (
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

-- 8. 任务运行记录表
CREATE TABLE IF NOT EXISTS job_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_date TEXT,
    start_time TEXT,
    end_time TEXT,
    status TEXT,
    retry_count INTEGER DEFAULT 0,
    error_msg TEXT
);
