import sqlite3

# Connect to the database
conn = sqlite3.connect('database.db')
cursor = conn.cursor()

# Get the schema for Drink and Sale tables
print("Drink Table Schema:")
cursor.execute("PRAGMA table_info(drink)")
for column in cursor.fetchall():
    print(column)

print("\nSale Table Schema:")
cursor.execute("PRAGMA table_info(sale)")
for column in cursor.fetchall():
    print(column)

conn.close()
