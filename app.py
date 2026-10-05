import streamlit as st
import sqlite3
import pandas as pd

st.title("🏨 ИИ арқылы отель нөмірін брондау жүйесі")

# Деректер базасынан нөмірлерді оқу функциясы
def get_rooms_from_db():
    conn = sqlite3.connect('hotel_system.db')
    df = pd.read_sql_query("SELECT * FROM rooms", conn)
    conn.close()
    return df

rooms_df = get_rooms_from_db()

# Интерфейс
st.subheader("Қолжетімді нөмірлер тізімі:")
st.dataframe(rooms_df)

max_price = st.slider("Максималды баға ($):", 50, 300, 150)
filtered = rooms_df[rooms_df['price_per_night'] <= max_price]

st.write(matching := f"Сіздің талабыңызға сай {len(filtered)} нөмір табылды:")
st.table(filtered[['room_type', 'price_per_night', 'capacity', 'description']])
