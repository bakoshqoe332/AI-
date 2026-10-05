import streamlit as st
import sqlite3
import pandas as pd

st.title("🏨 ИИ арқылы отель нөмірін брондау жүйесі")
st.write("GitHub репозиторийінен жұмыс істейтін қосымша.")

# 1. Деректер базасы мен кестені автоматты түрде құру функциясы
def init_db():
    conn = sqlite3.connect('hotel_system.db')
    cursor = conn.cursor()
    
    # Нөмірлер кестесін жасау
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS rooms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            room_type TEXT NOT NULL,
            price_per_night REAL NOT NULL,
            capacity INTEGER NOT NULL,
            has_balcony INTEGER NOT NULL,
            description TEXT
        )
    ''')
    
    # Егер кесте бос болса, бастапқы мысал деректерді қосу
    cursor.execute("SELECT COUNT(*) FROM rooms")
    if cursor.fetchone()[0] == 0:
        sample_rooms = [
            ('Standard', 70.0, 2, 0, 'Ықшам әрі жайлы стандартты нөмір'),
            ('Deluxe', 120.0, 2, 1, 'Керемет көрінісі бар және балконы бар жақсартылған нөмір'),
            ('Suite', 250.0, 4, 1, 'Үлкен отбасыға арналған люкс нөмір')
        ]
        cursor.executemany('''
            INSERT INTO rooms (room_type, price_per_night, capacity, has_balcony, description)
            VALUES (?, ?, ?, ?, ?)
        ''', sample_rooms)
    
    conn.commit()
    conn.close()

# 2. Деректерді базадан оқу функциясы
def get_rooms_from_db():
    init_db()  # Алдымен база мен кестенің барын тексеріп, жоқ болса жасаймыз
    conn = sqlite3.connect('hotel_system.db')
    df = pd.read_sql_query("SELECT * FROM rooms", conn)
    conn.close()
    return df

# Деректерді жүктеу
rooms_df = get_rooms_from_db()

st.subheader("Қолжетімді нөмірлер тізімі:")
st.dataframe(rooms_df)

max_price = st.slider("Максималды баға ($):", 50, 300, 150)
filtered = rooms_df[rooms_df['price_per_night'] <= max_price]

st.write(f"Сіздің талабыңызға сай {len(filtered)} нөмір табылды:")
st.table(filtered[['room_type', 'price_per_night', 'capacity', 'description']])
