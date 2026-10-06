"""
Створює таблиці та початкові дані MiniCafe у PostgreSQL (Railway).

Запуск з папки проекту:   py database/init_db.py
Адреса бази береться з файлу .env (змінна DATABASE_URL) або зі змінної середовища.
Для запуску з комп'ютера потрібна ПУБЛІЧНА адреса (DATABASE_PUBLIC_URL з Railway),
внутрішня postgres.railway.internal працює лише всередині Railway.
"""
import os
import sys

import psycopg2

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))


def main() -> int:
    url = os.getenv("DATABASE_URL")
    if not url:
        print("Немає DATABASE_URL. Скопіюй .env.example у .env і встав публічну адресу бази Railway.")
        return 1
    if "railway.internal" in url:
        print("Це ВНУТРІШНЯ адреса Railway, з комп'ютера вона не відкриється.\n"
              "Візьми DATABASE_PUBLIC_URL (хост *.proxy.rlwy.net) у Railway: Postgres -> Variables.")
        return 1

    with open(os.path.join(HERE, "schema_postgres.sql"), encoding="utf-8") as f:
        sql = f.read()

    try:
        conn = psycopg2.connect(url, connect_timeout=15)
    except Exception as e:
        print(f"Не вдалося підключитися: {e}")
        return 1

    try:
        with conn, conn.cursor() as cur:
            cur.execute(sql)
        with conn.cursor() as cur:
            for table in ("menucategories", "products", "menuitems", "menuitemingredients",
                          "cafetables", "employees", "orders", "orderitems"):
                cur.execute(f"SELECT COUNT(*) FROM {table}")
                print(f"  {table:<22} {cur.fetchone()[0]}")
        print("Готово: база MiniCafe налаштована.")
        return 0
    except Exception as e:
        print(f"Помилка виконання скрипта: {e}")
        return 1
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
