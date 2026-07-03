import tkinter as tk
from tkinter import ttk, messagebox, filedialog # Added filedialog
from datetime import datetime
import database
import sqlite3
import traceback # Import traceback for detailed error printing
import shutil # Added for file copying (Save As)
import pandas as pd # Added for Excel export
import os # Added for path manipulation
import re # Added for sanitizing sheet names
import sys
from sqlite3 import Connection # Import Connection for type hinting

APP_DIR = os.path.dirname(os.path.abspath(__file__))

class DieselInventoryApp:
    def __init__(self, root):
        self.root = root
        self.root.title("柴油库存管理系统")
        # Increased default size slightly
        self.root.geometry("1366x768")
        self.root.minsize(1024, 600)
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        # --- Menu Bar ---
        self.create_menu()

        # Initialize database
        self.conn: Connection | None = None # Initialize with None and add type hint
        self.db_path = os.path.join(APP_DIR, 'diesel_sales.db') # Always use project directory
        try:
            self.conn = database.create_connection(self.db_path) # Assign Connection object here
            # Ensure database and tables are created using the definition in database.py
            database.initialize_database(self.conn) # Pass the connection object
        except sqlite3.Error as e:
            messagebox.showerror("数据库错误", f"无法连接或初始化数据库:\n{e}\n请检查文件 '{self.db_path}'。")
            self.root.quit() # Exit if DB connection/initialization fails
            return # Stop further initialization in __init__

        # Create Notebook
        self.notebook = ttk.Notebook(self.root)
        self.notebook.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

        # Create tabs
        self.create_inventory_tab()
        self.selected_customer_id = None # Added to store the ID
        self.create_customer_tab()
        self.create_sales_tab()
        self.create_statistics_tab() # Create the tab structure
        # Initialize customer data needed for stats combobox before refreshing stats
        self.customer_data = {} # Dictionary to store {name: id}
        self.refresh_customer_names() # Populate combobox and data dict for sales tab first
        self.refresh_statistics() # Initial data load for stats tab

    def create_menu(self):
        """Creates the main menu bar."""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        # --- File Menu ---
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="文件", menu=file_menu)

        file_menu.add_command(label="打开存档文件...", command=self.open_database_file) # Added Open
        file_menu.add_command(label="另存为...", command=self.save_database_as)
        file_menu.add_command(label="导出到 Excel...", command=self.export_to_excel)
        file_menu.add_separator()
        file_menu.add_command(label="初始化数据...", command=self.initialize_all_data)
        file_menu.add_separator()
        file_menu.add_command(label="退出", command=self.root.quit)

        # --- Help Menu (Optional) ---
        # help_menu = tk.Menu(menubar, tearoff=0)
        # menubar.add_cascade(label="帮助", menu=help_menu)
        # help_menu.add_command(label="关于", command=self.show_about) # Placeholder

    # --- Menu Command Methods ---

    def initialize_all_data(self):
        """Deletes all data from inventory, sales, and customers tables."""
        if messagebox.askyesno("确认初始化", "警告：此操作将删除所有入库、销售和客户数据，且无法撤销！\n确定要继续吗？", icon='warning'):
            if self.conn:
                try:
                    with self.conn:
                        cursor = self.conn.cursor()
                        cursor.execute("DELETE FROM sales")
                        cursor.execute("DELETE FROM inventory")
                        cursor.execute("DELETE FROM customers")
                        # Optional: Reset auto-increment counters if using AUTOINCREMENT (SQLite specific)
                        # cursor.execute("DELETE FROM sqlite_sequence WHERE name IN ('sales', 'inventory', 'customers')")
                    messagebox.showinfo("初始化完成", "所有数据已成功删除。")
                    # Refresh all UI elements
                    self.refresh_table()
                    self.refresh_customer_list()
                    self.refresh_sales_list()
                    self.refresh_customer_names() # Clears comboboxes
                    self.update_stats_customer_combobox() # Clears stats combobox
                    self.refresh_statistics() # Clears stats display
                    self.update_remaining_liters() # Resets remaining liters display
                except sqlite3.Error as e:
                    messagebox.showerror("数据库错误", f"初始化数据时出错: {e}")
            else:
                messagebox.showerror("数据库错误", "数据库连接丢失，无法初始化。")

    def save_database_as(self):
        """Saves a copy of the current database file to a new location."""
        initial_dir = os.path.dirname(os.path.abspath(self.db_path)) # Use absolute path's dir
        initial_file = os.path.basename(self.db_path)
        save_path = filedialog.asksaveasfilename(
            initialdir=initial_dir,
            initialfile=f"备份_{initial_file}", # Suggest a backup name
            defaultextension=".db",
            filetypes=[("SQLite Database", "*.db"), ("All Files", "*.*")]
        )
        if save_path:
            # Ensure the target directory exists
            target_dir = os.path.dirname(save_path)
            if not os.path.exists(target_dir):
                try:
                    os.makedirs(target_dir)
                except OSError as e:
                    messagebox.showerror("创建目录失败", f"无法创建目标目录 '{target_dir}': {e}")
                    return

            try:
                # Ensure the database connection is closed before copying
                # A simple approach: copy the file directly. Might fail if locked.
                # A more robust approach would involve closing and reopening the connection,
                # but that adds significant complexity to the app's state management.
                # Let's try the simple copy first.
                if self.conn:
                    self.conn.commit() # Ensure data is written to disk
                    # self.conn.close() # Ideally close, but complicates reopening
                    # self.conn = None
                shutil.copy2(self.db_path, save_path) # copy2 preserves metadata
                messagebox.showinfo("另存为成功", f"数据库已成功另存为:\n{save_path}")
                # Reopen connection if we closed it
                # if not self.conn:
                #    self.conn = database.create_connection(self.db_path)
                #    if not self.conn:
                #        messagebox.showerror("数据库错误", "另存为后无法重新连接到原始数据库！应用程序可能需要重启。")
                #        self.root.quit()

            except Exception as e:
                messagebox.showerror("另存为失败", f"无法复制数据库文件: {e}\n可能是文件被占用，请尝试关闭应用程序后手动复制。")
                # Attempt to reopen connection if it was closed and failed
                # if not self.conn:
                #    self.conn = database.create_connection(self.db_path) # Try reopening original

    def export_to_excel(self):
        """Exports inventory, sales, per-customer sales, and summary data to an Excel file, filtered by stats tab dates."""
        if not self.conn:
            messagebox.showerror("数据库错误", "数据库连接丢失，无法导出。")
            return

        try:
            # --- Get and Validate Date Filters for Filename and Query ---
            start_date_str = self.stats_start_date_entry.get().strip()
            end_date_str = self.stats_end_date_entry.get().strip()
            start_date_obj = None
            end_date_obj = None
            filename_prefix = ""

            if start_date_str:
                try:
                    start_date_obj = datetime.strptime(start_date_str, "%Y-%m-%d")
                except ValueError:
                    messagebox.showwarning("日期格式错误", f"开始日期 '{start_date_str}' 格式无效，将不用于文件名前缀。")
                    start_date_str = None # Invalidate for query logic below

            if end_date_str:
                try:
                    end_date_obj = datetime.strptime(end_date_str, "%Y-%m-%d")
                except ValueError:
                    messagebox.showwarning("日期格式错误", f"结束日期 '{end_date_str}' 格式无效，将不用于文件名前缀。")
                    end_date_str = None # Invalidate for query logic below

            # Construct filename prefix
            if start_date_obj and end_date_obj:
                filename_prefix = f"{start_date_obj.strftime('%Y%m%d')}-{end_date_obj.strftime('%Y%m%d')}_"
            elif start_date_obj:
                filename_prefix = f"{start_date_obj.strftime('%Y%m%d')}起_"
            elif end_date_obj:
                filename_prefix = f"截至{end_date_obj.strftime('%Y%m%d')}_"

            initial_dir = os.path.dirname(os.path.abspath(self.db_path)) # Suggest saving near the database
            default_filename = f"{filename_prefix}柴油销售数据导出.xlsx"

            save_path = filedialog.asksaveasfilename(
                initialdir=initial_dir,
                initialfile=default_filename, # Use generated filename
                defaultextension=".xlsx",
                filetypes=[("Excel 文件", "*.xlsx")]
            )
            if not save_path: # User cancelled
                return

            # --- Prepare SQL Query Filters (using potentially invalidated date strings) ---
            inv_where_clauses = []
            inv_params = []
            sales_where_clauses = []
            sales_params = []

            if start_date_str: # Check if still valid after filename logic
                try:
                    datetime.strptime(start_date_str, "%Y-%m-%d") # Re-validate for query
                    inv_where_clauses.append("entry_date >= ?")
                    inv_params.append(start_date_str)
                    sales_where_clauses.append("s.sale_date >= ?")
                    sales_params.append(start_date_str)
                except ValueError:
                    # This case should ideally not be reached if invalidated above, but as safety
                    print(f"Query filter ignoring invalid start date: {start_date_str}")
                    start_date_str = None # Ensure it's None

            if end_date_str: # Check if still valid after filename logic
                try:
                    datetime.strptime(end_date_str, "%Y-%m-%d") # Re-validate for query
                    inv_where_clauses.append("entry_date <= ?")
                    inv_params.append(end_date_str)
                    sales_where_clauses.append("s.sale_date <= ?")
                    sales_params.append(end_date_str)
                except ValueError:
                    print(f"Query filter ignoring invalid end date: {end_date_str}")
                    end_date_str = None # Ensure it's None

            inv_where_sql = " AND ".join(inv_where_clauses) if inv_where_clauses else "1=1"
            sales_where_sql = " AND ".join(sales_where_clauses) if sales_where_clauses else "1=1"
            # --- End Date Filters ---

            # Read inventory data (apply filter)
            inventory_query = f"SELECT id, entry_date, order_number, price_per_ton, quantity_ton, density, total_liters FROM inventory WHERE {inv_where_sql} ORDER BY id ASC"
            inventory_df = pd.read_sql_query(inventory_query, self.conn, params=inv_params)
            # Rename columns for clarity in Excel (Already Chinese)
            inventory_df.rename(columns={
                'id': '序号', 'entry_date': '入库日期', 'order_number': '入库单号',
                'price_per_ton': '单价(吨/元)', 'quantity_ton': '数量(吨)',
                'density': '密度', 'total_liters': '总升数'
            }, inplace=True)

            # Read sales data with customer names
            sales_query = f"""
                SELECT s.id, c.name, s.sale_date, s.order_number, s.price_per_liter, s.quantity_liter, s.total_price
                FROM sales s
                LEFT JOIN customers c ON s.customer_id = c.id
                WHERE {sales_where_sql} -- Apply date filter
                ORDER BY s.id ASC
            """
            sales_df = pd.read_sql_query(sales_query, self.conn, params=sales_params)
            # Rename columns (Already Chinese)
            sales_df.rename(columns={
                'id': '序号', 'name': '客户名称', 'sale_date': '销售日期',
                'order_number': '销售单号', 'price_per_liter': '单价(元/升)',
                'quantity_liter': '数量(升)', 'total_price': '总价(元)'
            }, inplace=True)

            # Write to Excel
            with pd.ExcelWriter(save_path, engine='openpyxl') as writer:
                inventory_df.to_excel(writer, sheet_name='入库记录', index=False)
                sales_df.to_excel(writer, sheet_name='销售记录', index=False)

                # --- Add per-customer sheets ---
                cursor = self.conn.cursor()
                cursor.execute("SELECT id, name FROM customers ORDER BY name")
                customers = cursor.fetchall()

                # Define columns for customer sheets (Corrected keys to match DataFrame columns)
                customer_sales_cols_rename = {
                    'id': '序号', 'sale_date': '销售日期', 'order_number': '销售单号',
                    'price_per_liter': '单价(元/升)', 'quantity_liter': '数量(升)',
                    'total_price': '总价(元)'
                }
                # Define columns to SELECT in the SQL query
                customer_sales_query_cols = "s.id, s.sale_date, s.order_number, s.price_per_liter, s.quantity_liter, s.total_price"

                for customer_id, customer_name in customers:
                    # Sanitize customer name for sheet name
                    invalid_chars = r'[\\/?*\[\]:]'
                    sanitized_name = re.sub(invalid_chars, '', customer_name)
                    sanitized_name = sanitized_name[:31]

                    if not sanitized_name:
                        sanitized_name = f"客户_{customer_id}"

                    sheet_suffix = 1
                    original_sanitized_name = sanitized_name
                    while sanitized_name in writer.sheets:
                        sheet_suffix += 1
                        max_base_len = 31 - len(str(sheet_suffix)) - 1
                        truncated_base = original_sanitized_name[:max_base_len]
                        sanitized_name = f"{truncated_base}_{sheet_suffix}"
                        if len(sanitized_name) > 31:
                             sanitized_name = sanitized_name[:31]

                    customer_query = f"""
                        SELECT {customer_sales_query_cols}
                        FROM sales s
                        WHERE s.customer_id = ? AND ({sales_where_sql}) -- Apply date filter
                        ORDER BY s.id ASC
                    """
                    customer_params = [customer_id] + sales_params
                    customer_sales_df = pd.read_sql_query(customer_query, self.conn, params=customer_params)

                    if not customer_sales_df.empty:
                        # Rename columns using the corrected dictionary
                        customer_sales_df.rename(columns=customer_sales_cols_rename, inplace=True)
                        customer_sales_df.to_excel(writer, sheet_name=sanitized_name, index=False)
                # --- End add per-customer sheets ---

                # --- Add Sales Summary Sheet ---
                summary_query = f"""
                    SELECT
                        c.name AS customer_name,
                        COUNT(s.id) AS transaction_count,
                        SUM(s.quantity_liter) AS total_quantity,
                        SUM(s.total_price) AS total_amount
                    FROM sales s
                    LEFT JOIN customers c ON s.customer_id = c.id
                    WHERE {sales_where_sql} -- Apply the same date filters
                    GROUP BY c.id, c.name
                    ORDER BY c.name ASC
                """
                summary_df = pd.read_sql_query(summary_query, self.conn, params=sales_params)

                # Rename summary columns to Chinese
                summary_df.rename(columns={
                    'customer_name': '客户名称',
                    'transaction_count': '总交易次数',
                    'total_quantity': '总销售数量(升)',
                    'total_amount': '总销售金额(元)'
                }, inplace=True)

                # Write the summary sheet
                summary_df.to_excel(writer, sheet_name='销售汇总', index=False)
                # --- End Sales Summary Sheet ---


            messagebox.showinfo("导出成功", f"数据已成功导出到:\n{save_path}")

        except sqlite3.Error as e:
            messagebox.showerror("数据库错误", f"读取数据以供导出时出错: {e}")
        except ImportError:
             messagebox.showerror("缺少库", "导出 Excel 需要 'pandas' 和 'openpyxl' 库。\n请确保它们已安装: pip install pandas openpyxl")
        except Exception as e:
            traceback.print_exc()
            messagebox.showerror("导出失败", f"导出到 Excel 时发生错误: {e}")
        # Removed the final else block as the connection check is now at the beginning

    def open_database_file(self):
        """Opens an existing database file."""
        initial_dir = os.path.dirname(os.path.abspath(self.db_path))
        open_path = filedialog.askopenfilename(
            initialdir=initial_dir,
            title="打开数据库文件",
            filetypes=[("SQLite Database", "*.db"), ("All Files", "*.*")]
        )

        if open_path and open_path != self.db_path:
            print(f"Attempting to open database: {open_path}")
            # Close current connection if open
            if self.conn:
                try:
                    self.conn.close()
                    print(f"Closed connection to: {self.db_path}")
                    self.conn = None
                except sqlite3.Error as e:
                    messagebox.showerror("关闭连接错误", f"无法关闭当前数据库连接: {e}")
                    # Proceed with caution, might leave old connection dangling

            # Attempt to connect to the new database
            try:
                new_conn = database.create_connection(open_path) # Might raise Error
                self.conn = new_conn
                self.db_path = open_path
                print(f"Successfully connected to: {self.db_path}")

                # Verify/initialize tables in the new database
                database.initialize_database(self.conn) # Might raise Error

                # Refresh all UI elements
                self.refresh_all_views()
                # Update window title
                self.root.title(f"柴油库存管理系统 - [{os.path.basename(self.db_path)}]")
                messagebox.showinfo("打开成功", f"已成功打开数据库:\n{self.db_path}")

            except sqlite3.Error as e:
                messagebox.showerror("打开失败", f"无法连接或初始化选定的数据库文件:\n{open_path}\n错误: {e}\n\n将尝试重新连接到原始数据库。")
                self.conn = None # Ensure conn is None before trying to reconnect
                # Attempt to reconnect to the original database
                try:
                    self.conn = database.create_connection(self.db_path) # Use the original self.db_path
                    database.initialize_database(self.conn)
                    self.refresh_all_views() # Refresh with original data
                    self.root.title("柴油库存管理系统") # Reset title
                except sqlite3.Error as final_e:
                    messagebox.showerror("严重错误", f"无法重新连接到原始数据库！请重启应用程序。\n错误: {final_e}")
                    self.root.quit()
            except Exception as e: # Catch other potential errors during refresh etc.
                traceback.print_exc()
                messagebox.showerror("错误", f"打开数据库后发生意外错误: {e}")


    def refresh_all_views(self):
        """Refreshes all data-displaying widgets in the application."""
        print("Refreshing all views...")
        self.refresh_table()
        self.refresh_customer_list()
        self.refresh_sales_list()
        self.refresh_customer_names() # Includes updating comboboxes
        self.refresh_statistics()
        self.update_remaining_liters()
        print("All views refreshed.")

    # --- End Menu Command Methods ---


    def create_inventory_tab(self):
        # Create Inventory Management tab
        self.inventory_tab = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(self.inventory_tab, text="入库管理")
        self.inventory_tab.columnconfigure(0, weight=1)
        # Configure row 2 (where the list frame is) to expand vertically
        self.inventory_tab.rowconfigure(2, weight=1) # List frame row

        # Create UI components
        self.create_input_fields(self.inventory_tab) # Row 0
        # Add Edit and Delete buttons frame (Row 1)
        button_frame = ttk.Frame(self.inventory_tab)
        button_frame.grid(row=1, column=0, pady=5, sticky="e")
        ttk.Button(button_frame, text="编辑选中记录", command=self.edit_record).pack(side="left", padx=5)
        ttk.Button(button_frame, text="删除选中记录", command=self.delete_record).pack(side="left", padx=5)

        self.create_inventory_table(self.inventory_tab) # Row 2 (will expand)

        # Load initial data
        self.refresh_table()

    def create_customer_tab(self):
        # Create Customer Management tab
        self.customer_tab = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(self.customer_tab, text="客户管理")
        self.customer_tab.columnconfigure(0, weight=1) # Allow input frame to expand horizontally
        self.customer_tab.rowconfigure(1, weight=1) # Allow list frame to expand vertically

        # --- Top Frame for Input and Buttons ---
        top_frame = ttk.Frame(self.customer_tab)
        top_frame.grid(row=0, column=0, padx=5, pady=5, sticky="ew")
        top_frame.columnconfigure(1, weight=1) # Allow entry to expand (changed from 0 to 1)

        # Customer name input
        ttk.Label(top_frame, text="客户名称:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.customer_name_entry = ttk.Entry(top_frame)
        self.customer_name_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        # Button frame (aligned right)
        button_frame = ttk.Frame(top_frame)
        button_frame.grid(row=0, column=2, padx=5, pady=5, sticky="e")
        ttk.Button(button_frame, text="保存", command=self.save_customer).pack(side="left", padx=5)
        ttk.Button(button_frame, text="编辑", command=self.edit_customer).pack(side="left", padx=5)
        ttk.Button(button_frame, text="删除", command=self.delete_customer).pack(side="left", padx=5)

        # --- Customer List Frame (Expands) ---
        list_frame = ttk.LabelFrame(self.customer_tab, text="客户列表")
        list_frame.grid(row=1, column=0, padx=5, pady=5, sticky="nsew")
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)

        # Changed columns to ("display_id", "name")
        self.customer_tree = ttk.Treeview(list_frame, columns=("display_id", "name"), show="headings")
        self.customer_tree.heading("display_id", text="序号") # Changed heading
        self.customer_tree.heading("name", text="客户名称")
        self.customer_tree.column("display_id", width=50, stretch=False, anchor="center") # Changed column name
        self.customer_tree.column("name", width=200)
        self.customer_tree.grid(row=0, column=0, sticky="nsew")

        # Scrollbar
        customer_scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.customer_tree.yview)
        self.customer_tree.configure(yscrollcommand=customer_scrollbar.set)
        customer_scrollbar.grid(row=0, column=1, sticky="ns")

        self.refresh_customer_list()

    def delete_customer(self):
        selected = self.customer_tree.selection()
        if not selected:
            messagebox.showwarning("警告", "请先选择要删除的客户")
            return

        # Get the database ID (iid) directly from the selection
        db_id = selected[0]
        # Get display values for confirmation message
        item_values = self.customer_tree.item(db_id, 'values')
        display_id, customer_name = item_values # Display ID is now first

        if messagebox.askyesno("确认删除", f"确定要删除客户 {customer_name} (序号: {display_id}) 吗？"):
            if self.conn: # Add check
                try:
                    with self.conn:
                        cursor = self.conn.cursor()
                        # Check if customer has sales records using the actual database ID (db_id)
                        cursor.execute("SELECT 1 FROM sales WHERE customer_id = ?", (db_id,))
                        if cursor.fetchone():
                            messagebox.showerror("错误", f"无法删除客户 '{customer_name}'，该客户存在销售记录。")
                            return
                        # Delete using the actual database ID (db_id)
                        cursor.execute("DELETE FROM customers WHERE id = ?", (db_id,))
                    self.refresh_customer_list() # Refresh to renumber display IDs
                    self.refresh_customer_names() # Update names in sales tab dropdown/search
                    self.update_stats_customer_combobox() # Update stats tab combobox too
                except sqlite3.Error as e:
                    messagebox.showerror("数据库错误", f"删除客户时出错: {e}")
            else:
                messagebox.showerror("数据库错误", "数据库连接丢失")
                return

    def edit_customer(self):
        selected = self.customer_tree.selection()
        if not selected:
            messagebox.showwarning("警告", "请先选择要编辑的客户")
            return

        # Get the database ID (iid) directly from the selection
        db_id = selected[0]
        # Get display values
        item_values = self.customer_tree.item(db_id, 'values')
        display_id, old_name = item_values # Display ID is now first

        # Create a simple dialog for editing
        edit_dialog = tk.Toplevel(self.root)
        edit_dialog.title(f"编辑客户 (序号: {display_id})") # Show display ID
        edit_dialog.geometry("300x100")
        edit_dialog.transient(self.root) # Make it modal relative to the main window
        edit_dialog.grab_set() # Grab focus

        ttk.Label(edit_dialog, text="新名称:").pack(pady=5)
        name_entry = ttk.Entry(edit_dialog, width=30)
        name_entry.insert(0, old_name)
        name_entry.pack(pady=5)

        def save_customer_edit():
            new_name = name_entry.get().strip()
            if not new_name:
                messagebox.showerror("错误", "客户名称不能为空", parent=edit_dialog)
                return
            if new_name == old_name:
                edit_dialog.destroy()
                return

            if self.conn: # Add check
                try:
                    with self.conn:
                        cursor = self.conn.cursor()
                        # Check if new name already exists (excluding the current customer, using db_id)
                        cursor.execute("SELECT id FROM customers WHERE name = ? AND id != ?", (new_name, db_id))
                        if cursor.fetchone():
                            messagebox.showerror("错误", f"客户名称 '{new_name}' 已存在", parent=edit_dialog)
                            return
                        # Update using the actual database ID (db_id)
                        cursor.execute("UPDATE customers SET name = ? WHERE id = ?", (new_name, db_id))
                    edit_dialog.destroy()
                    self.refresh_customer_list() # Refresh to show changes and renumber
                    self.refresh_customer_names() # Update names list used elsewhere
                    self.refresh_sales_list() # Refresh sales list to show updated name
                    self.update_stats_customer_combobox() # Update stats tab combobox
                except sqlite3.Error as e:
                    messagebox.showerror("数据库错误", f"无法更新客户: {e}", parent=edit_dialog)
            else:
                messagebox.showerror("数据库错误", "数据库连接丢失", parent=edit_dialog)
                # No return here, let the dialog stay open

        save_button = ttk.Button(edit_dialog, text="保存", command=save_customer_edit)
        save_button.pack(pady=10)
        name_entry.focus()
        name_entry.select_range(0, tk.END)
        self.root.wait_window(edit_dialog) # Wait for the dialog to close


    def create_sales_tab(self):
        # Create Sales Management tab
        self.sales_tab = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(self.sales_tab, text="销售管理")
        self.sales_tab.columnconfigure(0, weight=1)
        # Configure row 2 (where the list frame is) to expand vertically
        self.sales_tab.rowconfigure(2, weight=1) # List frame row

        # --- Input Frame ---
        input_frame = ttk.LabelFrame(self.sales_tab, text="销售信息")
        input_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        input_frame.columnconfigure(1, weight=1) # Allow entry fields to expand

        # --- Reordered Fields ---
        # Row 0: Customer Search
        ttk.Label(input_frame, text="客户搜索:").grid(row=0, column=0, padx=5, pady=5, sticky="e")
        self.sales_customer_search_entry = ttk.Entry(input_frame)
        self.sales_customer_search_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        self.sales_customer_search_entry.bind("<KeyRelease>", self.update_customer_combobox_filter)

        # Row 1: Customer Selection Combobox
        ttk.Label(input_frame, text="选择客户:").grid(row=1, column=0, padx=5, pady=5, sticky="e")
        self.sales_customer_combobox = ttk.Combobox(input_frame, state="readonly", width=30)
        self.sales_customer_combobox.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        self.sales_customer_combobox.bind("<<ComboboxSelected>>", self.on_customer_selected)

        # Row 2: Price (per Liter)
        ttk.Label(input_frame, text="单价(元/升):").grid(row=2, column=0, padx=5, pady=5, sticky="e")
        self.sales_price_entry = ttk.Entry(input_frame)
        self.sales_price_entry.grid(row=2, column=1, padx=5, pady=5, sticky="ew")

        # Row 3: Date
        ttk.Label(input_frame, text="日期:").grid(row=3, column=0, padx=5, pady=5, sticky="e")
        self.sales_date_entry = ttk.Entry(input_frame)
        self.sales_date_entry.insert(0, datetime.now().strftime("%Y-%m-%d"))
        self.sales_date_entry.grid(row=3, column=1, padx=5, pady=5, sticky="ew")

        # Row 4: Order Number
        ttk.Label(input_frame, text="单号:").grid(row=4, column=0, padx=5, pady=5, sticky="e")
        self.sales_order_number_entry = ttk.Entry(input_frame)
        self.sales_order_number_entry.grid(row=4, column=1, padx=5, pady=5, sticky="ew")

        # Row 5: Quantity (Liters)
        ttk.Label(input_frame, text="数量(升):").grid(row=5, column=0, padx=5, pady=5, sticky="e")
        self.sales_quantity_entry = ttk.Entry(input_frame)
        self.sales_quantity_entry.grid(row=5, column=1, padx=5, pady=5, sticky="ew")

        # Bind Enter key for sales fields
        sales_entries_for_enter = [
            self.sales_price_entry,
            self.sales_date_entry,
            self.sales_order_number_entry,
            self.sales_quantity_entry
        ]
        for entry in sales_entries_for_enter:
            entry.bind("<Return>", lambda e: self.add_sales_record())
            entry.bind("<KP_Enter>", lambda e: self.add_sales_record()) # Numpad Enter
        # --- End Reordered Fields ---

        # --- Action Frame (Row 1) ---
        action_frame_sales = ttk.Frame(self.sales_tab)
        action_frame_sales.grid(row=1, column=0, padx=10, pady=5, sticky="ew")
        action_frame_sales.columnconfigure(1, weight=1) # Allow label to push button right

        self.remaining_liters_label = ttk.Label(action_frame_sales, text="剩余升数: 0.00")
        self.remaining_liters_label.grid(row=0, column=0, padx=5, pady=5, sticky="w")

        ttk.Button(action_frame_sales, text="添加销售记录", command=self.add_sales_record).grid(row=0, column=2, padx=5, pady=5, sticky="e")

        # --- Sales Records List Frame (Row 2 - Expands) ---
        list_frame = ttk.LabelFrame(self.sales_tab, text="销售记录")
        list_frame.grid(row=2, column=0, padx=10, pady=10, sticky="nsew")
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)

        # Changed columns to include display_id first
        sales_columns = ("display_id", "customer_name", "sale_date", "order_number", "price_per_liter", "quantity_liter", "total_price")
        self.sales_tree = ttk.Treeview(list_frame, columns=sales_columns, show="headings")
        # Column configuration
        self.sales_tree.heading("display_id", text="序号") # Changed heading
        self.sales_tree.column("display_id", width=40, stretch=False, anchor="center") # Changed column name
        self.sales_tree.heading("customer_name", text="客户名称")
        self.sales_tree.column("customer_name", width=150)
        self.sales_tree.heading("sale_date", text="销售日期")
        self.sales_tree.column("sale_date", width=100, anchor="center")
        self.sales_tree.heading("order_number", text="单号")
        self.sales_tree.column("order_number", width=100)
        self.sales_tree.heading("price_per_liter", text="单价(元/升)")
        self.sales_tree.column("price_per_liter", width=100, anchor="e")
        self.sales_tree.heading("quantity_liter", text="数量(升)")
        self.sales_tree.column("quantity_liter", width=100, anchor="e")
        self.sales_tree.heading("total_price", text="总价(元)")
        self.sales_tree.column("total_price", width=100, anchor="e")
        self.sales_tree.grid(row=0, column=0, sticky="nsew")

        # Scrollbar
        sales_scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.sales_tree.yview)
        self.sales_tree.configure(yscrollcommand=sales_scrollbar.set)
        sales_scrollbar.grid(row=0, column=1, sticky="ns")

        # --- Edit/Delete Buttons Frame (Row 3) ---
        edit_delete_frame = ttk.Frame(self.sales_tab)
        edit_delete_frame.grid(row=3, column=0, padx=10, pady=5, sticky="e")

        ttk.Button(edit_delete_frame, text="编辑选中记录", command=self.edit_sales_record).pack(side="left", padx=5)
        ttk.Button(edit_delete_frame, text="删除选中记录", command=self.delete_sales_record).pack(side="left", padx=5)

        # Initialize customer data and lists (already done in __init__)
        # self.customer_data = {} # Dictionary to store {name: id}
        # self.refresh_customer_names() # Populate combobox and data dict
        self.refresh_sales_list()
        self.update_remaining_liters()

    def update_customer_combobox_filter(self, event):
        """Filters the customer combobox based on the search entry."""
        search_term = self.sales_customer_search_entry.get().lower()
        # Use self.customer_data which stores {name: id}
        filtered_names = sorted([name for name in self.customer_data if search_term in name.lower()])

        current_selection = self.sales_customer_combobox.get() # Store current selection

        if filtered_names:
            self.sales_customer_combobox['values'] = filtered_names
            # Try to keep current selection if it's still valid, otherwise select first match
            if current_selection in filtered_names:
                 self.sales_customer_combobox.set(current_selection)
            else:
                first_match = filtered_names[0]
                self.sales_customer_combobox.set(first_match)
            # Update selected_customer_id based on the final combobox value
            self.selected_customer_id = self.customer_data.get(self.sales_customer_combobox.get())
            # Trigger order number update after filtering confirms a selection
            self._update_next_sales_order_number(self.selected_customer_id)
        else:
            # No match found
            self.sales_customer_combobox['values'] = []
            self.sales_customer_combobox.set('') # Clear selection
            self.selected_customer_id = None
            # Also clear order number if no customer is selected
            self._update_next_sales_order_number(None)

    def _update_next_sales_order_number(self, customer_id):
        """
        Fetches the last order number. If numeric: increments it.
        If the original numeric number started with '0', ensures the result also
        starts with '0', potentially increasing the total length (e.g., 09999 -> 010000).
        Otherwise (non-numeric, no record, or original numeric didn't start with '0'),
        defaults to '01'.
        """
        next_order_number = "01" # Default value

        if customer_id and self.conn:
            try:
                with self.conn:
                    cursor = self.conn.cursor()
                    cursor.execute("SELECT order_number FROM sales WHERE customer_id = ? ORDER BY id DESC LIMIT 1", (customer_id,))
                    last_order_result = cursor.fetchone()

                    if last_order_result and last_order_result[0]:
                        last_order_num_str = last_order_result[0]
                        # Check if the last order number is purely numeric
                        if last_order_num_str.isdigit():
                            started_with_zero = last_order_num_str.startswith('0')
                            try:
                                original_length = len(last_order_num_str)
                                next_num = int(last_order_num_str) + 1
                                next_num_str = str(next_num)

                                if started_with_zero:
                                    # First, pad to at least the original length
                                    padded_to_original = next_num_str.zfill(original_length)
                                    # If, after padding, it *still* doesn't start with '0'
                                    # (e.g., 09->10, 09999->10000), prepend an extra '0'.
                                    if not padded_to_original.startswith('0'):
                                         next_order_number = '0' + padded_to_original # Force leading zero
                                    else:
                                         next_order_number = padded_to_original
                                else:
                                    # Original didn't start with '0', just use the incremented number directly
                                    next_order_number = next_num_str
                            except ValueError:
                                # Should not happen if isdigit() is true, but as fallback
                                print(f"Error converting supposedly numeric '{last_order_num_str}' to int.")
                                next_order_number = "01" # Default back
                        else:
                            # Last order number was not purely numeric, use default
                            print(f"Last order number '{last_order_num_str}' is not numeric. Defaulting to '01'.")
                            next_order_number = "01"
                    # else: No last record found, default "01" is already set

            except sqlite3.Error as e:
                print(f"Error fetching last order number: {e}")
                next_order_number = "01" # Default on DB error

        # Update the entry field
        self.sales_order_number_entry.delete(0, tk.END)
        self.sales_order_number_entry.insert(0, next_order_number)

    def on_customer_selected(self, event):
        """Updates selected_customer_id and triggers order number update."""
        selected_name = self.sales_customer_combobox.get()
        self.selected_customer_id = self.customer_data.get(selected_name)
        # Call the helper function to update the order number
        self._update_next_sales_order_number(self.selected_customer_id)

    def edit_sales_record(self):
        selected = self.sales_tree.selection()
        if not selected:
            messagebox.showwarning("警告", "请先选择要编辑的销售记录")
            return

        # Get the database ID (iid) directly from the selection
        db_id = selected[0]
        # Get display values
        item_values = self.sales_tree.item(db_id, 'values')
        display_id, customer_name, sale_date, order_number, price_per_liter, quantity_liter, total_price = item_values

        original_customer_id = None
        original_quantity_liter = None
        if self.conn: # Add check
            try:
                with self.conn:
                    cursor = self.conn.cursor()
                    # Fetch original data using the actual database ID (db_id)
                    cursor.execute("SELECT customer_id, quantity_liter FROM sales WHERE id = ?", (db_id,))
                    result = cursor.fetchone()
                    if result:
                        original_customer_id = result[0]
                        original_quantity_liter = result[1]
                    else:
                        messagebox.showerror("错误", f"找不到销售记录 ID: {db_id}")
                        return
            except sqlite3.Error as e:
                 messagebox.showerror("数据库错误", f"无法获取原始销售数据: {e}")
                 return
        else:
             messagebox.showerror("数据库错误", "数据库连接丢失")
             return

        if original_customer_id is None or original_quantity_liter is None:
             messagebox.showerror("错误", "无法获取原始销售记录的关键信息。")
             return

        edit_dialog = tk.Toplevel(self.root)
        edit_dialog.title(f"编辑销售记录 (序号: {display_id})") # Show display ID
        edit_dialog.geometry("350x250")
        edit_dialog.transient(self.root)
        edit_dialog.grab_set()

        # Use a frame for better layout
        dialog_frame = ttk.Frame(edit_dialog, padding="10")
        dialog_frame.pack(fill="both", expand=True)

        # Fields to edit (Customer is not editable here), use fetched display values
        fields_info = [
            ("销售日期:", sale_date, False), # Label, Initial Value, ReadOnly flag
            ("单号:", order_number, False),
            ("单价(元/升):", price_per_liter, False),
            ("数量(升):", quantity_liter, False)
        ]

        entries = {}
        for i, (label_text, initial_value, is_readonly) in enumerate(fields_info):
            label = ttk.Label(dialog_frame, text=label_text)
            label.grid(row=i, column=0, padx=5, pady=5, sticky="e")
            entry = ttk.Entry(dialog_frame, width=25)
            entry.insert(0, str(initial_value))
            if is_readonly:
                entry.config(state="readonly")
            entry.grid(row=i, column=1, padx=5, pady=5, sticky="w")
            entries[label_text] = entry

        def save_changes():
            try:
                new_sale_date = entries["销售日期:"].get().strip()
                new_order_number = entries["单号:"].get().strip()
                new_price_per_liter_str = entries["单价(元/升):"].get().strip()
                new_quantity_liter_str = entries["数量(升):"].get().strip()

                if not new_sale_date: raise ValueError("销售日期不能为空")
                if not new_order_number: raise ValueError("单号不能为空") # Basic check
                if not new_price_per_liter_str: raise ValueError("单价不能为空")
                if not new_quantity_liter_str: raise ValueError("数量不能为空")

                new_price_per_liter = float(new_price_per_liter_str)
                new_quantity_liter = float(new_quantity_liter_str)

                if new_price_per_liter <= 0: raise ValueError("单价必须大于0")
                if new_quantity_liter <= 0: raise ValueError("数量必须大于0")

                new_total_price = new_price_per_liter * new_quantity_liter

                quantity_change = new_quantity_liter - original_quantity_liter
                current_remaining = self.calculate_remaining_liters()

                # Check if enough stock for the *increase* only
                if quantity_change > 0 and quantity_change > current_remaining:
                     messagebox.showwarning("库存不足", f"编辑后增加的数量 ({quantity_change:.2f} 升) 超过当前剩余库存 ({current_remaining:.2f} 升)。", parent=edit_dialog)
                     return

                if self.conn: # Add check
                    with self.conn:
                        cursor = self.conn.cursor()
                        # Check for duplicate sales order number (excluding current record, using db_id)
                        cursor.execute("SELECT id FROM sales WHERE order_number = ? AND id != ?", (new_order_number, db_id))
                        if cursor.fetchone():
                            messagebox.showerror("错误", f"销售单号 '{new_order_number}' 已存在", parent=edit_dialog)
                            return

                        cursor.execute('''
                            UPDATE sales SET
                                sale_date = ?,
                                order_number = ?,
                                price_per_liter = ?,
                                quantity_liter = ?,
                                total_price = ?
                            WHERE id = ?
                        ''', (new_sale_date, new_order_number, new_price_per_liter, new_quantity_liter, new_total_price, db_id)) # Use db_id here
                    edit_dialog.destroy()
                    self.refresh_sales_list() # Handles auto-scroll and renumbering
                    self.update_remaining_liters()
                    self.refresh_statistics() # Refresh stats after editing sale
                    # Removed success messagebox
                else:
                    messagebox.showerror("数据库错误", "数据库连接丢失", parent=edit_dialog)
                    # Keep dialog open

            except ValueError as e:
                messagebox.showerror("输入错误", f"输入无效: {e}", parent=edit_dialog)
            except sqlite3.Error as e:
                 messagebox.showerror("数据库错误", f"无法更新销售记录: {e}", parent=edit_dialog)

        save_button = ttk.Button(dialog_frame, text="保存更改", command=save_changes)
        save_button.grid(row=len(fields_info), column=0, columnspan=2, pady=15)

        entries["销售日期:"].focus()
        self.root.wait_window(edit_dialog)

    def delete_sales_record(self):
        selected = self.sales_tree.selection()
        if not selected:
            messagebox.showwarning("警告", "请先选择要删除的销售记录")
            return

        # Get the database ID (iid) directly from the selection
        db_id = selected[0]
        # Get display values for confirmation
        item_values = self.sales_tree.item(db_id, 'values')
        display_id = item_values[0] # Display ID is first

        if messagebox.askyesno("确认删除", f"确定要删除销售记录 (序号: {display_id}) 吗？"):
            if self.conn: # Add check
                try:
                    with self.conn:
                        cursor = self.conn.cursor()
                        # Delete using the actual database ID (db_id)
                        cursor.execute("DELETE FROM sales WHERE id = ?", (db_id,))
                    self.refresh_sales_list() # Refresh to renumber display IDs
                    self.update_remaining_liters()
                    self.refresh_statistics() # Refresh stats after deleting sale
                except sqlite3.Error as e:
                    messagebox.showerror("数据库错误", f"删除销售记录时出错: {e}")
            else:
                messagebox.showerror("数据库错误", "数据库连接丢失")
                return

    def create_statistics_tab(self):
        # Create Statistics tab
        self.statistics_tab = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(self.statistics_tab, text="数据统计")
        self.statistics_tab.columnconfigure(0, weight=1) # Allow content to expand

        # --- Filters Frame ---
        filter_frame = ttk.LabelFrame(self.statistics_tab, text="筛选条件")
        filter_frame.grid(row=0, column=0, padx=10, pady=5, sticky="ew")
        filter_frame.columnconfigure(1, weight=1) # Allow entries/combobox to expand slightly
        filter_frame.columnconfigure(3, weight=1)
        filter_frame.columnconfigure(5, weight=1)

        ttk.Label(filter_frame, text="开始日期:").grid(row=0, column=0, padx=5, pady=5, sticky="e")
        self.stats_start_date_entry = ttk.Entry(filter_frame)
        self.stats_start_date_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        # Placeholder for potential calendar picker later

        ttk.Label(filter_frame, text="结束日期:").grid(row=0, column=2, padx=5, pady=5, sticky="e")
        self.stats_end_date_entry = ttk.Entry(filter_frame)
        self.stats_end_date_entry.grid(row=0, column=3, padx=5, pady=5, sticky="ew")
        self.stats_end_date_entry.insert(0, datetime.now().strftime("%Y-%m-%d")) # Default to today

        ttk.Label(filter_frame, text="选择客户:").grid(row=0, column=4, padx=5, pady=5, sticky="e")
        self.stats_customer_combobox = ttk.Combobox(filter_frame, state="readonly", width=25)
        self.stats_customer_combobox.grid(row=0, column=5, padx=5, pady=5, sticky="ew")

        refresh_button = ttk.Button(filter_frame, text="刷新统计", command=self.refresh_statistics)
        refresh_button.grid(row=0, column=6, padx=10, pady=5)

        # --- Results Frame ---
        results_frame = ttk.Frame(self.statistics_tab)
        results_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
        results_frame.columnconfigure(0, weight=1)
        results_frame.columnconfigure(1, weight=1)
        results_frame.columnconfigure(2, weight=1) # Add a third column for profit
        self.statistics_tab.rowconfigure(1, weight=1) # Allow results frame to expand

        # --- Inventory Stats Frame ---
        inv_stats_frame = ttk.LabelFrame(results_frame, text="入库统计 (全部)")
        inv_stats_frame.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")
        inv_stats_frame.columnconfigure(1, weight=1)

        self.inv_stats_count_label = ttk.Label(inv_stats_frame, text="入库次数: 0")
        self.inv_stats_count_label.grid(row=0, column=0, columnspan=2, padx=5, pady=2, sticky="w")
        self.inv_stats_tons_label = ttk.Label(inv_stats_frame, text="总入库量 (吨): 0.00")
        self.inv_stats_tons_label.grid(row=1, column=0, columnspan=2, padx=5, pady=2, sticky="w")
        self.inv_stats_liters_label = ttk.Label(inv_stats_frame, text="总入库量 (升): 0.00")
        self.inv_stats_liters_label.grid(row=2, column=0, columnspan=2, padx=5, pady=2, sticky="w")
        self.inv_stats_remaining_label = ttk.Label(inv_stats_frame, text="当前库存余量 (升): 0.00")
        self.inv_stats_remaining_label.grid(row=3, column=0, columnspan=2, padx=5, pady=2, sticky="w")

        # --- Sales Stats Frame ---
        sales_stats_frame = ttk.LabelFrame(results_frame, text="销售统计 (根据筛选)")
        sales_stats_frame.grid(row=0, column=1, padx=5, pady=5, sticky="nsew")
        sales_stats_frame.columnconfigure(1, weight=1)

        self.sales_stats_count_label = ttk.Label(sales_stats_frame, text="交易次数: 0")
        self.sales_stats_count_label.grid(row=0, column=0, columnspan=2, padx=5, pady=2, sticky="w")
        self.sales_stats_avg_price_label = ttk.Label(sales_stats_frame, text="平均单价 (元/升): 0.00")
        self.sales_stats_avg_price_label.grid(row=1, column=0, columnspan=2, padx=5, pady=2, sticky="w")
        self.sales_stats_liters_label = ttk.Label(sales_stats_frame, text="总销售量 (升): 0.00")
        self.sales_stats_liters_label.grid(row=2, column=0, columnspan=2, padx=5, pady=2, sticky="w")
        self.sales_stats_revenue_label = ttk.Label(sales_stats_frame, text="总销售额 (元): 0.00")
        self.sales_stats_revenue_label.grid(row=3, column=0, columnspan=2, padx=5, pady=2, sticky="w")

        # --- Profit Stats Frame ---
        profit_stats_frame = ttk.LabelFrame(results_frame, text="利润统计 (估算*)")
        profit_stats_frame.grid(row=0, column=2, rowspan=2, padx=5, pady=5, sticky="nsew") # Span 2 rows
        profit_stats_frame.columnconfigure(1, weight=1)
        profit_stats_frame.rowconfigure(4, weight=1) # Allow treeview to expand

        self.profit_stats_total_label = ttk.Label(profit_stats_frame, text="总利润 (元): 0.00")
        self.profit_stats_total_label.grid(row=0, column=0, columnspan=2, padx=5, pady=2, sticky="w")
        self.profit_stats_avg_liter_label = ttk.Label(profit_stats_frame, text="每升平均利润 (元): 0.00")
        self.profit_stats_avg_liter_label.grid(row=1, column=0, columnspan=2, padx=5, pady=2, sticky="w")
        self.profit_stats_avg_ton_label = ttk.Label(profit_stats_frame, text="每吨平均利润 (元): 0.00")
        self.profit_stats_avg_ton_label.grid(row=2, column=0, columnspan=2, padx=5, pady=2, sticky="w")
        ttk.Label(profit_stats_frame, text="*基于全部库存的平均成本估算").grid(row=3, column=0, columnspan=2, padx=5, pady=0, sticky="w")

        # Monthly Profit Treeview
        monthly_profit_frame = ttk.LabelFrame(profit_stats_frame, text="月度利润 (估算)")
        monthly_profit_frame.grid(row=4, column=0, columnspan=2, padx=5, pady=5, sticky="nsew")
        monthly_profit_frame.columnconfigure(0, weight=1)
        monthly_profit_frame.rowconfigure(0, weight=1)

        self.monthly_profit_tree = ttk.Treeview(monthly_profit_frame, columns=("month", "revenue", "cost", "profit"), show="headings")
        self.monthly_profit_tree.heading("month", text="月份")
        self.monthly_profit_tree.column("month", width=80, anchor="center")
        self.monthly_profit_tree.heading("revenue", text="销售额")
        self.monthly_profit_tree.column("revenue", width=80, anchor="e")
        self.monthly_profit_tree.heading("cost", text="估算成本")
        self.monthly_profit_tree.column("cost", width=80, anchor="e")
        self.monthly_profit_tree.heading("profit", text="估算利润")
        self.monthly_profit_tree.column("profit", width=80, anchor="e")
        self.monthly_profit_tree.grid(row=0, column=0, sticky="nsew")

        monthly_scrollbar = ttk.Scrollbar(monthly_profit_frame, orient="vertical", command=self.monthly_profit_tree.yview)
        self.monthly_profit_tree.configure(yscrollcommand=monthly_scrollbar.set)
        monthly_scrollbar.grid(row=0, column=1, sticky="ns")

        # Customer combobox will be populated by refresh_customer_names -> update_stats_customer_combobox

    # --- Statistics Tab Methods ---
    def update_stats_customer_combobox(self):
        """Updates the customer combobox in the statistics tab."""
        # Ensure self.customer_data is initialized
        if not hasattr(self, 'customer_data'):
             self.customer_data = {} # Initialize if called before refresh_customer_names

        # Use self.customer_data which is {name: id} populated by refresh_customer_names
        names = ["所有客户"] + sorted(self.customer_data.keys())
        self.stats_customer_combobox['values'] = names
        if names:
            # Try to preserve selection if possible, otherwise default to "所有客户"
            current_selection = self.stats_customer_combobox.get()
            if current_selection in names:
                self.stats_customer_combobox.set(current_selection)
            else:
                self.stats_customer_combobox.current(0)
        else:
             self.stats_customer_combobox.set('') # Clear if no customers

    def refresh_statistics(self):
        """Calculates and displays all statistics based on filters."""
        if not self.conn:
            messagebox.showerror("错误", "数据库连接丢失，无法刷新统计数据")
            return

        try:
            # --- 1. Inventory Statistics (Always Full History) ---
            cursor = self.conn.cursor()
            cursor.execute("SELECT COUNT(*), SUM(quantity_ton), SUM(total_liters) FROM inventory")
            inv_count, inv_tons, inv_liters = cursor.fetchone()
            inv_count = inv_count or 0
            inv_tons = inv_tons or 0.0
            inv_liters = inv_liters or 0.0
            remaining_liters = self.calculate_remaining_liters() # Use existing method

            self.inv_stats_count_label.config(text=f"入库次数: {inv_count}")
            self.inv_stats_tons_label.config(text=f"总入库量 (吨): {inv_tons:.2f}")
            self.inv_stats_liters_label.config(text=f"总入库量 (升): {inv_liters:.2f}")
            self.inv_stats_remaining_label.config(text=f"当前库存余量 (升): {remaining_liters:.2f}")

            # --- 2. Sales Statistics (Based on Filters) ---
            start_date_str = self.stats_start_date_entry.get().strip()
            end_date_str = self.stats_end_date_entry.get().strip()
            selected_customer_name = self.stats_customer_combobox.get()

            # Build WHERE clause and parameters
            where_clauses = []
            params = []

            # Date filtering
            # Set default start date if empty
            if not start_date_str:
                 # Find the earliest sale date if start date is empty
                 cursor.execute("SELECT MIN(sale_date) FROM sales")
                 min_date_result = cursor.fetchone()
                 start_date_str = min_date_result[0] if min_date_result and min_date_result[0] else None
                 if start_date_str:
                     self.stats_start_date_entry.delete(0, tk.END)
                     self.stats_start_date_entry.insert(0, start_date_str)
                     # Add to where clause only if a valid date was found
                     where_clauses.append("s.sale_date >= ?")
                     params.append(start_date_str)
                 # No need to add to where_clauses if it remains None

            elif start_date_str:
                try:
                    datetime.strptime(start_date_str, "%Y-%m-%d")
                    where_clauses.append("s.sale_date >= ?")
                    params.append(start_date_str)
                except ValueError:
                    messagebox.showerror("日期错误", "开始日期格式无效，请使用 YYYY-MM-DD")
                    return

            if end_date_str:
                try:
                    datetime.strptime(end_date_str, "%Y-%m-%d")
                    where_clauses.append("s.sale_date <= ?")
                    params.append(end_date_str)
                except ValueError:
                    messagebox.showerror("日期错误", "结束日期格式无效，请使用 YYYY-MM-DD")
                    return
            # If end_date is empty, no upper bound is applied

            # Customer filtering
            stats_customer_id = None
            if selected_customer_name and selected_customer_name != "所有客户":
                stats_customer_id = self.customer_data.get(selected_customer_name)
                if stats_customer_id:
                    where_clauses.append("s.customer_id = ?")
                    params.append(stats_customer_id)
                else:
                    # Should not happen if combobox is populated correctly
                    print(f"Warning: Could not find ID for customer '{selected_customer_name}'")

            where_sql = " AND ".join(where_clauses) if where_clauses else "1=1" # Use 1=1 if no filters

            # Query for sales stats
            sales_query = f"""
                SELECT
                    COUNT(s.id),
                    AVG(s.price_per_liter),
                    SUM(s.quantity_liter),
                    SUM(s.total_price)
                FROM sales s
                WHERE {where_sql}
            """
            cursor.execute(sales_query, params)
            sales_count, sales_avg_price, sales_liters, sales_revenue = cursor.fetchone()
            sales_count = sales_count or 0
            sales_avg_price = sales_avg_price or 0.0
            sales_liters = sales_liters or 0.0
            sales_revenue = sales_revenue or 0.0

            self.sales_stats_count_label.config(text=f"交易次数: {sales_count}")
            self.sales_stats_avg_price_label.config(text=f"平均单价 (元/升): {sales_avg_price:.2f}")
            self.sales_stats_liters_label.config(text=f"总销售量 (升): {sales_liters:.2f}")
            self.sales_stats_revenue_label.config(text=f"总销售额 (元): {sales_revenue:.2f}")

            # --- 3. Profit Statistics (Estimation) ---
            total_profit = 0.0
            avg_profit_liter = 0.0
            avg_profit_ton = 0.0

            # Calculate overall average cost per liter from ALL inventory
            cursor.execute("""
                SELECT SUM(price_per_ton * quantity_ton), SUM(total_liters)
                FROM inventory
            """)
            total_inv_cost_result, total_inv_liters_result = cursor.fetchone()
            total_inv_cost = total_inv_cost_result or 0.0
            total_inv_liters = total_inv_liters_result or 0.0

            overall_avg_cost_liter = 0.0
            if total_inv_liters > 0:
                 # Cost is price_per_ton * quantity_ton. We need cost per liter.
                 # Total cost = SUM(price_per_ton * quantity_ton)
                 # Total liters = SUM(total_liters)
                 # Avg cost per liter = Total cost / Total liters
                 # However, price_per_ton is in Yuan/Ton. total_liters is in Liters.
                 # We need cost in Yuan. SUM(price_per_ton * quantity_ton) gives total Yuan cost.
                 overall_avg_cost_liter = total_inv_cost / total_inv_liters

            # Calculate estimated profit for the filtered period
            if sales_count > 0:
                estimated_cogs = sales_liters * overall_avg_cost_liter
                total_profit = sales_revenue - estimated_cogs
                if sales_liters > 0:
                    avg_profit_liter = total_profit / sales_liters

                # Estimate average density to convert sales liters to tons for avg profit/ton
                cursor.execute("SELECT AVG(density) FROM inventory")
                avg_density_result = cursor.fetchone()
                avg_density = avg_density_result[0] if avg_density_result and avg_density_result[0] else 0.84 # Default if no inventory
                if avg_density > 0:
                    sales_tons_estimated = (sales_liters / 1000) * avg_density
                    if sales_tons_estimated > 0:
                        avg_profit_ton = total_profit / sales_tons_estimated

            self.profit_stats_total_label.config(text=f"总利润 (元): {total_profit:.2f}")
            self.profit_stats_avg_liter_label.config(text=f"每升平均利润 (元): {avg_profit_liter:.2f}")
            self.profit_stats_avg_ton_label.config(text=f"每吨平均利润 (元): {avg_profit_ton:.2f}")

            # --- Monthly Profit ---
            # Clear previous treeview data
            for item in self.monthly_profit_tree.get_children():
                self.monthly_profit_tree.delete(item)

            # Query monthly sales data based on filters
            monthly_query = f"""
                SELECT
                    strftime('%Y-%m', s.sale_date) as sale_month,
                    SUM(s.total_price) as monthly_revenue,
                    SUM(s.quantity_liter) as monthly_liters
                FROM sales s
                WHERE {where_sql}
                GROUP BY sale_month
                ORDER BY sale_month ASC
            """
            cursor.execute(monthly_query, params)
            monthly_data = cursor.fetchall()

            for month, monthly_revenue, monthly_liters in monthly_data:
                monthly_revenue = monthly_revenue or 0.0
                monthly_liters = monthly_liters or 0.0
                monthly_estimated_cogs = monthly_liters * overall_avg_cost_liter
                monthly_profit = monthly_revenue - monthly_estimated_cogs
                self.monthly_profit_tree.insert("", "end", values=(
                    month,
                    f"{monthly_revenue:.2f}",
                    f"{monthly_estimated_cogs:.2f}",
                    f"{monthly_profit:.2f}"
                ))

        except sqlite3.Error as e:
            messagebox.showerror("数据库错误", f"统计查询失败: {e}")
        except Exception as e:
             # Print detailed error for debugging
             traceback.print_exc()
             messagebox.showerror("错误", f"计算统计数据时发生意外错误: {e}")
    # --- End Statistics Tab Methods ---


    def save_customer(self):
        name = self.customer_name_entry.get().strip()
        if name:
            if self.conn: # Add check
                try:
                    with self.conn:
                        cursor = self.conn.cursor()
                        # Check if customer name already exists
                        cursor.execute("SELECT id FROM customers WHERE name = ?", (name,))
                        if cursor.fetchone():
                            messagebox.showerror("错误", f"客户名称 '{name}' 已存在")
                            return
                        cursor.execute("INSERT INTO customers (name) VALUES (?)", (name,))
                    self.customer_name_entry.delete(0, tk.END)
                    self.refresh_customer_list() # Refresh to show new customer and renumber
                    self.refresh_customer_names() # Update combobox in sales tab
                    self.update_stats_customer_combobox() # Update stats tab combobox too
                except sqlite3.Error as e:
                    messagebox.showerror("数据库错误", f"保存客户时出错: {e}")
            else:
                messagebox.showerror("数据库错误", "数据库连接丢失")
                return
        else:
            messagebox.showwarning("警告", "客户名称不能为空")

    def refresh_customer_list(self):
        # Clear list
        for row in self.customer_tree.get_children():
            self.customer_tree.delete(row)

        # Reload
        last_inserted_iid = None
        if self.conn: # Add check
            try:
                with self.conn:
                    cursor = self.conn.cursor()
                    # Order by id ASC to ensure sequential display ID matches insertion order
                    cursor.execute("SELECT id, name FROM customers ORDER BY id ASC")
                    # Use enumerate to generate display ID (starts from 1)
                    for display_id, (db_id, name) in enumerate(cursor.fetchall(), start=1):
                        item_iid = str(db_id)
                        # Use db_id as iid, display_id as first value
                        self.customer_tree.insert("", "end", iid=item_iid, values=(display_id, name))
                        last_inserted_iid = item_iid # Keep track of the last one
            except sqlite3.Error as e:
                messagebox.showerror("数据库错误", f"无法加载客户列表: {e}")
        else:
            messagebox.showerror("数据库错误", "无法加载客户列表，数据库连接丢失")

        # --- Auto-scroll Customer Table to Bottom ---
        if last_inserted_iid:
            try:
                self.customer_tree.selection_set(last_inserted_iid)
                self.customer_tree.see(last_inserted_iid)
            except Exception as e:
                print(f"Error auto-scrolling customer table: {e}")
        # --- End Auto-scroll ---


    def refresh_sales_list(self):
        # Clear list
        for row in self.sales_tree.get_children():
            self.sales_tree.delete(row)

        # Reload using JOIN to get customer name
        last_inserted_iid = None
        if self.conn: # Add check
            try:
                with self.conn:
                    cursor = self.conn.cursor()
                    # Order by sales id ASC for sequential display ID
                    cursor.execute('''
                        SELECT s.id, c.name, s.sale_date, s.order_number, s.price_per_liter, s.quantity_liter, s.total_price
                        FROM sales s
                        LEFT JOIN customers c ON s.customer_id = c.id
                        ORDER BY s.id ASC
                    ''')
                    rows = cursor.fetchall()
                    # Use enumerate to generate display ID (starts from 1)
                    for display_id, row in enumerate(rows, start=1):
                        db_id, cust_name, sale_date, order_num, price, qty, total = row
                        # Initialize list with string representation of display_id
                        formatted_row = [str(display_id)]
                        formatted_row.append(str(cust_name) if cust_name else "未知客户")
                        formatted_row.append(str(sale_date))
                        formatted_row.append(str(order_num))
                        # Format numbers for display (already strings)
                        formatted_row.append(f"{price:.2f}" if price is not None else "0.00")
                        formatted_row.append(f"{qty:.2f}" if qty is not None else "0.00")
                        formatted_row.append(f"{total:.2f}" if total is not None else "0.00")

                        # Use the database ID (db_id) as the item ID (iid) in the treeview
                        item_iid = str(db_id)
                        self.sales_tree.insert("", "end", iid=item_iid, values=tuple(formatted_row))
                        last_inserted_iid = item_iid # Keep track of the last one

                    # --- Auto-scroll Sales Table to Bottom ---
                    if last_inserted_iid:
                        try:
                            # Select the last inserted item
                            self.sales_tree.selection_set(last_inserted_iid)
                            # Scroll to make the last inserted item visible (at the bottom)
                            self.sales_tree.see(last_inserted_iid)
                        except Exception as e:
                            print(f"Error auto-scrolling sales table: {e}")
                    # --- End Auto-scroll ---

            except sqlite3.Error as e:
                messagebox.showerror("数据库错误", f"无法加载销售列表: {e}")
        else:
            messagebox.showerror("数据库错误", "无法加载销售列表，数据库连接丢失")

    def refresh_customer_names(self):
        # Refreshes the customer data dictionary and the combobox
        self.customer_data = {}
        customer_names_list = []
        if self.conn: # Add check
            try:
                with self.conn:
                    cursor = self.conn.cursor()
                    # Order by name for the combobox display
                    cursor.execute("SELECT id, name FROM customers ORDER BY name")
                    for customer_id, name in cursor.fetchall():
                        self.customer_data[name] = customer_id
                        customer_names_list.append(name)
            except sqlite3.Error as e:
                messagebox.showerror("数据库错误", f"无法加载客户名称: {e}")
                self.customer_data = {}
                customer_names_list = []
        else:
            messagebox.showerror("数据库错误", "无法加载客户名称，数据库连接丢失")
            self.customer_data = {}
            customer_names_list = []

        # Update sales tab combobox values and selection
        current_search = self.sales_customer_search_entry.get().lower()
        if current_search: # If there's a search term, filter based on it
             filtered_names = sorted([name for name in customer_names_list if current_search in name.lower()])
             self.sales_customer_combobox['values'] = filtered_names
             if filtered_names:
                 self.sales_customer_combobox.set(filtered_names[0])
             else:
                 self.sales_customer_combobox.set('')
        else: # Otherwise, show all names
            self.sales_customer_combobox['values'] = customer_names_list
            if customer_names_list:
                 # Try to keep current selection if valid, else select first
                 current_selection = self.sales_customer_combobox.get()
                 if current_selection not in customer_names_list:
                     # Avoid setting index if list is empty
                     if self.sales_customer_combobox['values']:
                         self.sales_customer_combobox.current(0)
                     else:
                         self.sales_customer_combobox.set('')
                 # else keep current selection
            else:
                self.sales_customer_combobox.set('')

        # Update selected_customer_id based on the final combobox value
        # And trigger order number update
        final_selected_name = self.sales_customer_combobox.get()
        self.selected_customer_id = self.customer_data.get(final_selected_name)
        self._update_next_sales_order_number(self.selected_customer_id)

        # Update stats tab combobox as well, after sales tab is updated
        self.update_stats_customer_combobox()


    def add_sales_record(self):
        # Get selected customer name and find ID
        selected_name = self.sales_customer_combobox.get()
        customer_id = self.customer_data.get(selected_name)

        if customer_id is None:
            messagebox.showerror("错误", "请先选择一个有效的客户")
            return

        sale_date = self.sales_date_entry.get().strip()
        order_number = self.sales_order_number_entry.get().strip() # Sales order number

        if not sale_date:
             messagebox.showerror("错误", "销售日期不能为空")
             return
        # Add check for empty sales order number
        if not order_number:
             messagebox.showerror("错误", "销售单号不能为空")
             return

        try:
            price_per_liter_str = self.sales_price_entry.get().strip()
            quantity_liter_str = self.sales_quantity_entry.get().strip()

            if not price_per_liter_str: raise ValueError("单价不能为空")
            if not quantity_liter_str: raise ValueError("数量不能为空")

            price_per_liter = float(price_per_liter_str)
            quantity_liter = float(quantity_liter_str)

            if price_per_liter <= 0: raise ValueError("单价必须大于0")
            if quantity_liter <= 0: raise ValueError("数量必须大于0")

            total_price = price_per_liter * quantity_liter

            current_remaining = self.calculate_remaining_liters()
            if quantity_liter > current_remaining:
                messagebox.showwarning("库存不足", f"当前剩余库存 {current_remaining:.2f} 升，不足以销售 {quantity_liter:.2f} 升。")
                return

            if self.conn: # Add check
                with self.conn:
                    cursor = self.conn.cursor()
                    # Check for duplicate sales order number before inserting
                    cursor.execute("SELECT id FROM sales WHERE order_number = ?", (order_number,))
                    if cursor.fetchone():
                        messagebox.showerror("错误", f"销售单号 '{order_number}' 已存在")
                        return

                    cursor.execute('''
                        INSERT INTO sales (customer_id, sale_date, order_number, price_per_liter, quantity_liter, total_price)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (customer_id, sale_date, order_number, price_per_liter, quantity_liter, total_price))

                # Clear specific input fields after successful insertion
                self.sales_order_number_entry.delete(0, tk.END)
                # self.sales_price_entry.delete(0, tk.END) # Keep price
                self.sales_quantity_entry.delete(0, tk.END)
                # Keep customer, date, and price

                # Auto-fill next order number for the *same* customer after adding
                self._update_next_sales_order_number(customer_id) # Use current customer_id

                self.refresh_sales_list() # This now handles auto-scroll
                self.update_remaining_liters()
                self.refresh_statistics() # Refresh stats after adding sale
            else:
                messagebox.showerror("数据库错误", "无法添加销售记录，数据库连接丢失")
                return

        except ValueError as e:
            messagebox.showerror("错误", f"请输入有效的数值: {e}")
        except sqlite3.Error as e:
            messagebox.showerror("数据库错误", f"添加销售记录时出错: {e}")


    def create_input_fields(self, parent):
        frame = ttk.LabelFrame(parent, text="新入库记录")
        frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        frame.columnconfigure(1, weight=1) # Allow entries to expand

        # Entry Date
        ttk.Label(frame, text="入库日期:").grid(row=0, column=0, padx=5, pady=2, sticky="e")
        self.entry_date = ttk.Entry(frame)
        self.entry_date.insert(0, datetime.now().strftime("%Y-%m-%d"))
        self.entry_date.grid(row=0, column=1, padx=5, pady=2, sticky="ew")

        # Order Number
        ttk.Label(frame, text="单号:").grid(row=1, column=0, padx=5, pady=2, sticky="e")
        self.order_number = ttk.Entry(frame)
        self.order_number.grid(row=1, column=1, padx=5, pady=2, sticky="ew")

        # Price (Ton/Yuan)
        ttk.Label(frame, text="单价（吨/元）:").grid(row=2, column=0, padx=5, pady=2, sticky="e")
        self.price_per_ton = ttk.Entry(frame)
        self.price_per_ton.grid(row=2, column=1, padx=5, pady=2, sticky="ew")

        # Quantity (Ton)
        ttk.Label(frame, text="数量（吨）:").grid(row=3, column=0, padx=5, pady=2, sticky="e")
        self.quantity_ton = ttk.Entry(frame)
        self.quantity_ton.grid(row=3, column=1, padx=5, pady=2, sticky="ew")

        # Density (Ton/Cubic Meter)
        ttk.Label(frame, text="密度（吨/立方米）:").grid(row=4, column=0, padx=5, pady=2, sticky="e")
        self.density = ttk.Entry(frame)
        self.density.grid(row=4, column=1, padx=5, pady=2, sticky="ew")

        # Add Record Button
        ttk.Button(frame, text="添加入库记录", command=self.add_record).grid(row=5, column=0, columnspan=2, pady=10)

        # Bind Enter key for inventory fields
        inventory_entries = [
            self.entry_date, self.order_number, self.price_per_ton,
            self.quantity_ton, self.density
        ]
        for entry in inventory_entries:
            entry.bind("<Return>", lambda e: self.add_record())
            entry.bind("<KP_Enter>", lambda e: self.add_record()) # Numpad Enter


    def create_inventory_table(self, parent):
        # Grid row changed to 2 to place it below buttons and allow expansion
        frame = ttk.LabelFrame(parent, text="库存记录")
        frame.grid(row=2, column=0, padx=10, pady=10, sticky="nsew")
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)

        # Changed columns to include display_id first
        columns = ("display_id", "entry_date", "order_number", "price_per_ton",
                  "quantity_ton", "density", "total_liters")
        self.tree = ttk.Treeview(frame, columns=columns, show="headings", selectmode="browse")

        # Set column widths and headings
        self.tree.heading("display_id", text="序号") # Changed heading
        self.tree.column("display_id", width=40, stretch=False, anchor="center") # Changed column name
        self.tree.heading("entry_date", text="入库日期")
        self.tree.column("entry_date", width=100, anchor="center")
        self.tree.heading("order_number", text="单号")
        self.tree.column("order_number", width=120)
        self.tree.heading("price_per_ton", text="单价(吨/元)")
        self.tree.column("price_per_ton", width=100, anchor="e")
        self.tree.heading("quantity_ton", text="数量(吨)")
        self.tree.column("quantity_ton", width=100, anchor="e")
        self.tree.heading("density", text="密度")
        self.tree.column("density", width=80, anchor="e")
        self.tree.heading("total_liters", text="总升数")
        self.tree.column("total_liters", width=100, anchor="e")

        self.tree.grid(row=0, column=0, sticky="nsew")

        # Add scrollbar
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.grid(row=0, column=1, sticky="ns")

    def add_record(self, event=None):
        entry_date_str = self.entry_date.get().strip()
        order_num = self.order_number.get().strip()
        price_str = self.price_per_ton.get().strip()
        quantity_str = self.quantity_ton.get().strip()
        density_str = self.density.get().strip()

        # Basic validation
        if not all([entry_date_str, order_num, price_str, quantity_str, density_str]):
            messagebox.showerror("输入错误", "所有字段均为必填项")
            return

        try:
            # More specific validation
            try:
                datetime.strptime(entry_date_str, "%Y-%m-%d")
            except ValueError:
                messagebox.showerror("输入错误", "日期格式无效，请使用 YYYY-MM-DD")
                return

            price_val = float(price_str)
            quantity_val = float(quantity_str)
            density_val = float(density_str)

            if price_val <= 0: raise ValueError("单价必须大于0")
            if quantity_val <= 0: raise ValueError("数量必须大于0")
            if not (0.7 <= density_val <= 1.3): # Example density range for diesel
                 raise ValueError("密度应在 0.7 到 1.3 之间")

            # Check for duplicate order number
            if self.conn: # Add check
                with self.conn:
                    cursor = self.conn.cursor()
                    cursor.execute("SELECT id FROM inventory WHERE order_number=?", (order_num,))
                    if cursor.fetchone():
                        messagebox.showerror("输入错误", f"入库单号 '{order_num}' 已存在")
                        return

                    # Calculate total liters
                    total_liters = self.calculate_liters(quantity_val, density_val)

                    # Insert into database
                    cursor.execute('''
                        INSERT INTO inventory (entry_date, order_number, price_per_ton, quantity_ton, density, total_liters)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (entry_date_str, order_num, price_val, quantity_val, density_val, total_liters))

                # Clear fields and refresh if successful
                self.order_number.delete(0, tk.END)
                self.price_per_ton.delete(0, tk.END)
                self.quantity_ton.delete(0, tk.END)
                self.density.delete(0, tk.END)
                self.order_number.focus_set() # Focus next logical field

                self.refresh_table() # This now handles auto-scroll and renumbering
                self.update_remaining_liters()
                self.refresh_statistics() # Refresh stats after adding inventory
                # Removed success messagebox

            else:
                messagebox.showerror("数据库错误", "无法添加入库记录，数据库连接丢失")
                return

        except ValueError as e:
            messagebox.showerror("输入错误", f"输入无效: {e}")
        except sqlite3.Error as e:
            messagebox.showerror("数据库错误", f"添加入库记录时出错: {e}")


    def edit_record(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("警告", "请先选择要编辑的记录")
            return

        # Use item iid (which we set to the database ID)
        db_id = selected[0]
        # Fetch current display values directly from tree using iid
        item_values = self.tree.item(db_id, 'values')
        display_id, entry_date, order_num, price_ton, qty_ton, density, total_liters = item_values

        edit_dialog = tk.Toplevel(self.root)
        edit_dialog.title(f"编辑入库记录 (序号: {display_id})") # Show display ID
        edit_dialog.transient(self.root)
        edit_dialog.grab_set()

        dialog_frame = ttk.Frame(edit_dialog, padding="10")
        dialog_frame.pack(fill="both", expand=True)

        # Use fetched display values
        fields = [
            ("入库日期", entry_date),
            ("单号", order_num),
            ("单价（吨/元）", price_ton),
            ("数量（吨）", qty_ton),
            ("密度", density)
        ]

        entries = {}
        for i, (label, value) in enumerate(fields):
            ttk.Label(dialog_frame, text=label).grid(row=i, column=0, padx=5, pady=2, sticky="e")
            entry = ttk.Entry(dialog_frame, width=25)
            entry.insert(0, str(value))
            entry.grid(row=i, column=1, padx=5, pady=2, sticky="w")
            entries[label] = entry # Use label as key

        def save_changes():
            try:
                new_date = entries["入库日期"].get().strip()
                new_order = entries["单号"].get().strip()
                new_price_str = entries["单价（吨/元）"].get().strip()
                new_quantity_str = entries["数量（吨）"].get().strip()
                new_density_str = entries["密度"].get().strip()

                if not all([new_date, new_order, new_price_str, new_quantity_str, new_density_str]):
                    raise ValueError("所有字段都不能为空")

                try:
                    datetime.strptime(new_date, "%Y-%m-%d")
                except ValueError:
                    raise ValueError("日期格式无效，请使用 YYYY-MM-DD")

                new_price = float(new_price_str)
                new_quantity = float(new_quantity_str)
                new_density = float(new_density_str)

                if new_price <= 0: raise ValueError("单价必须大于0")
                if new_quantity <= 0: raise ValueError("数量必须大于0")
                if not (0.7 <= new_density <= 1.3): raise ValueError("密度应在 0.7 到 1.3 之间")

                new_total_liters = self.calculate_liters(new_quantity, new_density)

                if self.conn: # Add check
                    with self.conn:
                        cursor = self.conn.cursor()
                        # Check for duplicate order number (excluding current record, using db_id)
                        cursor.execute("SELECT id FROM inventory WHERE order_number = ? AND id != ?", (new_order, db_id))
                        if cursor.fetchone():
                            messagebox.showerror("错误", f"入库单号 '{new_order}' 已存在", parent=edit_dialog)
                            return

                        cursor.execute('''
                            UPDATE inventory SET
                                entry_date = ?,
                                order_number = ?,
                                price_per_ton = ?,
                                quantity_ton = ?,
                                density = ?,
                                total_liters = ?
                            WHERE id = ?
                        ''', (new_date, new_order, new_price, new_quantity, new_density, new_total_liters, db_id)) # Use db_id here

                    edit_dialog.destroy()
                    self.refresh_table() # Refresh to show changes and renumber
                    self.update_remaining_liters()
                    self.refresh_statistics() # Refresh stats after editing inventory
                    # Removed success messagebox for edit as well
                else:
                    messagebox.showerror("数据库错误", "无法更新记录，数据库连接丢失", parent=edit_dialog)

            except ValueError as e:
                messagebox.showerror("输入错误", f"输入无效: {e}", parent=edit_dialog)
            except sqlite3.Error as e:
                 messagebox.showerror("数据库错误", f"无法更新入库记录: {e}", parent=edit_dialog)

        save_button = ttk.Button(dialog_frame, text="保存更改", command=save_changes)
        save_button.grid(row=len(fields), column=0, columnspan=2, pady=10)

        entries["入库日期"].focus()
        self.root.wait_window(edit_dialog)


    def delete_record(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("警告", "请先选择要删除的入库记录")
            return

        # Use item iid (which is the database ID)
        db_id = selected[0]
        # Get display values for confirmation
        item_values = self.tree.item(db_id, 'values')
        display_id = item_values[0] # Display ID is first

        if messagebox.askyesno("确认删除", f"确定要删除入库记录 (序号: {display_id}) 吗？\n注意：这不会自动调整相关销售记录。"):
            if self.conn: # Add check
                try:
                    with self.conn:
                        cursor = self.conn.cursor()
                        # Delete using the actual database ID (db_id)
                        cursor.execute("DELETE FROM inventory WHERE id = ?", (db_id,))
                    self.refresh_table() # Refresh to renumber display IDs
                    self.update_remaining_liters()
                    self.refresh_statistics() # Refresh stats after deleting inventory
                except sqlite3.Error as e:
                    messagebox.showerror("数据库错误", f"删除入库记录时出错: {e}")
            else:
                messagebox.showerror("数据库错误", "无法删除记录，数据库连接丢失")
                return

    def refresh_table(self):
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Reload from database
        last_inserted_iid = None
        if self.conn: # Add check
            try:
                with self.conn:
                    cursor = self.conn.cursor()
                    # Order by id ASC for sequential display ID
                    cursor.execute("SELECT id, entry_date, order_number, price_per_ton, quantity_ton, density, total_liters FROM inventory ORDER BY id ASC")
                    rows = cursor.fetchall()
                    # Use enumerate to generate display ID (starts from 1)
                    for display_id, row in enumerate(rows, start=1):
                        db_id, entry_date, order_num, price, qty, density_val, total_liters = row
                        # Initialize list with string representation of display_id
                        formatted_row = [str(display_id)]
                        formatted_row.append(str(entry_date))
                        formatted_row.append(str(order_num))
                        # Format numbers for display (already strings)
                        formatted_row.append(f"{price:.2f}" if price is not None else "0.00")
                        formatted_row.append(f"{qty:.2f}" if qty is not None else "0.00")
                        formatted_row.append(f"{density_val:.3f}" if density_val is not None else "0.000")
                        formatted_row.append(f"{total_liters:.2f}" if total_liters is not None else "0.00")

                        # Use database ID as item ID (iid)
                        item_iid = str(db_id)
                        self.tree.insert("", "end", iid=item_iid, values=tuple(formatted_row))
                        last_inserted_iid = item_iid # Keep track of the last one

                    # --- Auto-scroll Inventory Table to Bottom ---
                    if last_inserted_iid:
                        try:
                            self.tree.selection_set(last_inserted_iid)
                            self.tree.see(last_inserted_iid)
                        except Exception as e:
                            print(f"Error auto-scrolling inventory table: {e}")
                    # --- End Auto-scroll ---

            except sqlite3.Error as e:
                messagebox.showerror("数据库错误", f"无法加载库存列表: {e}")
        else:
            messagebox.showerror("数据库错误", "无法加载库存列表，数据库连接丢失")


    def calculate_liters(self, quantity_ton, density):
        if density == 0:
            messagebox.showerror("计算错误", "密度不能为零")
            return 0
        return (quantity_ton / density) * 1000

    def update_remaining_liters(self):
        remaining_liters = self.calculate_remaining_liters()
        self.remaining_liters_label.config(text=f"剩余升数: {remaining_liters:.2f}")

    def calculate_remaining_liters(self):
        total_in = 0
        total_out = 0
        if self.conn: # Add check
            try:
                with self.conn:
                    cursor = self.conn.cursor()
                    cursor.execute("SELECT SUM(total_liters) FROM inventory")
                    result_in = cursor.fetchone()
                    if result_in and result_in[0] is not None:
                        total_in = result_in[0]

                    cursor.execute("SELECT SUM(quantity_liter) FROM sales")
                    result_out = cursor.fetchone()
                    if result_out and result_out[0] is not None:
                        total_out = result_out[0]
                return total_in - total_out
            except sqlite3.Error as e:
                messagebox.showerror("数据库错误", f"计算剩余升数时出错: {e}")
                return 0
        else:
            # Avoid showing error on initial load if connection is the issue
            # messagebox.showerror("数据库错误", "无法计算剩余升数，数据库连接丢失")
            print("无法计算剩余升数，数据库连接丢失")
            return 0

    selected_customer_id = None

if __name__ == "__main__":
    os.chdir(APP_DIR)
    root = tk.Tk()
    style = ttk.Style(root)
    tcl_version = tuple(int(part) for part in root.tk.call('info', 'patchlevel').split('.')[:2])
    if tcl_version < (8, 6):
        print(
            "警告: 当前 Python 的 Tcl/Tk 版本过旧，界面可能显示异常。"
            " 建议使用项目虚拟环境运行: .venv/bin/python main.py",
            file=sys.stderr,
        )
    for theme in ('aqua', 'clam', 'default'):
        try:
            style.theme_use(theme)
            break
        except tk.TclError:
            continue

    app = DieselInventoryApp(root)
    root.update_idletasks()
    root.mainloop()
