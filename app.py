import streamlit as st
import sqlite3
import pandas as pd
import re

# Беттің конфигурациясы (кең форматта ашылуы үшін)
st.set_page_config(page_title="Отель Брондау жүйесі", page_icon="🏨", layout="wide")

# Стильдер мен дизайнды әдемілеу
st.markdown("""
    <style>
    .room-card {
        padding: 20px;
        border-radius: 10px;
        border: 1px solid #e0e0e0;
        margin-bottom: 15px;
        background-color: #f9f9f9;
    }
    </style>
""", unsafe_allow_html=True)

st.title("🏨 Smart Hotel — ИИ Нөмір Брондау Жүйесі")
st.write("Қажетті бөлмені еркін тілде сипаттап іздеңіз немесе төмендегі сүзгілерді қолданыңыз.")

# 1. 100 нөмірді генерациялау базасы
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
    amenities = ["кондиционер, Wi-Fi және сейф бар", "шағын тоңазытқыш пен жұмыс үстелімен жабдықталған", "ақылды үй жүйесі қосылған", "жылытылатын едені бар жайлы бөлме"]

    sample_rooms = []
    room_number = 101  
    
    while room_number <= 200:
        cat_index = (room_number - 101) % len(room_categories)
        base = room_categories[cat_index]
        
        r_type = f"{room_number} комната ({base[0]})"
        price = round(base[1] + (((room_number * 7) % 35)), 2)
        capacity = base[3]
        balcony = 1 if base[4] == 1 or (room_number % 2 == 0) else 0
        
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

# 2. Бүйірлік панель (Sidebar) — қосымша фильтрлер
st.sidebar.header("🎛️ Қосымша сүзгілер")
filter_balcony = st.sidebar.selectbox("Балкон жағдайы:", ["Барлығы", "Балконы бар", "Балконы жоқ"])
max_sidebar_price = st.sidebar.slider("Максималды баға ($):", 40, 650, 650)

# 3. Негізгі ИИ Іздеу жолағы
st.subheader("🤖 ИИ Смарт Іздеу Ассистенті")
user_query = st.text_input(
    "Іздеген нөміріңізді немесе талабыңызды жазыңыз:", 
    placeholder="Мысалы: 105 комната, 4 адамдық, арзан бөлме, балконы жоқ"
)

# Бастапқы сүзу
filtered = df[df['price_per_night'] <= max_sidebar_price]

if filter_balcony == "Балконы бар":
    filtered = filtered[filtered['has_balcony'] == 1]
elif filter_balcony == "Балконы жоқ":
    filtered = filtered[filtered['has_balcony'] == 0]

# NLP Логика (Мәтінді талдау)
if user_query:
    q = user_query.lower()
    
    room_num_match = re.search(r'(\d{3})', q)
    if room_num_match:
        target_num = room_num_match.group(1)
        filtered = filtered[filtered['room_type'].str.contains(target_num)]
    
    capacity_match = re.search(r'(\d+)\s*(адам|орын|кісі)', q)
    if capacity_match:
        cap_val = int(capacity_match.group(1))
        filtered = filtered[filtered['capacity'] >= cap_val]
    
    if 'арзан' in q or 'бюджет' in q or 'тиімді' in q:
        filtered = filtered[filtered['price_per_night'] <= 80]
    elif 'қымбат' in q or 'люкс' in q or 'премиум' in q:
        filtered = filtered[filtered['price_per_night'] >= 200]

    price_match = re.search(r'(\d+)\s*(\$|доллар|тенге|тг)', q)
    if price_match:
        price_val = float(price_match.group(1))
        if 'кем' in q or 'арзан' in q or 'ден төмен' in q or 'до' in q:
            filtered = filtered[filtered['price_per_night'] <= price_val]

    if 'балконы жоқ' in q or 'балконсыз' in q or 'балкон жоқ' in q:
        filtered = filtered[filtered['has_balcony'] == 0]
    elif 'балконы бар' in q or ('балкон' in q and 'жоқ' not in q):
        filtered = filtered[filtered['has_balcony'] == 1]
        
    if 'тыныш' in q or 'демалу' in q:
        filtered = filtered[filtered['description'].str.lower().str.contains('тыныш|демалу')]

st.write(f"### 🎯 Табылған нөмірлер саны: {len(filtered)}")

# 4. Нөмірлерді ыңғайлы Карточкалар (Cards) түрінде көрсету
if not filtered.empty:
    # 2 бағанды сетка жасау
    cols = st.columns(2)
    for index, row in filtered.reset_index().iterrows():
        col = cols[index % 2]
        with col:
            with st.container(border=True):
                st.subheader(f"🛏️ {row['room_type']}")
                st.write(f"**Сипаттамасы:** {row['description']}")
                
                # Метрикалық көрсеткіштер
                m1, m2, m3 = st.columns(3)
                m1.metric("Бағасы", f"${row['price_per_night']}")
                m2.metric("Сиымдылығы", f"{row['capacity']} адам")
                balc_status = "Иә 🌅" if row['has_balcony'] == 1 else "Жоқ ❌"
                m3.metric("Балкон", balc_status)
                
                if st.button(f"Брондау ({row['room_type']})", key=f"book_{row['id']}:"):
                    st.success(f"🎉 Құттықтаймыз! Сіз сәтті түрде **{row['room_type']}** нөмірін брондадыңыз!")
else:
    st.warning("Өкінішке қарай, бұл талаптарға сай ешқандай нөмір табылмады. Іздеу шарттарын өңгеріп көріңіз.")
