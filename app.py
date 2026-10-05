import streamlit as st
import sqlite3
import pandas as pd
import random
import re

st.title("🏨 ИИ арқылы отель нөмірін брондау жүйесі")
st.write("100 түрлі бірегей сипаттамасы бар нөмірлер базасы (101-ден 200-ге дейін).")

# 1. 100 әртүрлі сипаттамасы бар нөмірді генерациялау
def init_db():
    conn = sqlite3.connect('hotel_system.db')
    cursor = conn.cursor()
    cursor.execute('DROP TABLE IF EXISTS rooms')
    cursor.execute('''
        CREATE TABLE rooms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            room_type TEXT NOT NULL,
            price_per_night REAL NOT NULL,
            capacity INTEGER NOT NULL,
            has_balcony INTEGER NOT NULL,
            description TEXT
        )
    ''')
    
    room_categories = [
        ("Standard Single", 40.0, 45.0, 1, 0, "Бір адамға арналған ықшам және қолжетімді стандартты нөмір"),
        ("Standard Double", 65.0, 80.0, 2, 0, "Екі адамға арналған жайлы стандартты нөмір"),
        ("Standard Twin", 70.0, 85.0, 2, 0, "Екі бөлек төсегі бар стандартты бөлме"),
        ("Standard Triple", 90.0, 110.0, 3, 0, "Үш адамдық кең стандартты нөмір"),
        ("Deluxe King", 110.0, 140.0, 2, 1, "Үлкен корольдік төсегі және керемет балконы бар Deluxe нөмір"),
        ("Deluxe Ocean View", 140.0, 180.0, 2, 1, "Теңізге қарайтын панорамалық көрінісі мен балконы бар Deluxe"),
        ("Deluxe Quiet Zone", 125.0, 155.0, 2, 1, "Қонақүйдің ең тыныш аймағында орналасқан демалыс бөлмесі"),
        ("Suite Family", 200.0, 260.0, 4, 1, "Үлкен отбасыға арналған кең люкс нөмір, балконы бар"),
        ("Executive Suite", 270.0, 350.0, 3, 1, "Бизнес саяхатшыларға арналған жоғары деңгейдегі премиум люкс"),
        ("Presidential Suite", 450.0, 600.0, 5, 1, "Жеке террасасы мен барлық элитті жағдайлары бар президенттік нөмір")
    ]
    
    views = ["Көше жаққа қарайтын терезе", "Ішкі аулаға көрініс", "Қала орталығына бағытталған панорама", "Саябаққа қарайтын тыныш терезе"]
    amenities = ["кондиционер, Wi-Fi және сейф бар", "шағын тоңазытқыш пен жұмыс үстелімен жабдықталған", "умный дом жүйесі қосылған", "жылытылатын едені бар жайлы бөлме"]

    sample_rooms = []
    room_number = 101  # 101-ден 200-ге дейін
    
    while room_number <= 200:
        cat_index = (room_number - 101) % len(room_categories)
        base = room_categories[cat_index]
        
        r_type = f"{room_number} комната ({base[0]})"
        price = round(base[1] + (((room_number * 7) % 35)), 2)
        capacity = base[3]
        balcony = 1 if base[4] == 1 or (room_number % 2 == 0) else 0
        
        # Әр бөлмеге әртүрлі уникaлды сипаттама құрастыру
        v_choice = views[room_number % len(views)]
        a_choice = amenities[(room_number * 3) % len(amenities)]
        balc_text = "Жеке балконы бар." if balcony == 1 else "Балконы жоқ."
        
        desc = f"{base[5]}. {v_choice}. Ішінде {a_choice}. {balc_text}"
            
        sample_rooms.append((r_type, price, capacity, balcony, desc))
        room_number += 1

    cursor.executemany('''
        INSERT INTO rooms (room_type, price_per_night, capacity, has_balcony, description)
        VALUES (?, ?, ?, ?, ?)
    ''', sample_rooms)
    conn.commit()
    conn.close()

def get_rooms():
    init_db()
    conn = sqlite3.connect('hotel_system.db')
    df = pd.read_sql_query("SELECT * FROM rooms", conn)
    conn.close()
    return df

df = get_rooms()

# 2. Пайдаланушы енгізу жолағы
st.subheader("🤖 ИИ Смарт Іздеу Ассистенті")
user_query = st.text_input(
    "Қажеттілігіңізді толық жазыңыз:", 
    placeholder="Мысалы: 105 комната, 4 адамдық, арзан бөлме, балконы жоқ"
)

# Бастапқы DataFrame
filtered = df.copy()

# 3. Мәтінді талдау логикасы (NLP Parser)
if user_query:
    q = user_query.lower()
    
    # Бөлме нөмірін іздеу
    room_num_match = re.search(r'(\d{3})', q)
    if room_num_match:
        target_num = room_num_match.group(1)
        filtered = filtered[filtered['room_type'].str.contains(target_num)]
    
    # Адам санын анықтау
    capacity_match = re.search(r'(\d+)\s*(адам|орын|кісі)', q)
    if capacity_match:
        cap_val = int(capacity_match.group(1))
        filtered = filtered[filtered['capacity'] >= cap_val]
    
    # «Арзан» немесе «бюджетті» сөздерін түсіну
    if 'арзан' in q or 'бюджет' in q or 'тиімді' in q:
        filtered = filtered[filtered['price_per_night'] <= 70]
        
    # «Қымбат» немесе «люкс» сөздерін түсіну
    elif 'қымбат' in q or 'люкс' in q or 'премиум' in q:
        filtered = filtered[filtered['price_per_night'] >= 200]

    # Бағаны санмен көрсеткенді талдау
    price_match = re.search(r'(\d+)\s*(\$|доллар|тенге|тг)', q)
    if price_match:
        price_val = float(price_match.group(1))
        if 'кем' in q or 'арзан' in q or 'ден төмен' in q or 'до' in q:
            filtered = filtered[filtered['price_per_night'] <= price_val]

    # Балкон шарттарын қатаң тексеру
    if 'балконы жоқ' in q or 'балконсыз' in q or 'балкон жоқ' in q:
        filtered = filtered[filtered['has_balcony'] == 0]
    elif 'балконы бар' in q or ('балкон' in q and 'жоқ' not in q):
        filtered = filtered[filtered['has_balcony'] == 1]
        
    # Тыныш аймақ шарты
    if 'тыныш' in q or 'демалу' in q:
        filtered = filtered[filtered['description'].str.lower().str.contains('тыныш|демалу')]

st.write(f"### 🎯 Сіздің сұрауыңызға сай табылған нөмірлер ({len(filtered)}):")

if not filtered.empty:
    display_df = filtered.copy()
    display_df['has_balcony'] = display_df['has_balcony'].apply(lambda x: 'Иә' if x == 1 else 'Жоқ')
    st.dataframe(display_df[['room_type', 'price_per_night', 'capacity', 'has_balcony', 'description']], use_container_width=True)
else:
    st.warning("Өкінішке қарай, бұл талаптарға сай ешқандай нөмір табылмады. Басқаша сипаттап көріңіз!")
