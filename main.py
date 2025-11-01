import sys
import sqlite3
from PyQt5 import QtWidgets, QtCore, QtGui

DB = "smartshop.db"

def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, password TEXT, role TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT, barcode TEXT UNIQUE, name TEXT, buy_price REAL, sell_price REAL, qty INTEGER)""")
    c.execute("""CREATE TABLE IF NOT EXISTS customers (
        id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, phone TEXT, address TEXT)
    """)
    c.execute("""CREATE TABLE IF NOT EXISTS sales (
        id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, barcode TEXT, name TEXT, qty INTEGER, total REAL)""")
    # create default admin
    try:
        c.execute("INSERT INTO users (username,password,role) VALUES (?,?,?)", ("admin","admin","Admin"))
    except:
        pass
    conn.commit()
    conn.close()

class LoginWindow(QtWidgets.QWidget):
    switch_to_main = QtCore.pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle("SmartShop POS - Login")
        self.setFixedSize(360,180)
        layout = QtWidgets.QVBoxLayout()
        form = QtWidgets.QFormLayout()
        self.user = QtWidgets.QLineEdit()
        self.pwd = QtWidgets.QLineEdit()
        self.pwd.setEchoMode(QtWidgets.QLineEdit.Password)
        form.addRow("Username:", self.user)
        form.addRow("Password:", self.pwd)
        layout.addLayout(form)
        btn = QtWidgets.QPushButton("Login")
        btn.clicked.connect(self.handle_login)
        layout.addWidget(btn)
        self.msg = QtWidgets.QLabel("")
        layout.addWidget(self.msg)
        self.setLayout(layout)

    def handle_login(self):
        username = self.user.text()
        pwd = self.pwd.text()
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute("SELECT role FROM users WHERE username=? AND password=?", (username,pwd))
        r = c.fetchone()
        conn.close()
        if r:
            self.switch_to_main.emit()
        else:
            self.msg.setText("Invalid credentials")

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SmartShop POS - Dashboard")
        self.resize(1000,600)
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        layout = QtWidgets.QHBoxLayout()
        central.setLayout(layout)

        # Left sidebar
        sidebar = QtWidgets.QFrame()
        sidebar.setFixedWidth(220)
        sb_layout = QtWidgets.QVBoxLayout()
        sidebar.setLayout(sb_layout)
        logo = QtWidgets.QLabel("SmartShop POS")
        logo.setAlignment(QtCore.Qt.AlignCenter)
        logo.setStyleSheet("font-weight:700; font-size:18px;")
        sb_layout.addWidget(logo)
        sb_layout.addSpacing(10)
        for name in ["Dashboard","Sales","Products","Customers","Reports","Settings","Logout"]:
            b = QtWidgets.QPushButton(name)
            b.setObjectName(name.lower())
            b.clicked.connect(self.menu_clicked)
            sb_layout.addWidget(b)
        sb_layout.addStretch()
        layout.addWidget(sidebar)

        # Content area (stacked)
        self.stack = QtWidgets.QStackedWidget()
        self.stack.addWidget(self.page_dashboard())
        self.stack.addWidget(self.page_sales())
        self.stack.addWidget(self.page_products())
        self.stack.addWidget(self.page_customers())
        self.stack.addWidget(self.page_reports())
        self.stack.addWidget(self.page_settings())
        layout.addWidget(self.stack)

    def menu_clicked(self):
        sender = self.sender().objectName()
        mapping = {
            "dashboard":0,"sales":1,"products":2,"customers":3,"reports":4,"settings":5,"logout":0
        }
        if sender=="logout":
            QtWidgets.qApp.quit()
            return
        idx = mapping.get(sender,0)
        self.stack.setCurrentIndex(idx)

    def page_dashboard(self):
        w = QtWidgets.QWidget()
        l = QtWidgets.QVBoxLayout()
        title = QtWidgets.QLabel("Dashboard")
        title.setStyleSheet("font-size:20px; font-weight:700;")
        l.addWidget(title)
        # simple summary boxes
        boxes = QtWidgets.QHBoxLayout()
        for t in ["Today's Sales: 0","Products: 0","Low Stock: 0"]:
            box = QtWidgets.QFrame()
            box.setFrameShape(QtWidgets.QFrame.StyledPanel)
            box.setFixedHeight(100)
            lab = QtWidgets.QLabel(t)
            lab.setAlignment(QtCore.Qt.AlignCenter)
            box_layout = QtWidgets.QVBoxLayout()
            box_layout.addWidget(lab)
            box.setLayout(box_layout)
            boxes.addWidget(box)
        l.addLayout(boxes)
        w.setLayout(l)
        return w

    def page_sales(self):
        w = QtWidgets.QWidget()
        l = QtWidgets.QVBoxLayout()
        title = QtWidgets.QLabel("Sales")
        title.setStyleSheet("font-size:18px; font-weight:600;")
        l.addWidget(title)
        form = QtWidgets.QHBoxLayout()
        self.barcode_input = QtWidgets.QLineEdit()
        self.barcode_input.setPlaceholderText("Scan barcode or type and press Enter")
        self.barcode_input.returnPressed.connect(self.add_product_by_barcode)
        form.addWidget(self.barcode_input)
        self.qty_input = QtWidgets.QSpinBox()
        self.qty_input.setValue(1)
        form.addWidget(self.qty_input)
        add_btn = QtWidgets.QPushButton("Add to Cart")
        add_btn.clicked.connect(self.add_product_by_barcode)
        form.addWidget(add_btn)
        l.addLayout(form)
        # cart table
        self.cart_table = QtWidgets.QTableWidget(0,4)
        self.cart_table.setHorizontalHeaderLabels(["Barcode","Name","Qty","Total"])
        l.addWidget(self.cart_table)
        # finalize sale
        fin = QtWidgets.QHBoxLayout()
        self.total_label = QtWidgets.QLabel("Total: 0.00")
        fin.addWidget(self.total_label)
        sale_btn = QtWidgets.QPushButton("Complete Sale")
        sale_btn.clicked.connect(self.complete_sale)
        fin.addWidget(sale_btn)
        l.addLayout(fin)
        w.setLayout(l)
        return w

    def add_product_by_barcode(self):
        barcode = self.barcode_input.text().strip()
        if not barcode:
            return
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute("SELECT name, sell_price, qty FROM products WHERE barcode=?", (barcode,))
        r = c.fetchone()
        if not r:
            QtWidgets.QMessageBox.warning(self, "Not found", "Product not found in inventory.")
            conn.close()
            return
        name, price, stock = r
        qty = self.qty_input.value()
        if qty > stock:
            QtWidgets.QMessageBox.warning(self, "Stock", "Not enough stock.")
            conn.close()
            return
        row = self.cart_table.rowCount()
        self.cart_table.insertRow(row)
        self.cart_table.setItem(row,0, QtWidgets.QTableWidgetItem(barcode))
        self.cart_table.setItem(row,1, QtWidgets.QTableWidgetItem(name))
        self.cart_table.setItem(row,2, QtWidgets.QTableWidgetItem(str(qty)))
        total = price * qty
        self.cart_table.setItem(row,3, QtWidgets.QTableWidgetItem(f"{total:.2f}"))
        # update total label
        self.update_total()
        conn.close()
        self.barcode_input.clear()
        self.qty_input.setValue(1)

    def update_total(self):
        total = 0.0
        for r in range(self.cart_table.rowCount()):
            item = self.cart_table.item(r,3)
            if item:
                try:
                    total += float(item.text())
                except:
                    pass
        self.total_label.setText(f"Total: {total:.2f}")

    def complete_sale(self):
        rows = self.cart_table.rowCount()
        if rows==0:
            return
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        for r in range(rows):
            barcode = self.cart_table.item(r,0).text()
            name = self.cart_table.item(r,1).text()
            qty = int(self.cart_table.item(r,2).text())
            total = float(self.cart_table.item(r,3).text())
            c.execute("INSERT INTO sales (date, barcode, name, qty, total) VALUES (datetime('now'),?,?,?,?)", (barcode, name, qty, total))
            # reduce stock
            c.execute("UPDATE products SET qty = qty - ? WHERE barcode=?", (qty, barcode))
        conn.commit()
        conn.close()
        QtWidgets.QMessageBox.information(self, "Sale", "Sale completed.")
        self.cart_table.setRowCount(0)
        self.update_total()

    def page_products(self):
        w = QtWidgets.QWidget()
        l = QtWidgets.QVBoxLayout()
        title = QtWidgets.QLabel("Products")
        title.setStyleSheet("font-size:18px; font-weight:600;")
        l.addWidget(title)
        toolbar = QtWidgets.QHBoxLayout()
        add_btn = QtWidgets.QPushButton("Add Product")
        add_btn.clicked.connect(self.open_add_product)
        toolbar.addWidget(add_btn)
        l.addLayout(toolbar)
        self.prod_table = QtWidgets.QTableWidget(0,6)
        self.prod_table.setHorizontalHeaderLabels(["ID","Barcode","Name","Buy","Sell","Qty"])
        l.addWidget(self.prod_table)
        refresh = QtWidgets.QPushButton("Refresh")
        refresh.clicked.connect(self.load_products)
        l.addWidget(refresh)
        w.setLayout(l)
        self.load_products()
        return w

    def open_add_product(self):
        dlg = AddProductDialog(self)
        dlg.exec_()
        self.load_products()

    def load_products(self):
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute("SELECT id,barcode,name,buy_price,sell_price,qty FROM products")
        rows = c.fetchall()
        conn.close()
        self.prod_table.setRowCount(0)
        for r in rows:
            row = self.prod_table.rowCount()
            self.prod_table.insertRow(row)
            for i,val in enumerate(r):
                self.prod_table.setItem(row,i, QtWidgets.QTableWidgetItem(str(val)))

    def page_customers(self):
        w = QtWidgets.QWidget()
        l = QtWidgets.QVBoxLayout()
        l.addWidget(QtWidgets.QLabel("Customers (To be implemented)"))
        w.setLayout(l)
        return w

    def export_sales_csv(self):
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute("SELECT date, barcode, name, qty, total FROM sales ORDER BY date DESC")
        rows = c.fetchall()
        conn.close()
        # save CSV
        import csv
        fn = QtWidgets.QFileDialog.getSaveFileName(self, 'Save CSV', 'sales_report.csv', 'CSV Files (*.csv)')
        if fn and fn[0]:
            with open(fn[0], 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(['date','barcode','name','qty','total'])
                writer.writerows(rows)
            QtWidgets.QMessageBox.information(self, 'Exported', f'Saved to {fn[0]}')

    def page_reports(self):
        w = QtWidgets.QWidget()
        l = QtWidgets.QVBoxLayout()
        title = QtWidgets.QLabel("Reports")
        title.setStyleSheet("font-size:18px; font-weight:600;")
        l.addWidget(title)
        exp = QtWidgets.QPushButton('Export Sales CSV')
        exp.clicked.connect(self.export_sales_csv)
        l.addWidget(exp)
        w.setLayout(l)
        return w

    def page_settings(self):
        w = QtWidgets.QWidget()
        l = QtWidgets.QVBoxLayout()
        l.addWidget(QtWidgets.QLabel("Settings (To be implemented)"))
        w.setLayout(l)
        return w

class AddProductDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Product")
        self.setFixedSize(400,260)
        layout = QtWidgets.QFormLayout()
        self.barcode = QtWidgets.QLineEdit()
        self.name = QtWidgets.QLineEdit()
        self.buy = QtWidgets.QDoubleSpinBox()
        self.buy.setMaximum(999999)
        self.sell = QtWidgets.QDoubleSpinBox()
        self.sell.setMaximum(999999)
        self.qty = QtWidgets.QSpinBox()
        self.qty.setMaximum(1000000)
        layout.addRow("Barcode:", self.barcode)
        layout.addRow("Name:", self.name)
        layout.addRow("Buy Price:", self.buy)
        layout.addRow("Sell Price:", self.sell)
        layout.addRow("Qty:", self.qty)
        btn = QtWidgets.QPushButton("Save")
        btn.clicked.connect(self.save_product)
        layout.addRow(btn)
        self.setLayout(layout)

    def save_product(self):
        b = self.barcode.text().strip()
        n = self.name.text().strip()
        buy = self.buy.value()
        sell = self.sell.value()
        q = self.qty.value()
        if not b or not n:
            QtWidgets.QMessageBox.warning(self, "Validation", "Barcode and Name required.")
            return
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        try:
            c.execute("INSERT INTO products (barcode,name,buy_price,sell_price,qty) VALUES (?,?,?,?,?)", (b,n,buy,sell,q))
            conn.commit()
            QtWidgets.QMessageBox.information(self, "Saved", "Product saved.")
            self.accept()
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "Error", str(e))
        conn.close()

def main():
    init_db()
    app = QtWidgets.QApplication(sys.argv)
    login = LoginWindow()
    mainw = MainWindow()
    login.switch_to_main.connect(mainw.show)
    login.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()