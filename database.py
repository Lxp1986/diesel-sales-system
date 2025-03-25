import sqlite3
from datetime import datetime
import pandas as pd

class Database:
    def get_customer_statistics(self, start_date, end_date):
        conn = sqlite3.connect(self.db_file)
        df = pd.read_sql_query("""
        SELECT c.name as customer_name,
               COUNT(sr.id) as transaction_count,
               SUM(sr.quantity) as total_quantity,
               SUM(sr.total_amount) as total_sales
        FROM sales_records sr
        JOIN customers c ON sr.customer_id = c.id
        WHERE date(sr.date) BETWEEN ? AND ?
        GROUP BY c.name
        ORDER BY total_sales DESC
        """, conn, params=(start_date, end_date))
        conn.close()
        return df

    def get_total_statistics(self, start_date, end_date):
        conn = sqlite3.connect(self.db_file)
        df = pd.read_sql_query("""
        SELECT COUNT(id) as transaction_count,
               SUM(quantity) as total_quantity,
               SUM(total_amount) as total_sales
        FROM sales_records
        WHERE date(date) BETWEEN ? AND ?
        """, conn, params=(start_date, end_date))
        conn.close()
        return df.iloc[0] if not df.empty else pd.Series([0,0,0], index=['transaction_count','total_quantity','total_sales'])

    def __init__(self, db_file="diesel_sales.db"):
        self.db_file = db_file
        self.init_database()

    def init_database(self):
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()

        # 创建油罐表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS tanks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            max_capacity REAL NOT NULL,
            current_capacity REAL NOT NULL
        )
        ''')

        # 创建入库记录表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS inventory_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tank_id INTEGER,
            date TEXT NOT NULL,
            batch_number TEXT NOT NULL,
            price REAL NOT NULL,
            quantity REAL NOT NULL,
            density REAL NOT NULL,
            total_price REAL NOT NULL,
            FOREIGN KEY (tank_id) REFERENCES tanks (id)
        )
        ''')

        # 创建客户表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE
        )
        ''')

        # 创建销售记录表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS sales_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER,
            date TEXT NOT NULL,
            invoice_number TEXT NOT NULL,
            price REAL NOT NULL,
            quantity REAL NOT NULL,
            total_amount REAL NOT NULL,
            FOREIGN KEY (customer_id) REFERENCES customers (id)
        )
        ''')

        conn.commit()
        conn.close()

    def add_tank(self, name, max_capacity):
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute('''
        INSERT INTO tanks (name, max_capacity, current_capacity)
        VALUES (?, ?, ?)
        ''', (name, max_capacity, 0))
        conn.commit()
        conn.close()

    def add_inventory_record(self, tank_id, date, batch_number, price, quantity, density):
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        total_price = price * quantity
        cursor.execute('''
        INSERT INTO inventory_records (tank_id, date, batch_number, price, quantity, density, total_price)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (tank_id, date, batch_number, price, quantity, density, total_price))
        
        # 将吨数转换为升数更新油罐当前容量
        volume_in_liters = quantity / density * 1000
        cursor.execute('''
        UPDATE tanks 
        SET current_capacity = current_capacity + ?
        WHERE id = ?
        ''', (volume_in_liters, tank_id))
        
        conn.commit()
        conn.close()

    def add_customer(self, name):
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute('''
        INSERT INTO customers (name)
        VALUES (?)
        ''', (name,))
        conn.commit()
        conn.close()

    def add_sale_record(self, customer_id, date, invoice_number, price, quantity, total_amount):
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute('''
        INSERT INTO sales_records (customer_id, date, invoice_number, price, quantity, total_amount)
        VALUES (?, ?, ?, ?, ?, ?)
        ''', (customer_id, date, invoice_number, price, quantity, total_amount))
        conn.commit()
        conn.close()

    def get_tanks(self):
        conn = sqlite3.connect(self.db_file)
        df = pd.read_sql_query("SELECT * FROM tanks", conn)
        conn.close()
        return df

    def get_inventory_records(self):
        conn = sqlite3.connect(self.db_file)
        df = pd.read_sql_query("""
        SELECT ir.*, t.name as tank_name 
        FROM inventory_records ir
        JOIN tanks t ON ir.tank_id = t.id
        """, conn)
        conn.close()
        return df

    def get_customers(self):
        conn = sqlite3.connect(self.db_file)
        df = pd.read_sql_query("SELECT * FROM customers", conn)
        conn.close()
        return df

    def get_sales_records(self, start_date='1970-01-01', end_date='2100-12-31'):
        """
        获取所有销售记录，并关联客户名称
        """
        try:
            conn = sqlite3.connect(self.db_file)
            
            # 禁用缓存
            conn.isolation_level = None
            conn.execute("PRAGMA cache_size = 0")
            conn.execute("PRAGMA temp_store = MEMORY")
            
            # 重置连接以确保没有残留的事务
            conn.execute("PRAGMA read_uncommitted = 1")
            
            # 设置Row工厂
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # 查询销售记录（按ID从小到大排序）
            query = """
            SELECT sr.id, sr.customer_id, sr.date, sr.invoice_number, 
                   sr.price, sr.quantity, sr.total_amount, c.name as customer_name 
            FROM sales_records sr
            JOIN customers c ON sr.customer_id = c.id
        WHERE date(sr.date) BETWEEN ? AND ?
            ORDER BY sr.id
            """
            cursor.execute(query, (start_date, end_date))
            rows = cursor.fetchall()
            
            # 将行转换为字典列表
            results = [dict(row) for row in rows]
            
            # 将字典列表转换为DataFrame
            if results:
                df = pd.DataFrame(results)
                
                # 重新整理ID，确保显示为连续的ID
                df['id'] = range(1, len(df) + 1)
            else:
                # 创建一个空的DataFrame但包含所有需要的列
                df = pd.DataFrame(columns=[
                    'id', 'customer_id', 'date', 'invoice_number', 
                    'price', 'quantity', 'total_amount', 'customer_name'
                ])
            
            conn.close()
            print(f"获取销售记录：共{len(df)}条")
            
            # 如果有记录，则确保是最新的
            if not df.empty:
                print(f"最新销售记录ID: {df['id'].max()}")
            
            return df
        except Exception as e:
            print(f"获取销售记录出错: {str(e)}")
            # 返回空DataFrame
            return pd.DataFrame(columns=[
                'id', 'customer_id', 'date', 'invoice_number', 
                'price', 'quantity', 'total_amount', 'customer_name'
            ])

    def get_customer_summary(self, start_date=None, end_date=None):
        conn = sqlite3.connect(self.db_file)
        query = """
        SELECT 
            c.name AS customer_name,
            c.id AS customer_id,
            SUM(sr.quantity) AS total_quantity,
            SUM(sr.total_amount) AS total_sales,
            AVG(sr.price) AS avg_price
        FROM sales_records sr
        JOIN customers c ON sr.customer_id = c.id
        WHERE date(sr.date) BETWEEN ? AND ?
        GROUP BY c.name
        ORDER BY c.id
        """
        params = (start_date or '1970-01-01', end_date or datetime.now().strftime('%Y-%m-%d'))
        df = pd.read_sql_query(query, conn, params=params)
        conn.close()
        return df

    def get_overall_statistics(self, start_date=None, end_date=None):
        conn = sqlite3.connect(self.db_file)
        query = """
        SELECT 
            COUNT(sr.id) AS total_transactions,
            SUM(sr.quantity) AS total_quantity,
            SUM(sr.total_amount) AS total_sales
        FROM sales_records sr
        WHERE date(sr.date) BETWEEN date(?) AND date(?)
        """
        params = (start_date or '1970-01-01', end_date or datetime.now().strftime('%Y-%m-%d'))
        df = pd.read_sql_query(query, conn, params=params)
        conn.close()
        return df.iloc[0] if not df.empty else pd.Series([0,0,0], index=['total_transactions','total_quantity','total_sales'])

    def get_customer_data(self, customer_id, start_date, end_date):
        conn = sqlite3.connect(self.db_file)
        df = pd.read_sql_query('''
        SELECT sr.*, c.name as customer_name 
        FROM sales_records sr
        JOIN customers c ON sr.customer_id = c.id
        WHERE date(sr.date) BETWEEN ? AND ?
        WHERE sr.customer_id = ? AND sr.date BETWEEN ? AND ?
        ''', conn, params=(customer_id, start_date, end_date))
        conn.close()
        return df

    def export_to_excel(self, filename, start_date, end_date):
        with pd.ExcelWriter(filename) as writer:
            tanks = self.get_tanks()
            tanks.columns = ['ID', '名称', '最大容量', '当前容量']
            tanks.to_excel(writer, sheet_name='油罐信息', index=False)

            inventory_records = self.get_inventory_records()
            inventory_records.columns = ['ID', '油罐', '日期', '单号', '单价', '数量', '密度', '总价', '油罐名称']
            inventory_records.to_excel(writer, sheet_name='入库记录', index=False)

            customers = self.get_customers()
            customers.columns = ['ID', '客户名称']
            customers.to_excel(writer, sheet_name='客户信息', index=False)

            sales_records = self.get_sales_records(start_date, end_date)
            sales_records.columns = ['ID', '客户', '日期', '单号', '单价', '数量', '总价', '客户名称']
            sales_records.to_excel(writer, sheet_name='销售记录', index=False)

            # 添加统计工作表
            customer_stats = self.get_customer_statistics(start_date, end_date)
            customer_stats.columns = ['客户名称', '交易次数', '总数量(升)', '总销售额']
            customer_stats.to_excel(writer, sheet_name='客户统计', index=False)

            total_stats = self.get_total_statistics(start_date, end_date).to_frame().T
            total_stats.columns = ['总交易次数', '总数量(升)', '总销售额']
            total_stats.to_excel(writer, sheet_name='总体统计', index=False)

            # 为每个客户创建单独的工作表
            for _, customer in customers.iterrows():
                customer_id = customer['ID']
                customer_name = customer['客户名称']
                customer_sales = self.get_customer_summary(customer_id)
                if not customer_sales.empty:
                    customer_sales.columns = ['客户名称', '客户ID', '总数量', '总销售额', '平均单价']
                    customer_sales.to_excel(writer, sheet_name=customer_name, index=False)

    def delete_inventory_record(self, record_id):
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        # 获取要删除的记录的信息
        cursor.execute('''
        SELECT tank_id, quantity, density
        FROM inventory_records
        WHERE id = ?
        ''', (record_id,))
        record = cursor.fetchone()
        
        if record:
            tank_id, quantity, density = record
            # 将吨数转换为升数
            volume_in_liters = quantity / density * 1000
            
            # 更新油罐容量
            cursor.execute('''
            UPDATE tanks 
            SET current_capacity = current_capacity - ?
            WHERE id = ?
            ''', (volume_in_liters, tank_id))
            
            # 删除记录
            cursor.execute('DELETE FROM inventory_records WHERE id = ?', (record_id,))
            
            # 重新排序ID
            cursor.execute('''
            UPDATE inventory_records
            SET id = (
                SELECT row_number
                FROM (
                    SELECT id, ROW_NUMBER() OVER (ORDER BY id) as row_number
                    FROM inventory_records
                ) t
                WHERE t.id = inventory_records.id
            )
            ''')
            
            conn.commit()
        conn.close()

    def delete_sales_record(self, record_id):
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        # 删除记录
        cursor.execute('DELETE FROM sales_records WHERE id = ?', (record_id,))
        
        # 重新排序ID
        cursor.execute('''
        UPDATE sales_records
        SET id = (
            SELECT row_number
            FROM (
                SELECT id, ROW_NUMBER() OVER (ORDER BY id) as row_number
                FROM sales_records
            ) t
            WHERE t.id = sales_records.id
        )
        ''')
        
        conn.commit()
        conn.close()

    def delete_customer(self, customer_id):
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        # 删除客户的所有销售记录
        cursor.execute('DELETE FROM sales_records WHERE customer_id = ?', (customer_id,))
        
        # 删除客户
        cursor.execute('DELETE FROM customers WHERE id = ?', (customer_id,))
        
        # 重新排序客户ID
        cursor.execute('''
        UPDATE customers
        SET id = (
            SELECT row_number
            FROM (
                SELECT id, ROW_NUMBER() OVER (ORDER BY id) as row_number
                FROM customers
            ) t
            WHERE t.id = customers.id
        )
        ''')
        
        # 更新销售记录中的客户ID
        cursor.execute('''
        UPDATE sales_records
        SET customer_id = (
            SELECT c.id
            FROM customers c
            WHERE c.name = (
                SELECT name
                FROM customers
                WHERE id = sales_records.customer_id
            )
        )
        ''')
        
        conn.commit()
        conn.close()

    def reset_database(self):
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        # 删除所有表
        cursor.execute("DROP TABLE IF EXISTS sales_records")
        cursor.execute("DROP TABLE IF EXISTS inventory_records")
        cursor.execute("DROP TABLE IF EXISTS customers")
        cursor.execute("DROP TABLE IF EXISTS tanks")
        
        conn.commit()
        conn.close()
        
        # 重新初始化数据库
        self.init_database()

    def calculate_total_profit(self):
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        # 计算总销售额
        cursor.execute("SELECT SUM(total_amount) FROM sales_records")
        total_sales = cursor.fetchone()[0] or 0
        
        # 计算总成本
        cursor.execute("SELECT SUM(total_price) FROM inventory_records")
        total_cost = cursor.fetchone()[0] or 0
        
        conn.close()
        
        # 计算总利润
        total_profit = total_sales - total_cost
        return total_profit

    def calculate_monthly_profit(self):
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        # 获取所有月份的销售额
        cursor.execute("""
        SELECT strftime('%Y-%m', date) as month,
               SUM(total_amount) as sales
        FROM sales_records
        GROUP BY month
        ORDER BY month
        """)
        monthly_sales = dict(cursor.fetchall())
        
        # 获取所有月份的成本
        cursor.execute("""
        SELECT strftime('%Y-%m', date) as month,
               SUM(total_price) as cost
        FROM inventory_records
        GROUP BY month
        ORDER BY month
        """)
        monthly_costs = dict(cursor.fetchall())
        
        conn.close()
        
        # 计算每月利润
        monthly_profits = []
        for month in set(monthly_sales.keys()) | set(monthly_costs.keys()):
            sales = monthly_sales.get(month, 0)
            cost = monthly_costs.get(month, 0)
            profit = sales - cost
            monthly_profits.append((month, profit))
        
        return sorted(monthly_profits)

    def calculate_batch_profit(self):
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        # 获取所有批次的销售额
        cursor.execute("""
        SELECT invoice_number,
               SUM(total_amount) as sales
        FROM sales_records
        GROUP BY invoice_number
        """)
        batch_sales = dict(cursor.fetchall())
        
        # 获取所有批次的成本
        cursor.execute("""
        SELECT batch_number,
               SUM(total_price) as cost
        FROM inventory_records
        GROUP BY batch_number
        """)
        batch_costs = dict(cursor.fetchall())
        
        conn.close()
        
        # 计算每个批次的利润
        batch_profits = []
        for batch in set(batch_sales.keys()) | set(batch_costs.keys()):
            sales = batch_sales.get(batch, 0)
            cost = batch_costs.get(batch, 0)
            profit = sales - cost
            batch_profits.append((batch, profit))
        
        return sorted(batch_profits)

    def calculate_profit_by_period(self, start_date=None, end_date=None):
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        # 构建日期条件
        date_condition = ""
        params = []
        if start_date and end_date:
            date_condition = "WHERE date BETWEEN ? AND ?"
            params = [start_date, end_date]
        elif start_date:
            date_condition = "WHERE date >= ?"
            params = [start_date]
        elif end_date:
            date_condition = "WHERE date <= ?"
            params = [end_date]
        
        # 计算期间销售额
        sales_query = f"SELECT SUM(total_amount) FROM sales_records {date_condition}"
        cursor.execute(sales_query, params)
        period_sales = cursor.fetchone()[0] or 0
        
        # 计算期间成本
        cost_query = f"SELECT SUM(total_price) FROM inventory_records {date_condition}"
        cursor.execute(cost_query, params)
        period_cost = cursor.fetchone()[0] or 0
        
        conn.close()
        
        # 计算期间利润
        period_profit = period_sales - period_cost
        return period_profit

    def update_tank_capacity(self, tank_id, quantity_change):
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute('''
        UPDATE tanks 
        SET current_capacity = current_capacity + ?
        WHERE id = ?
        ''', (quantity_change, tank_id))
        conn.commit()
        conn.close()

    def get_tank_id_by_name(self, tank_name):
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM tanks WHERE name = ?', (tank_name,))
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else None

    def get_customer_id_by_name(self, customer_name):
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM customers WHERE name = ?', (customer_name,))
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else None