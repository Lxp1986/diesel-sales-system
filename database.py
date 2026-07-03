import sqlite3
from sqlite3 import Error, Connection # Import Connection for type hinting

def create_connection(db_file: str) -> Connection:
    """ create a database connection to the SQLite database specified by db_file
    :param db_file: database file path
    :return: Connection object
    :raises: sqlite3.Error if connection fails
    """
    conn = None
    try:
        conn = sqlite3.connect(db_file)
        print(f"Connected to database: {db_file}")
        return conn # Return the connection object on success
    except Error as e:
        print(f"Error connecting to database {db_file}: {e}")
        raise e # Re-raise the exception on failure

def initialize_database(conn: Connection): # Accept connection object as parameter with type hint
    """ Initialize database tables using the provided connection """
    # Removed the 'if conn is None:' check as create_connection now raises an error

    # Added try...except block for database operations
    try:
        with conn: # Use the provided connection
            cursor = conn.cursor()
            # 库存表
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entry_date TEXT NOT NULL,      -- 入库日期
                order_number TEXT NOT NULL UNIQUE, -- Make order_number unique
                price_per_ton REAL NOT NULL,    -- 单价（吨/元）
                quantity_ton REAL NOT NULL,     -- 数量（吨）
                density REAL NOT NULL,          -- 密度（吨/立方米）
                total_liters REAL NOT NULL     -- 总升数（自动计算）
            )
        ''')
            # 客户表
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS customers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE -- Make customer name unique
            )
        ''')
            # 销售表
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS sales (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER NOT NULL, -- Make customer_id NOT NULL
                sale_date TEXT NOT NULL,
                order_number TEXT NOT NULL UNIQUE, -- Make sales order_number unique
                price_per_liter REAL NOT NULL,
                quantity_liter REAL NOT NULL,
                total_price REAL NOT NULL,
                FOREIGN KEY(customer_id) REFERENCES customers(id)
            )
        ''')

            # --- Add missing columns robustly ---
            # Check sales table
            cursor.execute("PRAGMA table_info(sales)")
            sales_columns = {info[1]: info[2] for info in cursor.fetchall()} # Store name: type

            sales_columns_to_add = {
                # 'customer_id': "INTEGER NOT NULL DEFAULT 0", # Ensure NOT NULL if adding later
                'order_number': "TEXT NOT NULL DEFAULT ''",
                'price_per_liter': "REAL NOT NULL DEFAULT 0.0",
                'quantity_liter': "REAL NOT NULL DEFAULT 0.0",
                'total_price': "REAL NOT NULL DEFAULT 0.0"
            }

            for col_name, col_definition in sales_columns_to_add.items():
                if col_name not in sales_columns:
                    try:
                        cursor.execute(f"ALTER TABLE sales ADD COLUMN {col_name} {col_definition}")
                        print(f"Added missing '{col_name}' column to 'sales' table.")
                    except sqlite3.Error as e:
                        print(f"Error adding '{col_name}' column to sales: {e}")

            # Add UNIQUE constraint to inventory order_number if missing
            cursor.execute("PRAGMA index_list(inventory)")
            inv_indices = [idx[1] for idx in cursor.fetchall()]
            if 'idx_inventory_order_number' not in inv_indices:
                 try:
                     cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_inventory_order_number ON inventory(order_number)")
                     print("Added UNIQUE index to inventory.order_number.")
                 except sqlite3.Error as e:
                     print(f"Could not add UNIQUE index to inventory.order_number: {e}")

            # Add UNIQUE constraint to customer name if missing
            cursor.execute("PRAGMA index_list(customers)")
            cust_indices = [idx[1] for idx in cursor.fetchall()]
            if 'idx_customers_name' not in cust_indices:
                 try:
                     cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_customers_name ON customers(name)")
                     print("Added UNIQUE index to customers.name.")
                 except sqlite3.Error as e:
                     print(f"Could not add UNIQUE index to customers.name: {e}")

            # Add UNIQUE constraint to sales order_number if missing
            cursor.execute("PRAGMA index_list(sales)")
            sales_indices = [idx[1] for idx in cursor.fetchall()]
            if 'idx_sales_order_number' not in sales_indices:
                 try:
                     cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_sales_order_number ON sales(order_number)")
                     print("Added UNIQUE index to sales.order_number.")
                 except sqlite3.Error as e:
                     print(f"Could not add UNIQUE index to sales.order_number: {e}")


            # --- Remove remaining_liters from inventory table robustly (if exists) ---
            cursor.execute("PRAGMA table_info(inventory)")
            inventory_columns_info = {info[1]: info for info in cursor.fetchall()} # Get full column info
            if 'remaining_liters' in inventory_columns_info:
                try:
                    print("Found 'remaining_liters' column in 'inventory'. Recreating table...")
                    # 1. Begin transaction
                    cursor.execute("BEGIN TRANSACTION;")
                    # 2. Create new table without the column, preserving constraints
                    cursor.execute('''
                        CREATE TABLE inventory_new (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            entry_date TEXT NOT NULL,
                            order_number TEXT NOT NULL UNIQUE, -- Keep UNIQUE
                            price_per_ton REAL NOT NULL,
                            quantity_ton REAL NOT NULL,
                            density REAL NOT NULL,
                            total_liters REAL NOT NULL
                        )
                    ''')
                    # 3. Copy data from old table to new table
                    cursor.execute('''
                        INSERT INTO inventory_new (id, entry_date, order_number, price_per_ton, quantity_ton, density, total_liters)
                        SELECT id, entry_date, order_number, price_per_ton, quantity_ton, density, total_liters
                        FROM inventory
                    ''')
                    # 4. Drop the old table
                    cursor.execute("DROP TABLE inventory")
                    # 5. Rename the new table
                    cursor.execute("ALTER TABLE inventory_new RENAME TO inventory")
                    # 6. Commit transaction
                    cursor.execute("COMMIT;")
                    print("Successfully removed 'remaining_liters' column and recreated 'inventory' table.")
                except sqlite3.Error as e:
                    cursor.execute("ROLLBACK;") # Rollback on error
                    print(f"Error removing 'remaining_liters' column: {e}. Rolled back changes.")
            # --- End remove remaining_liters ---

        print("Database initialized/verified successfully.")

    except sqlite3.Error as e:
        print(f"An error occurred during database initialization: {e}")
        # Optionally re-raise or handle differently
    # 'with conn:' handles commit/rollback on success/error and closing cursor implicitly.
    # Connection closing is handled by the caller (main.py).

# Example usage (optional, for testing this module directly)
if __name__ == '__main__':
    db_file = 'test_diesel_sales.db'
    conn = create_connection(db_file)
    if conn:
        initialize_database(conn)
        # Example: Add a customer
        try:
            with conn:
                cursor = conn.cursor()
                cursor.execute("INSERT OR IGNORE INTO customers (name) VALUES (?)", ('测试客户',))
                print("Test customer added or already exists.")
                cursor.execute("SELECT * FROM customers")
                print("Customers:", cursor.fetchall())
        except sqlite3.Error as e:
            print(f"Error during test operation: {e}")
        finally:
            conn.close()
            print(f"Connection to {db_file} closed.")
    else:
        print("Failed to create connection for testing.")
