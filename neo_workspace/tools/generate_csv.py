import os
import csv
import sqlite3
import random
from datetime import datetime

def generate_random_name():
    """Generate a random name"""
    first_names = ["Иван", "Петр", "Сергей", "Александр", "Дмитрий"]
    last_names = ["Иванов", "Петров", "Сергеев", "Алексеев", "Дмитриев"]
    return f"{random.choice(first_names)} {random.choice(last_names)}"

def generate_random_age():
    """Generate a random age between 18 and 100"""
    return random.randint(18, 100)

def generate_random_city():
    """Generate a random city"""
    cities = ["Москва", "Санкт-Петербург", "Казань", "Новосибирск", "Екатеринбург"]
    return random.choice(cities)

def run_tool(inputs: dict) -> dict:
    output_dir = inputs.get("output_dir", "/tmp")
    try:
        rows = int(inputs.get("rows", 1000))
        columns = inputs.get("columns", ["Имя", "Возраст", "Город"])
        chat_id = inputs.get("chat_id", "")
        task = inputs.get("task", "")

        print(f"Generating CSV file with {rows} rows and columns: {columns}")

        # Generate CSV file
        csv_filename = f"test_{datetime.now().strftime('%Y%m%d%H%M%S')}.csv"
        csv_path = os.path.join(output_dir, csv_filename)
        with open(csv_path, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(columns)
            for _ in range(rows):
                writer.writerow([generate_random_name(), generate_random_age(), generate_random_city()])

        print(f"CSV file generated: {csv_path}")

        # Convert CSV to SQLite database
        db_filename = f"test_{datetime.now().strftime('%Y%m%d%H%M%S')}.db"
        db_path = os.path.join(output_dir, db_filename)
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Create table
        create_table_query = f"CREATE TABLE IF NOT EXISTS test ({columns[0]} TEXT, {columns[1]} INTEGER, {columns[2]} TEXT)"
        cursor.execute(create_table_query)

        # Insert data from CSV
        with open(csv_path, 'r') as csvfile:
            reader = csv.reader(csvfile)
            next(reader)  # Skip header
            for row in reader:
                insert_query = f"INSERT INTO test VALUES (?, ?, ?)"
                cursor.execute(insert_query, row)

        conn.commit()
        conn.close()

        print(f"SQLite database generated: {db_path}")

        result = f"CSV file generated: {csv_path}\nSQLite database generated: {db_path}"
        return {"ok": True, "output": result, "files": [csv_path, db_path], "error": ""}
    except Exception as e:
        return {"ok": False, "output": "", "files": [], "error": str(e)}