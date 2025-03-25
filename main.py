import sys
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                           QHBoxLayout, QTabWidget, QPushButton, QLabel, 
                           QLineEdit, QTableWidget, QTableWidgetItem, QMessageBox,
                           QFileDialog, QComboBox, QSpinBox, QDoubleSpinBox, QDateEdit, QHeaderView, QGridLayout)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QIcon  # 添加QIcon导入
from database import Database
from PySide6.QtCore import QDateTime
from PySide6.QtWidgets import QGridLayout, QGroupBox
import pandas as pd
from datetime import datetime
import sqlite3

class DieselSalesSystem(QMainWindow):
    def create_statistics_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)

        # 日期筛选
        date_layout = QHBoxLayout()
        date_layout.addWidget(QLabel('统计区间:'))
        
        self.start_date = QDateEdit()
        self.start_date.setDate(QDate.currentDate().addMonths(-1))
        self.start_date.setCalendarPopup(True)
        date_layout.addWidget(self.start_date)
        
        date_layout.addWidget(QLabel('至'))
        
        self.end_date = QDateEdit()
        self.end_date.setDate(QDate.currentDate())
        self.end_date.setCalendarPopup(True)
        date_layout.addWidget(self.end_date)
        
        refresh_btn = QPushButton('刷新统计')
        refresh_btn.clicked.connect(self.refresh_statistics)
        date_layout.addWidget(refresh_btn)
        layout.addLayout(date_layout)

        # 客户统计表格
        self.stat_table = QTableWidget()
        self.stat_table.setColumnCount(4)
        self.stat_table.setHorizontalHeaderLabels(['客户名称', '加油次数', '总数量(升)', '总金额(元)'])
        self.stat_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.stat_table)

        # 全局汇总
        total_group = QGroupBox('全局统计')
        total_layout = QGridLayout()
        
        self.total_count = QLabel('0次')
        self.total_quantity = QLabel('0升')
        self.total_amount = QLabel('0元')
        
        total_layout.addWidget(QLabel('总加油次数:'), 0, 0)
        total_layout.addWidget(self.total_count, 0, 1)
        total_layout.addWidget(QLabel('总销售量(升):'), 1, 0)
        total_layout.addWidget(self.total_quantity, 1, 1)
        total_layout.addWidget(QLabel('总销售额:'), 2, 0)
        total_layout.addWidget(self.total_amount, 2, 1)
        
        total_group.setLayout(total_layout)
        layout.addWidget(total_group)
        
        # 初始化数据
        self.refresh_statistics()
        return widget

    def refresh_statistics(self):
        start = self.start_date.date().toString('yyyy-MM-dd')
        end = self.end_date.date().toString('yyyy-MM-dd')
        
        # 客户统计
        customer_stats = self.db.get_customer_statistics(start, end)
        self.stat_table.setRowCount(len(customer_stats))
        
        for row, stats in enumerate(customer_stats.itertuples(index=False)):
            name, count, quantity, amount = stats[0], stats[1], stats[2], stats[3]
            self.stat_table.setItem(row, 0, QTableWidgetItem(name))
            self.stat_table.setItem(row, 1, QTableWidgetItem(str(count)))
            self.stat_table.setItem(row, 2, QTableWidgetItem(f'{quantity:.2f}'))
            self.stat_table.setItem(row, 3, QTableWidgetItem(f'{amount:.2f}'))
        
        # 全局统计
        total = self.db.get_total_statistics(start, end)
        self.total_count.setText(f'{total.iloc[0]}次')
        self.total_quantity.setText(f'{total.iloc[1]:.2f}升')
        self.total_amount.setText(f'{total.iloc[2]:.2f}元')
    def __init__(self):
        super().__init__()
        self.db = Database()
        self.customer_search_history = []  # 初始化客户搜索历史记录
        self.init_ui()
        # 禁用自动选择
        self.customer_search.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)

    def init_ui(self):
        self.setWindowTitle('柴油销售管理系统')
        self.setGeometry(100, 100, 1920, 1080)  # 修改为1920*1080的分辨率
        self.setMinimumSize(1280, 720)  # 设置最小窗口尺寸
        
        # 设置应用程序图标为加油枪
        self.setWindowIcon(QIcon("fuel_pump_icon.png"))  # 确保图标文件在应用程序目录中

        # 创建中心部件和主布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(20, 20, 20, 20)  # 设置边距，使界面更加美观
        layout.setSpacing(15)  # 增加组件之间的间距

        # 创建标签页
        tabs = QTabWidget()
        tabs.setStyleSheet("""
            QTabBar::tab { 
                height: 30px; 
                min-width: 120px; 
                font-size: 14px;
                color: #000000;  /* 确保标签页文字为黑色 */
            }
            QTabBar::tab:selected { 
                font-weight: bold;
                background-color: #4a86e8; 
                color: white;
            }
        """)
        layout.addWidget(tabs)

        # 添加各个功能标签页
        tabs.addTab(self.create_tank_tab(), '油罐管理')
        tabs.addTab(self.create_inventory_tab(), '入库管理')
        tabs.addTab(self.create_sales_tab(), '销售管理')
        tabs.addTab(self.create_customer_tab(), '客户管理')
        tabs.addTab(self.create_statistics_tab(), '数据统计')

        # 添加工具栏按钮 - 改为水平布局在顶部
        toolbar = QHBoxLayout()
        toolbar.setSpacing(10)  # 按钮之间的间距
        
        # 定义工具栏按钮样式
        button_style = """
        QPushButton {
            background-color: rgba(240, 240, 240, 0.9);
            color: #333333;
            border: 1px solid #dcdcdc;
            border-radius: 5px;
            padding: 8px 16px;
            font-size: 14px;
            min-width: 120px;
            color: #000000;  /* 确保按钮文字为黑色 */
        }
        QPushButton:hover {
            background-color: #e0e0e0;
        }
        QPushButton:pressed {
            background-color: #d0d0d0;
        }
        """
        
        new_file_btn = QPushButton('新建文件')
        new_file_btn.setStyleSheet(button_style)
        new_file_btn.clicked.connect(self.new_file)
        toolbar.addWidget(new_file_btn)

        open_file_btn = QPushButton('打开文件')
        open_file_btn.setStyleSheet(button_style)
        open_file_btn.clicked.connect(self.open_file)
        toolbar.addWidget(open_file_btn)

        save_as_btn = QPushButton('另存为')
        save_as_btn.setStyleSheet(button_style)
        save_as_btn.clicked.connect(self.save_file_as)
        toolbar.addWidget(save_as_btn)

        export_btn = QPushButton('导出Excel')
        export_btn.setStyleSheet(button_style)
        export_btn.clicked.connect(self.export_to_excel)
        toolbar.addWidget(export_btn)

        # 添加弹性空间
        toolbar.addStretch()
        
        reset_btn = QPushButton('初始化')
        reset_btn.setStyleSheet(button_style)
        reset_btn.clicked.connect(self.reset_database)
        toolbar.addWidget(reset_btn)

        # 将工具栏添加到主布局
        layout.insertLayout(0, toolbar)

        # 添加状态栏
        self.statusBar().setStyleSheet("QStatusBar{font-size: 14px; padding: 5px;}")
        self.statusBar().showMessage('系统准备就绪')

        # 设置全局样式
        self.setStyleSheet("""
            QMainWindow {
                background-color: rgba(240, 240, 240, 0.9);
            color: #333333;
            }
            QWidget {
                background-color: rgba(240, 240, 240, 0.9);
            color: #333333;
            }
            QTabWidget::pane {
                border: 1px solid #c0c0c0;
                background-color: #f8f8f8;
            }
            QLabel {
                color: #000000;
                font-size: 14px;
                font-weight: normal;
            }
            QTableWidget {
                background-color: white;
                color: #000000;
                gridline-color: #d4d4d4;
                font-size: 13px;
            }
            QTableWidget::item {
                padding: 5px;
                border-bottom: 1px solid #eeeeee;
                color: #000000;
                text-align: center;  /* 添加文本居中属性 */
            }
            QHeaderView::section {
                background-color: #e0e0e0;
                color: #000000;
                font-weight: bold;
                padding: 8px;
                border: none;
                border-right: 1px solid #d4d4d4;
                border-bottom: 1px solid #d4d4d4;
                text-align: center;  /* 添加表头文本居中属性 */
            }
            QPushButton {
                min-width: 80px;
                padding: 8px 15px;
                font-size: 14px;
                color: #000000;
                background-color: #e0e0e0;
                border: 1px solid #c0c0c0;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #d0d0d0;
            }
            QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QDateEdit {
                background-color: white;
                color: #000000;
                border: 1px solid #c0c0c0;
                padding: 8px;
                min-height: 20px;
                selection-background-color: #308cc6;
                selection-color: white;
            }
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: center right;
                width: 20px;
                border-left: 1px solid #c0c0c0;
            }
            QComboBox::down-arrow {
                width: 12px;
                height: 12px;
                background-color: #4a86e8;
            }
            QDateEdit::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: center right;
                width: 20px;
                border-left: 1px solid #c0c0c0;
            }
            QDateEdit::down-arrow {
                width: 12px;
                height: 12px;
                background-color: #4a86e8;
            }
            QPushButton {
                padding: 2px 6px;
                min-height: 18px;
                max-height: 18px;
            }
        """)

        # 初始化搜索历史
        self.sales_search_history = []
        self.customer_search_history = []

    def create_tank_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(15, 15, 15, 15)  # 设置边距
        layout.setSpacing(15)  # 组件间距

        # 添加油罐表单
        form_layout = QHBoxLayout()
        form_layout.setSpacing(10)
        
        # 设置输入框样式
        input_style = """
        QLineEdit, QDoubleSpinBox {
            padding: 8px;
            border: 1px solid #dcdcdc;
            border-radius: 4px;
            min-width: 150px;
            font-size: 14px;
        }
        QLabel {
            font-size: 14px;
        }
        """
        
        self.tank_name = QLineEdit()
        self.tank_name.setPlaceholderText('油罐名称')
        self.tank_name.setStyleSheet(input_style)
        
        self.tank_capacity = QDoubleSpinBox()
        self.tank_capacity.setRange(0, 1000000)
        self.tank_capacity.setSuffix(' 升')
        self.tank_capacity.setStyleSheet(input_style)
        
        add_tank_btn = QPushButton('添加油罐')
        add_tank_btn.setStyleSheet("""
        QPushButton {
            background-color: #4CAF50;
            color: white;
            border: none;
            border-radius: 4px;
            padding: 8px 16px;
            font-size: 14px;
            min-width: 100px;
        }
        QPushButton:hover {
            background-color: #45a049;
        }
        QPushButton:pressed {
            background-color: #3d8b40;
        }
        """)
        add_tank_btn.clicked.connect(self.add_tank)
        
        name_label = QLabel('油罐名称:')
        name_label.setStyleSheet("font-size: 14px;")
        form_layout.addWidget(name_label)
        form_layout.addWidget(self.tank_name)
        
        capacity_label = QLabel('最大容量:')
        capacity_label.setStyleSheet("font-size: 14px;")
        form_layout.addWidget(capacity_label)
        form_layout.addWidget(self.tank_capacity)
        
        form_layout.addWidget(add_tank_btn)
        form_layout.addStretch(1)  # 添加弹性空间
        layout.addLayout(form_layout)

        # 油罐列表 - 添加表格样式
        table_style = """
        QTableWidget {
            border: 1px solid #dcdcdc;
            border-radius: 5px;
            font-size: 14px;
        }
        QTableWidget::item {
            padding: 5px;
        }
        QHeaderView::section {
            background-color: rgba(240, 240, 240, 0.9);
            color: #333333;
            padding: 8px;
            font-size: 14px;
            font-weight: bold;
            border: none;
            border-right: 1px solid #dcdcdc;
            border-bottom: 1px solid #dcdcdc;
        }
        """
        
        self.tank_table = QTableWidget()
        self.tank_table.setColumnCount(5)
        self.tank_table.setHorizontalHeaderLabels(['ID', '名称', '最大容量', '当前油量', '剩余容量'])
        self.tank_table.setStyleSheet(table_style)
        # 修改为可调整列宽
        self.tank_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.tank_table.horizontalHeader().setStretchLastSection(True)  # 最后一列拉伸
        self.tank_table.verticalHeader().setVisible(False)  # 隐藏垂直表头
        self.tank_table.setAlternatingRowColors(True)  # 表格行交替颜色
        self.tank_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)  # 表格内容不可编辑
        layout.addWidget(self.tank_table)
        self.refresh_tank_table()

        # 添加回车键事件处理
        self.tank_name.returnPressed.connect(self.add_tank)
        self.tank_capacity.editingFinished.connect(self.add_tank)

        return widget

    def create_inventory_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)

        # 入库表单
        form_layout = QHBoxLayout()
        form_layout.setSpacing(10)
        
        # 设置输入框样式
        input_style = """
        QLineEdit, QDoubleSpinBox, QComboBox {
            padding: 8px;
            border: 1px solid #dcdcdc;
            border-radius: 4px;
            min-width: 120px;
            font-size: 14px;
        }
        QLabel {
            font-size: 14px;
        }
        """
        
        self.inventory_tank = QComboBox()
        self.inventory_tank.setStyleSheet(input_style)
        self.refresh_tank_combo()
        
        self.inventory_date = QLineEdit()
        self.inventory_date.setStyleSheet(input_style)
        self.inventory_date.setText(datetime.now().strftime('%Y-%m-%d'))
        self.inventory_date.returnPressed.connect(self.add_inventory_record)
        
        self.inventory_batch = QLineEdit()
        self.inventory_batch.setStyleSheet(input_style)
        self.inventory_batch.returnPressed.connect(self.add_inventory_record)
        
        self.inventory_price = QDoubleSpinBox()
        self.inventory_price.setStyleSheet(input_style)
        self.inventory_price.setRange(0, 10000)
        self.inventory_price.setSuffix(' 元/吨')
        self.inventory_price.editingFinished.connect(self.add_inventory_record)
        
        self.inventory_quantity = QDoubleSpinBox()
        self.inventory_quantity.setStyleSheet(input_style)
        self.inventory_quantity.setRange(0, 1000000)
        self.inventory_quantity.setSuffix(' 吨')
        self.inventory_quantity.editingFinished.connect(self.add_inventory_record)
        
        self.inventory_density = QDoubleSpinBox()
        self.inventory_density.setStyleSheet(input_style)
        self.inventory_density.setRange(0, 1)
        self.inventory_density.setSingleStep(0.001)
        self.inventory_density.setDecimals(4)
        self.inventory_density.editingFinished.connect(self.add_inventory_record)
        
        add_inventory_btn = QPushButton('添加入库记录')
        add_inventory_btn.setStyleSheet("""
        QPushButton {
            background-color: #4CAF50;
            color: white;
            border: none;
            border-radius: 4px;
            padding: 8px 16px;
            font-size: 14px;
            min-width: 100px;
        }
        QPushButton:hover {
            background-color: #45a049;
        }
        QPushButton:pressed {
            background-color: #3d8b40;
        }
        """)
        add_inventory_btn.clicked.connect(self.add_inventory_record)

        form_layout.addWidget(QLabel('油罐:'))
        form_layout.addWidget(self.inventory_tank)
        form_layout.addWidget(QLabel('日期:'))
        form_layout.addWidget(self.inventory_date)
        form_layout.addWidget(QLabel('单号:'))
        form_layout.addWidget(self.inventory_batch)
        form_layout.addWidget(QLabel('单价:'))
        form_layout.addWidget(self.inventory_price)
        form_layout.addWidget(QLabel('数量:'))
        form_layout.addWidget(self.inventory_quantity)
        form_layout.addWidget(QLabel('密度:'))
        form_layout.addWidget(self.inventory_density)
        form_layout.addWidget(add_inventory_btn)
        layout.addLayout(form_layout)

        # 入库记录列表 - 添加表格样式
        table_style = """
        QTableWidget {
            border: 1px solid #dcdcdc;
            border-radius: 5px;
            font-size: 14px;
        }
        QTableWidget::item {
            padding: 5px;
        }
        QHeaderView::section {
            background-color: rgba(240, 240, 240, 0.9);
            color: #333333;
            padding: 8px;
            font-size: 14px;
            font-weight: bold;
            border: none;
            border-right: 1px solid #dcdcdc;
            border-bottom: 1px solid #dcdcdc;
        }
        """
        
        self.inventory_table = QTableWidget()
        self.inventory_table.setColumnCount(9)  # 增加一列用于显示总价
        self.inventory_table.setHorizontalHeaderLabels(['ID', '油罐', '日期', '单号', '单价', '数量', '密度', '总价', '操作'])
        self.inventory_table.setStyleSheet(table_style)
        # 修改为可调整列宽
        self.inventory_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.inventory_table.horizontalHeader().setStretchLastSection(True)  # 最后一列拉伸
        self.inventory_table.verticalHeader().setVisible(False)  # 隐藏垂直表头
        self.inventory_table.setAlternatingRowColors(True)  # 表格行交替颜色
        self.inventory_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)  # 表格内容不可编辑
        layout.addWidget(self.inventory_table)
        self.refresh_inventory_table()

        return widget

    def create_sales_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)

        # 销售表单
        form_layout = QVBoxLayout()  # 改为垂直布局以便添加水平布局
        form_layout.setSpacing(15)
        
        # 设置输入框样式
        input_style = """
        QLineEdit, QDoubleSpinBox, QComboBox {
            padding: 8px;
            border: 1px solid #b0b0b0;
            border-radius: 4px;
            min-width: 120px;
            font-size: 14px;
            color: #000000;
            background-color: white;
        }
        QLabel {
            font-size: 14px;
            color: #000000;
        }
        """
        
        # 客户搜索和选择放在同一行
        customer_layout = QHBoxLayout()
        customer_layout.setSpacing(10)
        
        # 搜索部分
        customer_search_label = QLabel('客户搜索:')
        customer_search_label.setStyleSheet("font-size: 14px; min-width: 80px;")
        customer_layout.addWidget(customer_search_label)
        
        self.sales_customer_search = QComboBox()
        self.sales_customer_search.setStyleSheet(input_style)
        self.sales_customer_search.setEditable(True)
        self.sales_customer_search.setPlaceholderText('输入关键字搜索')
        self.sales_customer_search.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.sales_customer_search.editTextChanged.connect(self.filter_sales_customer_combo)
        self.sales_customer_search.setMinimumWidth(180)
        self.sales_customer_search.activated.connect(self.add_sales_search_history)
        customer_layout.addWidget(self.sales_customer_search)
        
        # 选择部分
        customer_select_label = QLabel('选择客户:')
        customer_select_label.setStyleSheet("font-size: 14px; min-width: 80px;")
        customer_layout.addWidget(customer_select_label)
        
        self.sales_customer = QComboBox()
        self.sales_customer.setStyleSheet(input_style)
        self.sales_customer.setMinimumWidth(180)
        customer_layout.addWidget(self.sales_customer)
        
        # 添加弹性空间
        customer_layout.addStretch(1)
        
        # 添加单价设置到客户选择同一行
        price_label = QLabel('单价设置:')
        price_label.setStyleSheet("font-size: 14px; min-width: 80px;")
        customer_layout.addWidget(price_label)
        
        self.sales_price = QDoubleSpinBox()
        self.sales_price.setStyleSheet(input_style)
        self.sales_price.setRange(0, 10000)
        self.sales_price.setSuffix(' 元/升')
        self.sales_price.setMinimumWidth(120)
        customer_layout.addWidget(self.sales_price)
        
        # 将客户搜索和选择布局添加到主表单
        form_layout.addLayout(customer_layout)
        
        # 刷新客户下拉框
        self.refresh_customer_combo()
        
        # 销售信息输入框
        sales_info_layout = QHBoxLayout()
        sales_info_layout.setSpacing(10)
        
        date_label = QLabel('日期:')
        date_label.setStyleSheet("font-size: 14px;")
        sales_info_layout.addWidget(date_label)
        
        self.sales_date = QLineEdit()
        self.sales_date.setStyleSheet(input_style)
        self.sales_date.setText(datetime.now().strftime('%Y-%m-%d'))
        self.sales_date.returnPressed.connect(self.add_sales_record)
        sales_info_layout.addWidget(self.sales_date)
        
        invoice_label = QLabel('单号:')
        invoice_label.setStyleSheet("font-size: 14px;")
        sales_info_layout.addWidget(invoice_label)
        
        self.sales_invoice = QLineEdit()
        self.sales_invoice.setStyleSheet(input_style)
        self.sales_invoice.returnPressed.connect(self.add_sales_record)
        sales_info_layout.addWidget(self.sales_invoice)
        
        quantity_label = QLabel('数量:')
        quantity_label.setStyleSheet("font-size: 14px;")
        sales_info_layout.addWidget(quantity_label)
        
        self.sales_quantity = QDoubleSpinBox()
        self.sales_quantity.setStyleSheet(input_style)
        self.sales_quantity.setRange(0, 1000000)
        self.sales_quantity.setSuffix(' 升')
        self.sales_quantity.editingFinished.connect(self.add_sales_record)
        sales_info_layout.addWidget(self.sales_quantity)
        
        # 添加销售记录按钮
        add_sales_btn = QPushButton('添加销售记录')
        add_sales_btn.setStyleSheet("""
        QPushButton {
            background-color: #2ecc71;
            color: white;
            border: none;
            border-radius: 4px;
            padding: 8px 16px;
            font-size: 14px;
            font-weight: bold;
            min-width: 120px;
        }
        QPushButton:hover {
            background-color: #27ae60;
        }
        """)
        add_sales_btn.clicked.connect(self.add_sales_record)
        sales_info_layout.addWidget(add_sales_btn)
        
        # 添加销售信息布局到主表单
        form_layout.addLayout(sales_info_layout)
        
        # 将表单添加到主布局
        layout.addLayout(form_layout)

        # 销售记录列表 - 添加表格样式
        table_style = """
        QTableWidget {
            border: 1px solid #c0c0c0;
            border-radius: 5px;
            font-size: 14px;
            color: #000000;
            background-color: white;
        }
        QTableWidget::item {
            padding: 5px;
            border-bottom: 1px solid #e0e0e0;
        }
        QHeaderView::section {
            background-color: #e0e0e0;
            color: #000000;
            padding: 8px;
            font-size: 14px;
            font-weight: bold;
            border: none;
            border-right: 1px solid #c0c0c0;
            border-bottom: 1px solid #c0c0c0;
        }
        """
        
        self.sales_table = QTableWidget()
        self.sales_table.setColumnCount(8)
        self.sales_table.setHorizontalHeaderLabels(['ID', '客户', '日期', '单号', '单价', '数量', '总价', '操作'])
        self.sales_table.setStyleSheet(table_style)
        
        # 修改为可调整列宽
        self.sales_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        # 设置初始列宽
        self.sales_table.setColumnWidth(0, 50)  # ID列
        self.sales_table.setColumnWidth(1, 150)  # 客户列 - 限制宽度而不是自动拉伸
        self.sales_table.horizontalHeader().setStretchLastSection(True)  # 最后一列拉伸
        
        self.sales_table.verticalHeader().setVisible(False)
        self.sales_table.setAlternatingRowColors(True)
        self.sales_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.sales_table)
        self.refresh_sales_table()

        return widget

    def create_customer_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)
        
        # 设置输入框样式
        input_style = """
        QLineEdit, QDoubleSpinBox, QComboBox, QDateEdit {
            padding: 8px;
            border: 1px solid #dcdcdc;
            border-radius: 4px;
            min-width: 120px;
            font-size: 14px;
        }
        QLabel {
            font-size: 14px;
        }
        """

        # 添加客户部分
        form_layout = QHBoxLayout()
        form_layout.setSpacing(10)
        
        self.customer_name = QLineEdit()
        self.customer_name.setStyleSheet(input_style)
        self.customer_name.setPlaceholderText('客户名称')
        self.customer_name.returnPressed.connect(self.add_customer)
        
        add_customer_btn = QPushButton('添加客户')
        add_customer_btn.setStyleSheet("""
        QPushButton {
            background-color: #4CAF50;
            color: white;
            border: none;
            border-radius: 4px;
            padding: 8px 16px;
            font-size: 14px;
            min-width: 100px;
        }
        QPushButton:hover {
            background-color: #45a049;
        }
        QPushButton:pressed {
            background-color: #3d8b40;
        }
        """)
        add_customer_btn.clicked.connect(self.add_customer)
        
        customer_label = QLabel('客户名称:')
        customer_label.setStyleSheet("font-size: 14px;")
        customer_label.setFixedWidth(80)  # 固定标签宽度
        form_layout.addWidget(customer_label)
        form_layout.addWidget(self.customer_name)
        form_layout.addWidget(add_customer_btn)
        form_layout.addStretch(1)
        layout.addLayout(form_layout)
        
        # 客户列表 - 添加表格样式
        table_style = """
        QTableWidget {
            border: 1px solid #dcdcdc;
            border-radius: 5px;
            font-size: 14px;
        }
        QTableWidget::item {
            padding: 5px;
        }
        QHeaderView::section {
            background-color: rgba(240, 240, 240, 0.9);
            color: #333333;
            padding: 8px;
            font-size: 14px;
            font-weight: bold;
            border: none;
            border-right: 1px solid #dcdcdc;
            border-bottom: 1px solid #dcdcdc;
        }
        """
        
        self.customer_table = QTableWidget()
        self.customer_table.setColumnCount(3)
        self.customer_table.setHorizontalHeaderLabels(['ID', '客户名称', '操作'])
        self.customer_table.setStyleSheet(table_style)
        # 修改为可调整列宽
        self.customer_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.customer_table.horizontalHeader().setStretchLastSection(True)  # 最后一列拉伸
        self.customer_table.verticalHeader().setVisible(False)
        self.customer_table.setAlternatingRowColors(True)
        self.customer_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.customer_table)
        self.refresh_customer_table()

        # 客户数据查看部分 - 使用框架突出显示
        data_view_layout = QVBoxLayout()
        
        # 添加标题
        data_view_title = QLabel('客户数据查询')
        data_view_title.setStyleSheet("font-weight: bold; font-size: 16px; margin-top: 15px;")
        data_view_layout.addWidget(data_view_title)
        
        # 设置固定标签宽度，确保垂直对齐
        label_style = "font-size: 14px; min-width: 80px; max-width: 80px;"
        
        # 客户搜索部分 - 使用网格布局实现更精确的对齐
        search_grid = QGridLayout()
        search_grid.setSpacing(10)
        search_grid.setColumnMinimumWidth(0, 80)  # 第一列固定宽度
        search_grid.setColumnMinimumWidth(1, 150)  # 第二列固定宽度
        search_grid.setColumnMinimumWidth(2, 80)  # 第三列固定宽度
        search_grid.setColumnMinimumWidth(3, 150)  # 第四列固定宽度
        search_grid.setColumnStretch(5, 1)  # 最后一列弹性拉伸
        
        # 第一行：客户搜索和选择
        customer_search_label = QLabel('客户搜索:')
        customer_search_label.setStyleSheet(label_style)
        customer_search_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        search_grid.addWidget(customer_search_label, 0, 0)
        
        self.customer_search = QComboBox()
        self.customer_search.setStyleSheet(input_style)
        self.customer_search.setEditable(True)
        self.customer_search.setPlaceholderText('输入关键字搜索')
        self.customer_search.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.customer_search.editTextChanged.connect(self.filter_customer_combo)
        self.customer_search.setFixedWidth(150)
        self.customer_search.activated.connect(self.add_customer_search_history)
        search_grid.addWidget(self.customer_search, 0, 1)
        
        customer_select_label = QLabel('选择客户:')
        customer_select_label.setStyleSheet(label_style)
        customer_select_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        search_grid.addWidget(customer_select_label, 0, 2)
        
        self.customer_combo = QComboBox()
        self.customer_combo.setStyleSheet(input_style)
        self.customer_combo.setFixedWidth(150)
        search_grid.addWidget(self.customer_combo, 0, 3)
        
        # 第二行：日期选择
        date_start_label = QLabel('开始日期:')
        date_start_label.setStyleSheet(label_style)
        date_start_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        search_grid.addWidget(date_start_label, 1, 0)
        
        self.customer_start_date = QDateEdit()
        self.customer_start_date.setStyleSheet(input_style)
        self.customer_start_date.setCalendarPopup(True)
        self.customer_start_date.setDate(QDate.currentDate().addMonths(-1))
        self.customer_start_date.setFixedWidth(150)
        search_grid.addWidget(self.customer_start_date, 1, 1)
        
        date_end_label = QLabel('结束日期:')
        date_end_label.setStyleSheet(label_style)
        date_end_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        search_grid.addWidget(date_end_label, 1, 2)
        
        self.customer_end_date = QDateEdit()
        self.customer_end_date.setStyleSheet(input_style)
        self.customer_end_date.setCalendarPopup(True)
        self.customer_end_date.setDate(QDate.currentDate())
        self.customer_end_date.setFixedWidth(150)
        search_grid.addWidget(self.customer_end_date, 1, 3)
        
        # 查看按钮放在第二行的第5列
        view_customer_data_btn = QPushButton('查看客户数据')
        view_customer_data_btn.setStyleSheet("""
        QPushButton {
            background-color: #4CAF50;
            color: white;
            border: none;
            border-radius: 4px;
            padding: 8px 16px;
            font-size: 14px;
        }
        QPushButton:hover {
            background-color: #45a049;
        }
        QPushButton:pressed {
            background-color: #3d8b40;
        }
        """)
        view_customer_data_btn.clicked.connect(self.view_customer_data)
        view_customer_data_btn.setMinimumHeight(30)
        view_customer_data_btn.setFixedWidth(200)
        search_grid.addWidget(view_customer_data_btn, 1, 4)
        
        data_view_layout.addLayout(search_grid)
        self.refresh_customer_combo()
        
        layout.addLayout(data_view_layout)

        # 利润显示
        profit_layout = QVBoxLayout()
        
        # 添加标题
        profit_title = QLabel('利润分析')
        profit_title.setStyleSheet("font-weight: bold; font-size: 16px; margin-top: 15px;")
        profit_layout.addWidget(profit_title)
        
        # 使用网格布局实现更精确的对齐
        profit_grid = QGridLayout()
        profit_grid.setSpacing(10)
        profit_grid.setColumnMinimumWidth(0, 80)  # 第一列固定宽度
        profit_grid.setColumnMinimumWidth(1, 150)  # 第二列固定宽度
        profit_grid.setColumnMinimumWidth(2, 80)  # 第三列固定宽度
        profit_grid.setColumnMinimumWidth(3, 150)  # 第四列固定宽度
        profit_grid.setColumnStretch(5, 1)  # 最后一列弹性拉伸
        
        # 周期选择
        period_label = QLabel('利润周期:')
        period_label.setStyleSheet(label_style)
        period_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        profit_grid.addWidget(period_label, 0, 0)
        
        self.profit_start_date = QDateEdit()
        self.profit_start_date.setStyleSheet(input_style)
        self.profit_start_date.setCalendarPopup(True)
        self.profit_start_date.setDate(QDate.currentDate().addMonths(-1))
        self.profit_start_date.setFixedWidth(150)
        profit_grid.addWidget(self.profit_start_date, 0, 1)
        
        to_label = QLabel('至')
        to_label.setStyleSheet(label_style)
        to_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        profit_grid.addWidget(to_label, 0, 2)
        
        self.profit_end_date = QDateEdit()
        self.profit_end_date.setStyleSheet(input_style)
        self.profit_end_date.setCalendarPopup(True)
        self.profit_end_date.setDate(QDate.currentDate())
        self.profit_end_date.setFixedWidth(150)
        profit_grid.addWidget(self.profit_end_date, 0, 3)
        
        update_profit_btn = QPushButton('查看指定周期利润')
        update_profit_btn.setStyleSheet("""
        QPushButton {
            background-color: #2196F3;
            color: white;
            border: none;
            border-radius: 4px;
            padding: 8px 16px;
            font-size: 14px;
        }
        QPushButton:hover {
            background-color: #0b7dda;
        }
        QPushButton:pressed {
            background-color: #0a6fc2;
        }
        """)
        update_profit_btn.clicked.connect(self.update_profit_by_period)
        update_profit_btn.setFixedWidth(200)
        profit_grid.addWidget(update_profit_btn, 0, 4)
        
        profit_layout.addLayout(profit_grid)
        
        # 利润标签
        self.total_profit_label = QLabel('总利润: 0.00 元')
        self.total_profit_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #336699; margin-top: 10px;")
        self.monthly_profit_label = QLabel('月利润: 0.00 元')
        self.monthly_profit_label.setStyleSheet("font-size: 14px; color: #336699;")
        profit_layout.addWidget(self.total_profit_label)
        profit_layout.addWidget(self.monthly_profit_label)
        
        layout.addLayout(profit_layout)
        
        # 初始化显示最新利润
        self.update_profit_display()

        return widget

    def refresh_tank_table(self):
        tanks = self.db.get_tanks()
        self.tank_table.setRowCount(len(tanks))
        for i, row in tanks.iterrows():
            id_item = QTableWidgetItem(str(row['id']))
            id_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            # 将行索引转换为整数,并确保i是可转换为整数的类型
            row_index = int(float(i)) if isinstance(i, (int, float, str)) else 0
            self.tank_table.setItem(row_index, 0, id_item)
            
            name_item = QTableWidgetItem(str(row['name']))
            name_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            # 将行索引转换为整数,并确保i是可转换为整数的类型
            row_index = int(float(i)) if isinstance(i, (int, float, str)) else 0
            self.tank_table.setItem(row_index, 1, name_item)
            
            max_cap_item = QTableWidgetItem(f"{row['max_capacity']:.2f}")
            max_cap_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            # 将行索引转换为整数,并确保i是可转换为整数的类型
            row_index = int(float(i)) if isinstance(i, (int, float, str)) else 0
            self.tank_table.setItem(row_index, 2, max_cap_item)
            
            curr_cap_item = QTableWidgetItem(f"{row['current_capacity']:.2f}")
            curr_cap_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            # 将行索引转换为整数,并确保i是可转换为整数的类型
            row_index = int(float(i)) if isinstance(i, (int, float, str)) else 0
            self.tank_table.setItem(row_index, 3, curr_cap_item)
            
            # 计算剩余容量
            remaining_capacity = row['max_capacity'] - row['current_capacity']
            remain_cap_item = QTableWidgetItem(f"{remaining_capacity:.2f}")
            remain_cap_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            # 将行索引转换为整数,并确保i是可转换为整数的类型
            row_index = int(float(i)) if isinstance(i, (int, float, str)) else 0
            self.tank_table.setItem(row_index, 4, remain_cap_item)

    def refresh_inventory_table(self):
        records = self.db.get_inventory_records()
        self.inventory_table.setRowCount(len(records))
        for i, row in records.iterrows():
            items = [
                QTableWidgetItem(str(row['id'])),
                QTableWidgetItem(str(row['tank_name'])),
                QTableWidgetItem(str(row['date'])),
                QTableWidgetItem(str(row['batch_number'])),
                QTableWidgetItem(f"{row['price']:.2f}"),
                QTableWidgetItem(f"{row['quantity']:.2f}"),
                QTableWidgetItem(f"{row['density']:.4f}"),
                QTableWidgetItem(f"{row['total_price']:.2f}")
            ]
            
            # 设置所有单元格文本居中对齐
            for col, item in enumerate(items):
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                # 将行索引转换为整数,并确保i是可转换为整数的类型
                row_index = int(float(i)) if isinstance(i, (int, float, str)) else 0
                self.inventory_table.setItem(row_index, col, item)
            
            delete_btn = QPushButton('删除')
            delete_btn.setStyleSheet("""
                QPushButton {
                    background-color: #e74c3c;
                    color: white;
                    border: none;
                    border-radius: 3px;
                    padding: 2px 6px;
                    font-size: 12px;
                    font-weight: bold;
                    min-width: 40px;
                    max-width: 40px;
                    min-height: 18px;
                    max-height: 18px;
                }
                QPushButton:hover {
                    background-color: #c0392b;
                }
            """)
            delete_btn.clicked.connect(lambda checked, r=row: self.delete_inventory_record(r['id']))
            # 将行索引i转换为整数
            row_index = int(float(i)) if isinstance(i, (int, float, str)) else 0
            self.inventory_table.setCellWidget(row_index, 8, delete_btn)

    def refresh_sales_table(self):
        try:
            # 获取销售记录前先清空之前缓存的数据
            records = self.db.get_sales_records()
            
            # 输出一些调试信息
            print(f"刷新销售表格，记录数: {len(records)}")
            if not records.empty:
                print(f"第一条记录: {records.iloc[0].to_dict()}")
            
            self.sales_table.setRowCount(len(records))
            for i, row in records.iterrows():
                items = [
                    QTableWidgetItem(str(row['id'])),
                    QTableWidgetItem(str(row['customer_name'])),
                    QTableWidgetItem(str(row['date'])),
                    QTableWidgetItem(str(row['invoice_number'])),
                    QTableWidgetItem(f"{row['price']:.2f}"),
                    QTableWidgetItem(f"{row['quantity']:.2f}"),
                    QTableWidgetItem(f"{row['total_amount']:.2f}")
                ]
                
                # 设置所有单元格文本居中对齐
                for col, item in enumerate(items):
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    # 确保行索引是整数类型
                    row_index = int(float(i)) if isinstance(i, (int, float, str)) else 0
                    self.sales_table.setItem(row_index, col, item)
                
                delete_btn = QPushButton('删除')
                delete_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #e74c3c;
                        color: white;
                        border: none;
                        border-radius: 3px;
                        padding: 2px 6px;
                        font-size: 12px;
                        font-weight: bold;
                        min-width: 40px;
                        max-width: 40px;
                        min-height: 18px;
                        max-height: 18px;
                    }
                    QPushButton:hover {
                        background-color: #c0392b;
                    }
                """)
                delete_btn.clicked.connect(lambda checked, r=row: self.delete_sales_record(r['id']))
                # 将行索引i转换为整数
                row_index = int(float(i)) if isinstance(i, (int, float, str)) else 0
                self.sales_table.setCellWidget(row_index, 7, delete_btn)
            
            # 修复update()方法调用
            self.sales_table.viewport().update()
            
            # 自动滚动到底部
            self.sales_table.scrollToBottom()
        except Exception as e:
            print(f"刷新销售表格出错: {str(e)}")

    def refresh_customer_table(self):
        customers = self.db.get_customers()
        self.customer_table.setRowCount(len(customers))
        for i, row in customers.iterrows():
            id_item = QTableWidgetItem(str(row['id']))
            id_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            # 将行索引转换为整数,并确保i是可转换为整数的类型
            row_index = int(float(i)) if isinstance(i, (int, float, str)) else 0
            self.customer_table.setItem(row_index, 0, id_item)
            
            name_item = QTableWidgetItem(str(row['name']))
            name_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            # 将行索引转换为整数,并确保i是可转换为整数的类型
            row_index = int(float(i)) if isinstance(i, (int, float, str)) else 0
            self.customer_table.setItem(row_index, 1, name_item)
            
            delete_btn = QPushButton('删除')
            delete_btn.setStyleSheet("""
                QPushButton {
                    background-color: #e74c3c;
                    color: white;
                    border: none;
                    border-radius: 3px;
                    padding: 2px 6px;
                    font-size: 12px;
                    font-weight: bold;
                    min-width: 40px;
                    max-width: 40px;
                    min-height: 18px;
                    max-height: 18px;
                }
                QPushButton:hover {
                    background-color: #c0392b;
                }
            """)
            delete_btn.clicked.connect(lambda checked, r=row: self.delete_customer(r['id']))
            # 将行索引转换为整数,并确保i是可转换为整数的类型
            row_index = int(float(i)) if isinstance(i, (int, float, str)) else 0
            self.customer_table.setCellWidget(row_index, 2, delete_btn)

            # 自动滚动到底部
            self.customer_table.scrollToBottom()

    def refresh_tank_combo(self):
        tanks = self.db.get_tanks()
        self.inventory_tank.clear()
        for _, row in tanks.iterrows():
            # 将Series类型转换为str类型
            self.inventory_tank.addItem(str(row['name']), int(row['id']))

    def refresh_customer_combo(self, refresh_sales=True, refresh_customer=True):
        """
        刷新客户下拉框，保留当前选择的文本
        """
        # 获取所有客户
        customers = self.db.get_customers()
        
        # 刷新销售客户下拉框
        if refresh_sales and hasattr(self, 'sales_customer'):
            # 保存当前数据
            current_data = self.sales_customer.currentData()
            
            # 暂时阻止信号
            self.sales_customer.blockSignals(True)
            self.sales_customer.clear()
            
            # 添加所有客户
            for _, row in customers.iterrows():
                # 将Series类型转换为str类型
                self.sales_customer.addItem(str(row['name']), int(row['id']))
            
            # 恢复之前的选择
            if current_data:
                index = self.sales_customer.findData(current_data)
                if index == -1:  # 如果ID不存在则尝试名称匹配
                    current_text = self.sales_customer.currentText()
                    index = self.sales_customer.findText(current_text, Qt.MatchContains)
                
                if index >= 0:
                    self.sales_customer.setCurrentIndex(index)
                else:
                    print(f"未找到匹配客户: ID={current_data}, 文本={self.sales_customer.currentText()}")
                    
            # 恢复信号处理
            self.sales_customer.blockSignals(False)
            
            # 恢复搜索历史
            if hasattr(self, 'sales_customer_search') and hasattr(self, 'sales_search_history'):
                self.sales_customer_search.blockSignals(True)
                self.sales_customer_search.clear()
                for item in self.sales_search_history:
                    self.sales_customer_search.addItem(item)
                self.sales_customer_search.blockSignals(False)
        
        # 刷新客户管理页面的客户下拉框
        if refresh_customer and hasattr(self, 'customer_combo'):
            current_data = self.customer_combo.currentData()
            
            self.customer_combo.blockSignals(True)
            self.customer_combo.clear()
            
            for _, row in customers.iterrows():
                # 将Series对象转换为字符串和整数
                self.customer_combo.addItem(str(row['name']), int(row['id']))
            
            # 恢复之前的选择
            if current_data:
                for i in range(self.customer_combo.count()):
                    if self.customer_combo.itemData(i) == current_data:
                        self.customer_combo.setCurrentIndex(i)
                        break
            
            self.customer_combo.blockSignals(False)
            
            # 恢复搜索历史
            if hasattr(self, 'customer_search') and hasattr(self, 'customer_search_history'):
                self.customer_search.blockSignals(True)
                self.customer_search.clear()
                for item in self.customer_search_history:
                    self.customer_search.addItem(item)
                self.customer_search.blockSignals(False)

    def add_tank(self):
        name = self.tank_name.text()
        capacity = self.tank_capacity.value()
        if not name or capacity <= 0:
            self.statusBar().showMessage('错误: 请输入有效的油罐信息', 3000)
            return
        self.db.add_tank(name, capacity)
        self.refresh_tank_table()
        self.refresh_tank_combo()
        self.tank_name.clear()
        self.tank_capacity.setValue(0)
        self.statusBar().showMessage(f'成功添加油罐: {name}', 3000)

    def add_inventory_record(self):
        # 检查是否由编辑完成事件触发
        sender = self.sender()
        if isinstance(sender, QDoubleSpinBox) and not sender.hasFocus():
            return
        if isinstance(sender, QLineEdit) and not self.focusWidget() == sender:
            return
            
        tank_id = self.inventory_tank.currentData()
        date = self.inventory_date.text()
        batch = self.inventory_batch.text()
        price = self.inventory_price.value()
        quantity = self.inventory_quantity.value()
        density = self.inventory_density.value()
        
        if not tank_id or not date or not batch or price <= 0 or quantity <= 0 or density <= 0:
            self.statusBar().showMessage('错误: 请输入有效的入库信息', 3000)
            return
            
        self.db.add_inventory_record(tank_id, date, batch, price, quantity, density)
        self.refresh_inventory_table()
        self.refresh_tank_table()
        self.inventory_batch.clear()
        self.inventory_price.setValue(0)
        self.inventory_quantity.setValue(0)
        self.inventory_density.setValue(0)
        self.statusBar().showMessage(f'成功添加入库记录: {batch}', 3000)

    def add_customer(self):
        name = self.customer_name.text()
        if not name:
            self.statusBar().showMessage('错误: 请输入客户名称', 3000)
            return
        
        # 检查是否已经存在同名客户
        customers = self.db.get_customers()
        existing_customer = customers[customers['name'] == name]
        if len(existing_customer) > 0:
            self.statusBar().showMessage(f'错误: 客户 "{name}" 已存在', 3000)
            return
            
        self.db.add_customer(name)
        self.refresh_customer_table()
        self.refresh_customer_combo()
        self.customer_name.clear()
        self.statusBar().showMessage(f'成功添加客户: {name}', 3000)

    def add_sales_record(self):
        # 检查是否由编辑完成事件触发
        sender = self.sender()
        if isinstance(sender, QDoubleSpinBox) and not sender.hasFocus():
            return
        if isinstance(sender, QLineEdit) and not self.focusWidget() == sender:
            return
            
        customer_id = self.sales_customer.currentData()
        customer_text = self.sales_customer.currentText().strip()
        date = self.sales_date.text()
        invoice = self.sales_invoice.text()
        price = self.sales_price.value()
        quantity = self.sales_quantity.value()
        total = price * quantity
        tank_id = self.inventory_tank.currentData()

        if not date or not invoice or price <= 0 or quantity <= 0:
            self.statusBar().showMessage('错误: 请输入有效的销售信息', 3000)
            return
        
        if not tank_id:
            self.statusBar().showMessage('错误: 请选择一个油罐', 3000)
            return

        if not customer_id:
            self.statusBar().showMessage('错误: 请选择一个客户', 3000)
            return

        try:
            print(f"添加销售记录: 客户ID={customer_id}, 客户名={customer_text}")
            # 添加销售记录
            self.db.add_sale_record(customer_id, date, invoice, price, quantity, total)
            self.db.update_tank_capacity(tank_id, -quantity)
            
            # 清空输入框，但保持单价不变
            self.sales_invoice.clear()
            self.sales_quantity.setValue(0)
            
            # 强制刷新显示
            QApplication.processEvents()
            
            # 刷新所有相关表格和显示
            self.refresh_sales_table()
            self.refresh_tank_table()
            self.update_profit_display()
            
            # 状态栏消息
            self.statusBar().showMessage(f'成功添加销售记录: {invoice} (客户: {customer_text})', 3000)
            
            # 再次刷新以确保显示最新数据
            QApplication.processEvents()
            self.refresh_sales_table()
        except Exception as e:
            self.statusBar().showMessage(f'错误: 添加销售记录出错: {str(e)}', 5000)

    def delete_inventory_record(self, record_id):
        reply = QMessageBox.question(self, '确认删除', '确定要删除这条入库记录吗？',
                                       QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.db.delete_inventory_record(record_id)
            self.refresh_inventory_table()
            self.refresh_tank_table()

    def delete_sales_record(self, record_id):
        reply = QMessageBox.question(self, '确认删除', '确定要删除这条销售记录吗？',
                                       QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            # 获取销售记录信息以便更新油罐容量
            conn = sqlite3.connect(self.db.db_file)
            cursor = conn.cursor()
            cursor.execute('SELECT quantity FROM sales_records WHERE id = ?', (record_id,))
            quantity = cursor.fetchone()[0]
            conn.close()
            
            # 删除销售记录
            self.db.delete_sales_record(record_id)
            
            # 更新油罐容量（这里假设删除销售记录需要将油罐容量增加）
            # 注意：这里需要选择一个油罐进行更新，如果没有足够的信息，可能需要用户选择
            tank_id = self.inventory_tank.currentData()
            if tank_id:
                self.db.update_tank_capacity(tank_id, quantity)
            
            self.refresh_sales_table()
            self.refresh_tank_table()
            self.update_profit_display()

    def delete_customer(self, customer_id):
        reply = QMessageBox.question(self, '确认删除', '确定要删除这个客户吗？',
                                       QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.db.delete_customer(customer_id)
            self.refresh_customer_table()
            self.refresh_customer_combo()

    def delete_tank(self, tank_id):
        reply = QMessageBox.question(self, '确认删除', '确定要删除这个油罐吗？',
                                       QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            # 检查油罐是否存在
            conn = sqlite3.connect(self.db.db_file)
            cursor = conn.cursor()
            cursor.execute('DELETE FROM tanks WHERE id = ?', (tank_id,))
            conn.commit()
            conn.close()
            self.refresh_tank_table()
            self.refresh_tank_combo()

    def export_to_excel(self):
        filename, _ = QFileDialog.getSaveFileName(self, '导出Excel文件', '', 'Excel Files (*.xlsx)')
        if not filename:
            return
        
        # 直接使用统计页面的日期控件值
        start_date = self.start_date.date().toString('yyyy-MM-dd')
        end_date = self.end_date.date().toString('yyyy-MM-dd')
        
        if self.start_date.date() > self.end_date.date():
            QMessageBox.warning(self, '错误', '开始日期不能晚于结束日期')
            return
        
        try:
            self.db.export_to_excel(filename, start_date, end_date)
            QMessageBox.information(self, '导出成功', f'已导出{start_date}至{end_date}的数据')
        except Exception as e:
            QMessageBox.critical(self, '错误', f'导出失败: {str(e)}')

    def new_file(self):
        reply = QMessageBox.question(self, '确认新建', '确定要新建文件吗？当前数据将丢失。',
                                       QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.db.reset_database()
            self.refresh_all_tables()

    def open_file(self):
        filename, _ = QFileDialog.getOpenFileName(self, '打开文件', '', 'Excel Files (*.xlsx)')
        if filename:
            # 从Excel导入数据
            try:
                # 读取所有工作表
                xls = pd.ExcelFile(filename)
                
                # 导入油罐信息
                if '油罐信息' in xls.sheet_names:
                    tanks = pd.read_excel(xls, '油罐信息')
                    for _, row in tanks.iterrows():
                        self.db.add_tank(row['名称'], row['最大容量'])
                
                # 导入客户信息
                if '客户信息' in xls.sheet_names:
                    customers = pd.read_excel(xls, '客户信息')
                    for _, row in customers.iterrows():
                        self.db.add_customer(row['客户名称'])
                
                # 导入入库记录
                if '入库记录' in xls.sheet_names:
                    inventory = pd.read_excel(xls, '入库记录')
                    for _, row in inventory.iterrows():
                        tank_id = self.db.get_tank_id_by_name(row['油罐名称'])
                        if tank_id:
                            self.db.add_inventory_record(
                                tank_id,
                                row['日期'],
                                row['单号'],
                                row['单价'],
                                row['数量'],
                                row['密度']
                            )
                
                # 导入销售记录
                if '销售记录' in xls.sheet_names:
                    sales = pd.read_excel(xls, '销售记录')
                    for _, row in sales.iterrows():
                        customer_id = self.db.get_customer_id_by_name(row['客户名称'])
                        if customer_id:
                            self.db.add_sale_record(
                                customer_id,
                                row['日期'],
                                row['单号'],
                                row['单价'],
                                row['数量'],
                                row['总价']
                            )
                
                self.statusBar().showMessage('成功从Excel导入数据', 3000)
                self.refresh_all_tables()
            except Exception as e:
                QMessageBox.warning(self, '导入失败', f'导入Excel数据时出错: {str(e)}')

    def save_file_as(self):
        filename, _ = QFileDialog.getSaveFileName(self, '另存为', '', 'Excel Files (*.xlsx)')
        if filename:
            start_date = QInputDialog.getText(self, '开始日期', '请输入开始日期(YYYY-MM-DD):', text='2023-01-01')[0]
        end_date = QInputDialog.getText(self, '结束日期', '请输入结束日期(YYYY-MM-DD):', text=QDate.currentDate().toString('yyyy-MM-dd'))[0]
        
        try:
            QDate.fromString(start_date, 'yyyy-MM-dd')
            QDate.fromString(end_date, 'yyyy-MM-dd')
            self.db.export_to_excel(filename, start_date, end_date)
        except:
            QMessageBox.warning(self, '错误', '日期格式无效，请使用YYYY-MM-DD格式')
            QMessageBox.information(self, '成功', '数据已成功保存到Excel文件', QMessageBox.StandardButton.Ok)

    def refresh_all_tables(self):
        self.refresh_tank_table()
        self.refresh_inventory_table()
        self.refresh_sales_table()
        self.refresh_customer_table()

    def generate_customer_report(self, start_date, end_date):
        # 假设这里有一个方法可以生成客户报告
        # 从数据库获取客户销售记录
        conn = sqlite3.connect(self.db.db_file)
        query = f"""
            SELECT 
                c.name as customer_name,
                s.date,
                s.invoice_number,
                s.price,
                s.quantity,
                s.total_amount
            FROM sales_records s
            JOIN customers c ON s.customer_id = c.id
            WHERE s.date BETWEEN '{start_date}' AND '{end_date}'
            ORDER BY s.date
        """
        report = pd.read_sql_query(query, conn)
        conn.close()
        return report

    def generate_profit_report(self, start_date, end_date):
        # 假设这里有一个方法可以生成利润报告
        # 从数据库获取销售和入库记录
        conn = sqlite3.connect(self.db.db_file)
        
        # 获取销售记录
        sales_query = f"""
            SELECT date, SUM(total_amount) as sales_amount
            FROM sales_records 
            WHERE date BETWEEN '{start_date}' AND '{end_date}'
            GROUP BY date
        """
        sales = pd.read_sql_query(sales_query, conn)
        
        # 获取入库记录
        inventory_query = f"""
            SELECT date, SUM(price * quantity) as inventory_cost
            FROM inventory_records
            WHERE date BETWEEN '{start_date}' AND '{end_date}'
            GROUP BY date
        """
        inventory = pd.read_sql_query(inventory_query, conn)
        
        # 合并销售和入库数据
        report = pd.merge(sales, inventory, on='date', how='outer').fillna(0)
        
        # 计算每日利润
        report['profit'] = report['sales_amount'] - report['inventory_cost']
        
        conn.close()
        return report

    def export_customer_report(self, start_date, end_date):
        report = self.generate_customer_report(start_date, end_date)
        filename, _ = QFileDialog.getSaveFileName(self, '导出客户报告', '', 'Excel Files (*.xlsx)')
        if filename:
            report.to_excel(filename)
            QMessageBox.information(self, '成功', '客户报告已成功导出', QMessageBox.StandardButton.Ok)

    def export_profit_report(self, start_date, end_date):
        report = self.generate_profit_report(start_date, end_date)
        filename, _ = QFileDialog.getSaveFileName(self, '导出利润报告', '', 'Excel Files (*.xlsx)')
        if filename:
            report.to_excel(filename)
            QMessageBox.information(self, '成功', '利润报告已成功导出', QMessageBox.StandardButton.Ok)

    def reset_database(self):
        reply = QMessageBox.question(self, '确认初始化', '确定要初始化所有数据吗？',
                                       QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.db.reset_database()
            # 全面刷新界面
            self.refresh_all_tables()
            self.refresh_tank_combo()
            self.refresh_customer_combo()
            
            # 重置所有表单输入
            if hasattr(self, 'tank_name'):
                self.tank_name.clear()
            if hasattr(self, 'tank_capacity'):
                self.tank_capacity.setValue(0)
            if hasattr(self, 'inventory_batch'):
                self.inventory_batch.clear()  # 使用clear()方法清空QLineEdit内容
            if hasattr(self, 'inventory_price'):
                self.inventory_price.setValue(0)
            if hasattr(self, 'inventory_quantity'):
                self.inventory_quantity.setValue(0)
            if hasattr(self, 'inventory_density'):
                self.inventory_density.setValue(0)
            if hasattr(self, 'customer_name'):
                self.customer_name.clear()
            if hasattr(self, 'sales_invoice'):
                self.sales_invoice.clear()
            if hasattr(self, 'sales_price'):
                self.sales_price.setValue(0)
            if hasattr(self, 'sales_quantity'):
                self.sales_quantity.setValue(0)
                
            # 更新利润显示
            self.update_profit_display()
            
            QMessageBox.information(self, '成功', '系统已成功初始化！', QMessageBox.StandardButton.Ok)

    def view_customer_data(self):
        start_date = self.customer_start_date.date().toString('yyyy-MM-dd')
        end_date = self.customer_end_date.date().toString('yyyy-MM-dd')
        customer_id = self.customer_combo.currentData()
        if not customer_id:
            QMessageBox.warning(self, '错误', '请选择一个客户')
            return
        customer_data = self.db.get_customer_data(customer_id, start_date, end_date)
        total_quantity = customer_data['quantity'].sum()
        total_amount = customer_data['total_amount'].sum()
        QMessageBox.information(self, '客户数据', f'总加油量: {total_quantity} 升\n总金额: {total_amount} 元', QMessageBox.StandardButton.Ok)
        print(customer_data)

    def update_profit_display(self):
        # 调用数据库中的方法计算利润
        total_profit = self.db.calculate_total_profit()
        monthly_profit = self.db.calculate_monthly_profit()

        # 更新界面显示
        self.total_profit_label.setText(f'总利润: {total_profit:.2f} 元')
        if monthly_profit:
            monthly_profit_text = ', '.join([f'{month}: {profit:.2f}' for month, profit in monthly_profit])
            self.monthly_profit_label.setText(f'月利润: {monthly_profit_text}')

    def update_profit_by_period(self):
        # 获取选择的时期
        start_date = self.profit_start_date.date().toString('yyyy-MM-dd')
        end_date = self.profit_end_date.date().toString('yyyy-MM-dd')
        
        # 计算指定时期的利润
        period_profit = self.db.calculate_profit_by_period(start_date, end_date)
        
        # 更新利润显示
        QMessageBox.information(self, '周期利润', f'{start_date} 至 {end_date} 的利润为: {period_profit:.2f} 元', QMessageBox.StandardButton.Ok)
        
        # 更新月利润显示
        monthly_profit = self.db.calculate_monthly_profit()
        if monthly_profit:
            monthly_profit_text = ', '.join([f'{month}: {profit:.2f}' for month, profit in monthly_profit])
            self.monthly_profit_label.setText(f'月利润: {monthly_profit_text}')

    def filter_sales_customer_combo(self):
        # 获取搜索文本,并转换为小写并去除首尾空格
        search_text = self.sales_customer_search.currentText().lower().strip()
        # 保存当前光标位置
        cursor_pos = self.sales_customer_search.lineEdit().cursorPosition()
        # 禁用自动补全和自动选择
        self.sales_customer_search.setCompleter(None)
        self.sales_customer_search.setCurrentText(search_text)
        
        # 获取当前选择的客户ID
        current_data = self.sales_customer.currentData()
        
        # 阻止信号
        self.sales_customer.blockSignals(True)
        self.sales_customer.clear()
        
        # 从数据库获取所有客户
        customers = self.db.get_customers()
        
        # 添加匹配的客户
        matched_customers = []
        
        for _, row in customers.iterrows():
            customer_name = str(row['name']).lower()
            customer_phone = str(row.get('phone', '')).lower()
            # 显示格式包含客户名称和电话
            display_text = str(row['name'])
            
            # 如果搜索文本为空或客户名称/电话包含搜索文本，则添加到匹配列表
            if not search_text or search_text in customer_name or search_text in customer_phone:
                matched_customers.append((display_text, int(row['id'])))
        
        # 按客户名称排序
        matched_customers.sort(key=lambda x: x[0])
        
        # 添加匹配的客户到下拉框
        for display_text, id in matched_customers:
            self.sales_customer.addItem(display_text, id)
        
        # 恢复之前的选择
        if self.sales_customer.count() > 0:
            if current_data:
                index = self.sales_customer.findData(current_data)
                self.sales_customer.setCurrentIndex(index if index >= 0 else 0)
            else:
                self.sales_customer.setCurrentIndex(0)
        
        # 恢复信号
        self.sales_customer.blockSignals(False)
        
        # 更新搜索历史
        if search_text and search_text not in self.sales_search_history:
            self.sales_search_history.insert(0, search_text)
            self.sales_search_history = self.sales_search_history[:6]  # 保留最近6条记录
            
            # 更新搜索框的下拉历史
            self.sales_customer_search.blockSignals(True)
            self.sales_customer_search.clear()
            self.sales_customer_search.addItem('')  # 添加一个空选项
            for item in self.sales_search_history:
                self.sales_customer_search.addItem(item)
            self.sales_customer_search.setCurrentText(search_text)  # 保持当前输入文本
            # 恢复光标位置
            self.sales_customer_search.lineEdit().setCursorPosition(cursor_pos)
            # 禁用自动选择
            self.sales_customer_search.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
            self.sales_customer_search.blockSignals(False)

    def filter_customer_combo(self):
        # 获取搜索文本,并转换为小写并去除首尾空格
        search_text = self.customer_search.currentText().lower().strip()
        # 保存当前光标位置
        cursor_pos = self.customer_search.lineEdit().cursorPosition()
        # 禁用自动补全和自动选择
        self.customer_search.setCompleter(None)
        self.customer_search.setCurrentText(search_text)
        
        # 获取当前选择的客户ID
        current_data = self.customer_combo.currentData()
        
        # 阻止信号
        self.customer_combo.blockSignals(True)
        self.customer_combo.clear()
        
        # 从数据库获取所有客户
        customers = self.db.get_customers()
        
        # 添加匹配的客户
        matched_customers = []
        
        for _, row in customers.iterrows():
            customer_name = str(row['name']).lower()
            customer_phone = str(row.get('phone', '')).lower()
            # 显示格式包含客户名称和电话
            display_text = str(row['name'])
            
            # 如果搜索文本为空或客户名称/电话包含搜索文本，则添加到匹配列表
            if not search_text or search_text in customer_name or search_text in customer_phone:
                matched_customers.append((display_text, int(row['id'])))
        
        # 按客户名称排序
        matched_customers.sort(key=lambda x: x[0])
        
        # 添加匹配的客户到下拉框
        for display_text, id in matched_customers:
            self.customer_combo.addItem(display_text, id)
        
        # 恢复之前的选择
        if self.customer_combo.count() > 0:
            if current_data:
                index = self.customer_combo.findData(current_data)
                self.customer_combo.setCurrentIndex(index if index >= 0 else 0)
            else:
                self.customer_combo.setCurrentIndex(0)
        
        # 恢复信号
        self.customer_combo.blockSignals(False)
        
        # 更新搜索历史
        if search_text and search_text not in self.customer_search_history:
            self.customer_search_history.insert(0, search_text)
            self.customer_search_history = self.customer_search_history[:6]  # 保留最近6条记录
            
            # 更新搜索框的下拉历史
            self.customer_search.blockSignals(True)
            self.customer_search.clear()
            self.customer_search.addItem('')  # 添加一个空选项
            for item in self.customer_search_history:
                self.customer_search.addItem(item)
            self.customer_search.setCurrentText(search_text)  # 保持当前输入文本
            # 恢复光标位置
            self.customer_search.lineEdit().setCursorPosition(cursor_pos)
            # 禁用自动选择
            self.customer_search.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
            self.customer_search.blockSignals(False)
        
        # 更新搜索历史
        if search_text and search_text not in self.customer_search_history:
            self.customer_search_history.insert(0, search_text)
            self.customer_search_history = self.customer_search_history[:6]  # 保留最近6条记录
            
            # 更新搜索框的下拉历史
            self.customer_search.blockSignals(True)
            self.customer_search.clear()
            self.customer_search.addItem('')  # 添加一个空选项
            for item in self.customer_search_history:
                self.customer_search.addItem(item)
            self.customer_search.setCurrentText(search_text)  # 保持当前输入文本
            # 恢复光标位置
            self.customer_search.lineEdit().setCursorPosition(cursor_pos)
            # 禁用自动选择
            self.customer_search.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
            self.customer_search.blockSignals(False)
    
    def add_customer_search_history(self):
        # 获取当前搜索文本
        search_text = self.customer_search.currentText().strip()
        
        # 如果搜索文本不为空且不在历史记录中，则添加到历史记录
        if search_text and search_text not in self.customer_search_history:
            self.customer_search_history.insert(0, search_text)
            self.customer_search_history = self.customer_search_history[:6]  # 保留最近6条记录
            
            # 更新搜索框的下拉历史
            self.customer_search.blockSignals(True)
            self.customer_search.clear()
            self.customer_search.addItem('')  # 添加一个空选项
            for item in self.customer_search_history:
                self.customer_search.addItem(item)
            self.customer_search.setCurrentText(search_text)  # 保持当前输入文本
            # 恢复光标位置
            self.customer_search.lineEdit().setCursorPosition(cursor_pos)
            # 禁用自动选择
            self.customer_search.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
            self.customer_search.blockSignals(False)

    def add_sales_search_history(self, index):
        """添加销售管理页面的客户搜索历史"""
        # 获取搜索框中的文本并去除首尾空格
        text = self.sales_customer_search.currentText().strip()
        if not text or text in self.sales_search_history:
            return
            
        # 将当前搜索添加到历史记录
        self.sales_search_history.insert(0, text)
        # 限制历史记录数量为6个
        self.sales_search_history = self.sales_search_history[:6]
        
        # 更新下拉框
        self.sales_customer_search.blockSignals(True)
        self.sales_customer_search.clear()
        for item in self.sales_search_history:
            self.sales_customer_search.addItem(item)
        self.sales_customer_search.blockSignals(False)
    
    def add_customer_search_history(self, index):
        """添加客户管理页面的客户搜索历史"""
        text = self.customer_search.currentText().strip()
        if not text or text in self.customer_search_history:
            return
            
        # 将当前搜索添加到历史记录
        self.customer_search_history.insert(0, text)
        # 限制历史记录数量为6个
        self.customer_search_history = self.customer_search_history[:6]
        
        # 更新下拉框
        self.customer_search.blockSignals(True)
        self.customer_search.clear()
        for item in self.customer_search_history:
            self.customer_search.addItem(item)
        self.customer_search.blockSignals(False)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = DieselSalesSystem()
    window.show()
    sys.exit(app.exec())