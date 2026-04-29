import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
import pandas as pd
import os
import logging

logger = logging.getLogger(__name__)

class Notifier:
    def __init__(self, smtp_config: dict):
        self.config = smtp_config

    def send_email(self, subject: str, body: str, attachment_paths: list = None):
        """发送带多个附件的邮件"""
        try:
            msg = MIMEMultipart()
            msg['Subject'] = subject
            msg['From'] = self.config['user']
            msg['To'] = self.config['receiver']

            msg.attach(MIMEText(body, 'plain'))

            if attachment_paths:
                for path in attachment_paths:
                    if os.path.exists(path):
                        with open(path, "rb") as f:
                            part = MIMEApplication(f.read(), Name=os.path.basename(path))
                        part['Content-Disposition'] = f'attachment; filename="{os.path.basename(path)}"'
                        msg.attach(part)

            with smtplib.SMTP_SSL(self.config['server'], self.config['port']) as server:
                server.login(self.config['user'], self.config['password'])
                server.send_message(msg)
            
            logger.info(f"Email sent successfully to {self.config['receiver']} with {len(attachment_paths) if attachment_paths else 0} attachments.")
            return True
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False

    def export_txt(self, df: pd.DataFrame, file_path: str):
        """导出股票代码列表到 TXT (同花顺导入格式)"""
        if df is None or df.empty:
            return None
        
        # 提取股票代码 (Tushare 格式是 000001.SZ，同花顺通常能识别，或者去掉后缀)
        # 这里保留原始代码，同花顺批量导入通常支持 000001.SZ 格式
        codes = df['ts_code'].tolist()
        with open(file_path, 'w', encoding='utf-8') as f:
            for code in codes:
                f.write(f"{code}\n")
        
        logger.info(f"Stock codes exported to {file_path}")
        return file_path

    def export_csv(self, df: pd.DataFrame, file_path: str, columns_map: dict = None):
        """导出筛选结果到 CSV"""
        if df is None or df.empty:
            return None

        if columns_map is None:
            columns_map = {
            'trade_date': '交易日期',
            'ts_code': '股票代码',
            'name': '股票名称',
            'qfq_close': '当日前复权收盘价',
            'turnover_rate': '当日换手率',
            'ma200': '当日前复权MA200',
            'high60': '过去60日最高前复权high',
            'high30': '过去30日最高前复权high',
            'is_first_break': '是否首次突破',
            'vol': '当日成交量',
            'vol_ma3': '过去3日平均成交量',
            'vol_ratio_3': '当日/3日均量',
            'vol_ma7': '过去7日平均成交量',
            'vol_ratio_7': '当日/7日均量'
        }
        
        # 只保留存在的字段
        available_cols = [c for c in columns_map.keys() if c in df.columns]
        out_df = df[available_cols].rename(columns=columns_map)
        
        out_df.to_csv(file_path, index=False, encoding='utf-8-sig')
        logger.info(f"Results exported to {file_path}")
        return file_path
