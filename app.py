import streamlit as st
import sqlite3
import pandas as pd
import re

# Конфигурация страницы
st.set_page_config(page_title="TRYP by Wyndham — Отель Брондау", page_icon="🏨", layout="wide")

# Исправленные CSS-стили для идеальной видимости текста и карточек
st.markdown("""
    <style>
    /* Шапка сайта */
    .header-container {
        background-color: #111e38;
        padding: 15px 25px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        border-radius: 8px;
        margin-bottom: 25px;
        color: white;
    }
    .nav-links {
        display: flex;
        gap: 25px;
        font-size: 14px;
        font-weight: 600;
        color: white;
    }
    
    /* Блоки преимуществ */
    .amenity-box {
        background: #111e38;
        color: white;
        padding: 15px;
        border-radius: 8px;
        text-align: center;
        font-size: 14px;
        font-weight: 500;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }

    /* Принудительный белый фон и темный текст для карточек номеров, чтобы текст не пропадал */
    div[data-testid="stVerticalBlock"] > div.stElementContainer div[data-testid="stContainer"] {
        background-color: #ffffff !important;
        color: #111e38 !important;
        padding: 20px;
        border-radius: 10px;
        border: 1px solid #dcdcdc;
        box-shadow: 0 4px 10px rgba(0,0,0,0.05);
    }
    
    /* Стили кнопок бронирования */
    div.stButton > button {
        background-color: #111e38;
        color: white;
        border-radius: 6px;
        border: none;
        padding: 8px 16px;
        font-weight: 600;
        width: 100%;
        transition: 0.3s;
    }
    div.stButton > button:hover {
        background-color: #1f365c;
        color: #fff;
    }
    </style>
""", unsafe_allow_html=True)

# Верхняя панель бренда
st.markdown("""
    <div class="header-container">
        <div style="font-weight: 800; font-size: 20px; letter-spacing: 1px;">🏨 TRYP HOTEL</div>
        <div class="nav-links">
            <span style="color: #4da6ff; cursor:pointer;">НОМЕРА</span>
            <span style="cursor:pointer; opacity: 0.8;">РЕСТОРАНЫ</span>
            <span style="cursor:pointer; opacity: 0.8;">УДОБСТВА</span>
            <span style="cursor:pointer; opacity: 0.8;">СПЕЦПРЕДЛОЖЕНИЯ</span>
            <span style="cursor:pointer; opacity: 0.8;">КОНТАКТЫ</span>
        </div>
    </div>
""", unsafe_allow_html=True)

# 1. Генерация 100 номеров по этажам с нарастающей ценой
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
        ("Standard Single", 45.0, 1, 0, "Бір адамға арналған ықшам және жайлы стандартты нөмір"),
        ("Standard Double", 65.0, 2, 0, "Екі адамға арналған жарық және таза стандартты нөмір"),
        ("Standard Twin", 70.0, 2, 0, "Екі бөлек төсегі бар стандартты бөлме"),
        ("Standard Triple", 90.0, 3, 0, "Үш адамдық кең стандартты нөмір"),
        ("Deluxe King", 120.0, 2, 1, "Үлкен корольдік төсегі және керемет балконы бар Deluxe нөмір"),
        ("Deluxe Ocean View", 150.0, 2, 1, "Панорамалық көрінісі мен жеке балконы бар Deluxe"),
        ("Deluxe Quiet Zone", 130.0, 2, 1, "Қонақүйдің ең тыныш аймағында орналасқан демалыс бөлмесі"),
        ("Suite Family", 190.0, 4, 1, "Үлкен отбасыға арналған кең люкс нөмір, балконы бар"),
        ("Executive Suite", 260.0, 3, 1, "Бизнес саяхатшыларға арналған жоғары деңгейдегі премиум люкс"),
        ("Presidential Suite", 420.0, 5, 1, "Жеке террасасы мен элитті жағдайлары бар президенттік нөмір")
    ]
    
    views = ["Көше жаққа қарайтын терезе", "Ішкі аулаға әдемі көрініс", "Қала орталығына бағытталған панорама", "Саябаққа қарайтын тыныш терезе"]
    amenities = ["кондиционер, Wi-Fi және сейф бар", "шағын тоңазытқыш пен жұмыс үстелімен жабдықталған", "ақылды үй жүйесі қосылған", "жылытылатын едені бар жайлы бөлме"]

    sample_rooms = []
    
    for floor in range(1, 11):
        for room_idx in range(1, 11):
            room_number = floor * 100 + room_idx if floor < 10 else 1000 + room_idx
            
            cat_index = (room_idx - 1) % len(room_categories)
            base = room_categories[cat_index]
            
            floor_extra = (floor - 1) * 7.0
            price = round(base[1] + floor_extra + ((room_number * 3) % 12), 2)
            
            floor_name = f"{floor}-ші қабат" if floor < 10 else "10-ші қабат (Пентхаус)"
            r_type = f"{room_number} комната ({base[0]})"
            capacity = base[2]
            balcony = 1 if base[3] == 1 or (floor >= 4) else 0 
            
            v_choice = views[room_number % len(views)]
            a_choice = amenities[(room_number * 3) % len(amenities)]
            balc_text = "Жеке балконы бар 🌅." if balcony == 1 else "Балконы жоқ ❌."
            
            desc = f"{floor_name}. {base[4]}. {v_choice}. Ішінде {a_choice}. {balc_text}"
                
            sample_rooms.append((r_type, price, capacity, balcony, desc))

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

# Верхние иконки преимуществ
ac1, ac2, ac3, ac4 = st.columns(4)
with ac1:
    st.markdown('<div class="amenity-box">📶 Тегін High-Speed Wi-Fi</div>', unsafe_allow_html=True)
with ac2:
    st.markdown('<div class="amenity-box">👑 VIP Қызмет көрсету</div>', unsafe_allow_html=True)
with ac3:
    st.markdown('<div class="amenity-box">🍳 Таңғы ас кіреді</div>', unsafe_allow_html=True)
with ac4:
    st.markdown('<div class="amenity-box">🕒 Заезд 14:00 / Выезд 12:00</div>', unsafe_allow_html=True)

st.markdown("---")

if "chat_query" not in st.session_state:
    st.session_state.chat_query = ""

# БОКОВАЯ ПАНЕЛЬ — ИИ Ассистент чат и фильтры
st.sidebar.markdown("## 🤖 ИИ Ассистент Чаты")
st.sidebar.write("Қажеттілігіңізді жазыңыз (мысалы: *'1-ші қабат'*, *'9 қабат'*, *'105 комната'*, *'арзан'*):")

user_input = st.sidebar.text_input("Сұраныс енгізу:", value=st.session_state.chat_query)

if st.sidebar.button("Іздеуді орындау"):
    st.session_state.chat_query = user_input

if st.sidebar.button("Барлық бөлмелерді көрсету"):
    st.session_state.chat_query = ""
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.markdown("### 🎛️ Қосымша сүзгілер")
filter_balcony = st.sidebar.selectbox("Балкон жағдайы:", ["Барлығы", "Балконы бар", "Балконы жоқ"])
max_price = st.sidebar.slider("Максималды баға ($):", 40, 750, 750)

# ОСНОВНОЙ КОНТЕНТ
st.markdown("### 🛏️ Қонақүй нөмірлері (101 — 1010)")
st.write("Барлық 100 заманауи нөмір қабаттар бойынша реттелген. Жоғары қабаттарға қарай баға біртіндеп өседі.")

filtered = df[df['price_per_night'] <= max_price]

if filter_balcony == "Балконы бар":
    filtered = filtered[filtered['has_balcony'] == 1]
elif filter_balcony == "Балконы жоқ":
    filtered = filtered[filtered['has_balcony'] == 0]

active_query = st.session_state.chat_query.lower()
if active_query:
    floor_match = re.search(r'(\d+)\s*(-ші|-нші|ші|нші)?\s*қабат', active_query)
    if floor_match:
        floor_num = floor_match.group(1)
        if floor_num == '1':
            filtered = filtered[filtered['room_type'].str.contains(r'10[1-9]|110')]
        elif floor_num == '2':
            filtered = filtered[filtered['room_type'].str.contains(r'20[1-9]|210')]
        elif floor_num == '3':
            filtered = filtered[filtered['room_type'].str.contains(r'30[1-9]|310')]
        elif floor_num == '4':
            filtered = filtered[filtered['room_type'].str.contains(r'40[1-9]|410')]
        elif floor_num == '5':
            filtered = filtered[filtered['room_type'].str.contains(r'50[1-9]|510')]
        elif floor_num == '6':
            filtered = filtered[filtered['room_type'].str.contains(r'60[1-9]|610')]
        elif floor_num == '7':
            filtered = filtered[filtered['room_type'].str.contains(r'70[1-9]|710')]
        elif floor_num == '8':
            filtered = filtered[filtered['room_type'].str.contains(r'80[1-9]|810')]
        elif floor_num == '9':
            filtered = filtered[filtered['room_type'].str.contains(r'90[1-9]|910')]
        elif floor_num == '10':
            filtered = filtered[filtered['room_type'].str.contains(r'100[1-9]|1010')]

    room_num_match = re.search(r'(\d{3,4})', active_query)
    if room_num_match and not floor_match:
        target_num = room_num_match.group(1)
        filtered = filtered[filtered['room_type'].str.contains(target_num)]
    
    capacity_match = re.search(r'(\d+)\s*(адам|орын|кісі)', active_query)
    if capacity_match:
        cap_val = int(capacity_match.group(1))
        filtered = filtered[filtered['capacity'] >= cap_val]
    
    if 'арзан' in active_query or 'бюджет' in active_query or 'тиімді' in active_query:
        filtered = filtered[filtered['price_per_night'] <= 90]
    elif 'қымбат' in active_query or 'люкс' in active_query or 'премиум' in active_query:
        filtered = filtered[filtered['price_per_night'] >= 200]

    if 'балконы жоқ' in active_query or 'балконсыз' in active_query or 'балкон жоқ' in active_query:
        filtered = filtered[filtered['has_balcony'] == 0]
    elif 'балконы бар' in active_query or ('балкон' in active_query and 'жоқ' not in active_query):
        filtered = filtered[filtered['has_balcony'] == 1]
        
    st.info(f"🤖 ИИ Ассистент талдады: «{st.session_state.chat_query}» бойынша нөмірлер сүзілді.")

st.write(f"### 🎯 Табылған нөмірлер саны: {len(filtered)}")

# Вывод карточек номеров
if not filtered.empty:
    cols = st.columns(2)
    for index, row in filtered.reset_index().iterrows():
        col = cols[index % 2]
        with col:
            with st.container(border=True):
                # Дополнительная обертка для темного текста внутри белой карточки
                st.markdown(f"<h3 style='color: #111e38; margin-bottom: 5px;'>🛏️ {row['room_type']}</h3>", unsafe_allow_html=True)
                st.markdown(f"<p style='color: #333333;'><b>Сипаттамасы:</b> {row['description']}</p>", unsafe_allow_html=True)
                
                m1, m2, m3 = st.columns(3)
                m1.metric("Бағасы", f"${row['price_per_night']}")
                m2.metric("Сиымдылығы", f"{row['capacity']} адам")
                balc_status = "Иә 🌅" if row['has_balcony'] == 1 else "Жоқ ❌"
                m3.metric("Балкон", balc_status)
                
                if st.button(f"Брондау ({row['room_type']})", key=f"book_{row['id']}"):
                    st.success(f"🎉 Құттықтаймыз! Сіз сәтті түрде **{row['room_type']}** нөмірін брондадыңыз!")
else:
    st.warning("Өкінішке қарай, бұл талаптарға сай ешқандай нөмір табылмады. Іздеу шарттарын өзгертіп көріңіз.")
