import streamlit as st
import sqlite3
import pandas as pd
import re
import hashlib

# Беттің конфигурациясы
st.set_page_config(page_title="TRYP by Wyndham — Отель Брондау", page_icon="🏨", layout="wide")

# Заманауи Премиум CSS стильдер (Glassmorphism және тазартылган дизайн)
st.markdown("""
    <style>
    .stApp {
        background: linear-gradient(135deg, #0d1117 0%, #161b22 100%);
        color: #e6edf3;
    }
    
    /* Бүйірлік панельді әдемілеу */
    [data-testid="stSidebar"] {
        background-color: #11141d;
        border-right: 1px solid #30363d;
    }

    /* Басты тақырыпқа градиент беру */
    .main-title {
        font-size: 2.5rem;
        font-weight: 800;
        background: linear-gradient(90deg, #58a6ff, #1f6feb);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0px;
    }
    
    .sub-text {
        color: #8b949e;
        font-size: 1.1rem;
        margin-bottom: 25px;
    }

    /* Қонақүй нөмірінің карточкасы */
    .room-card {
        background: rgba(22, 27, 34, 0.7);
        backdrop-filter: blur(10px);
        border: 1px solid #30363d;
        border-radius: 14px;
        padding: 22px;
        margin-bottom: 20px;
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
        transition: transform 0.2s ease, border-color 0.2s ease;
    }
    
    .room-card:hover {
        border-color: #58a6ff;
        transform: translateY(-3px);
    }

    .room-title {
        font-size: 1.35rem;
        font-weight: 700;
        color: #58a6ff;
        margin-bottom: 8px;
    }

    .room-desc {
        color: #c9d1d9;
        font-size: 0.95rem;
        margin-bottom: 15px;
        line-height: 1.5;
    }

    .badge-price {
        background-color: #238636;
        color: white;
        padding: 6px 12px;
        border-radius: 20px;
        font-weight: 600;
        font-size: 0.9rem;
    }

    .badge-info {
        background-color: #21262d;
        color: #8b949e;
        padding: 6px 12px;
        border-radius: 20px;
        font-size: 0.85rem;
        border: 1px solid #30363d;
    }

    /* Батырмалар дизайны */
    div.stButton > button {
        background: linear-gradient(90deg, #238636, #2ea043);
        color: white;
        border-radius: 8px;
        border: none;
        padding: 10px 20px;
        font-weight: 600;
        width: 100%;
        box-shadow: 0 4px 12px rgba(35, 134, 54, 0.3);
        transition: all 0.3s ease;
    }
    
    div.stButton > button:hover {
        background: linear-gradient(90deg, #2ea043, #3fb950);
        box-shadow: 0 6px 16px rgba(46, 160, 67, 0.5);
        color: #fff;
    }

    /* Құлыпталған батырма стилі */
    div.stButton > button:disabled {
        background: #21262d !important;
        color: #8b949e !important;
        border: 1px solid #30363d;
        box-shadow: none;
    }
    </style>
""", unsafe_allow_html=True)

# 1. Дерекқорды инициализациялау (Нөмірлер, Қолданушылар, Брондаулар)
def init_db():
    conn = sqlite3.connect('hotel_system.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            full_name TEXT NOT NULL,
            phone TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            room_type TEXT NOT NULL,
            price REAL NOT NULL,
            booking_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='rooms'")
    if not cursor.fetchone():
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
            ("Standard Single", 40.0, 1, 0, "Бір адамға арналған ықшам және заманауи жайлы стандартты нөмір"),
            ("Standard Double", 60.0, 2, 0, "Екі адамға арналған жарық және таза стандартты нөмір"),
            ("Standard Twin", 65.0, 2, 0, "Екі бөлек төсегі бар жайлы стандартты бөлме"),
            ("Standard Triple", 85.0, 3, 0, "Үш адамдық кең стандартты нөмір"),
            ("Deluxe King", 110.0, 2, 1, "Үлкен корольдік төсегі және панорамалық балконы бар Deluxe нөмір"),
            ("Deluxe Ocean View", 140.0, 2, 1, "Әсем көрінісі мен жеке балконы бар элиталық Deluxe"),
            ("Deluxe Quiet Zone", 125.0, 2, 1, "Қонақүйдің ең тыныш әрі жайлы аймағында орналасқан нөмір"),
            ("Suite Family", 180.0, 4, 1, "Үлкен отбасыға арналған кең люкс нөмір, жеке терассасы бар"),
            ("Executive Suite", 250.0, 3, 1, "Бизнес саяхатшыларға арналған жоғары деңгейдегі премиум люкс"),
            ("Presidential Suite", 380.0, 5, 1, "Президенттік деңгейдегі сәнді террасасы мен люкс жағдайлары бар нөмір")
        ]
        
        views = ["Көше жаққа қарайтын панорамалық терезе", "Ішкі жасыл аулаға әдемі көрініс", "Қала орталығына бағытталған көрініс", "Саябаққа қарайтын тыныш терезе"]
        amenities = ["кондиционер, Wi-Fi және сейф бар", "шағын тоңазытқыш пен жұмыс үстелімен жабдықталған", "ақылды үй жүйесі мен дауыстық көмекші қосылған", "жылытылатын едені бар премиум бөлме"]

        sample_rooms = []
        for floor in range(1, 11):
            for room_idx in range(1, 11):
                room_number = floor * 100 + room_idx if floor < 10 else 1000 + room_idx
                cat_index = (room_idx - 1) % len(room_categories)
                base = room_categories[cat_index]
                
                floor_extra = (floor - 1) * 18.0
                if floor == 10:
                    floor_extra += 120.0
                    
                price = round(base[1] + floor_extra + ((room_number * 3) % 15), 2)
                floor_name = f"{floor}-ші қабат" if floor < 10 else "10-ші қабат (Пентхаус)"
                r_type = f"{room_number} комната ({base[0]})"
                capacity = base[2]
                balcony = 1 if base[3] == 1 or (floor >= 3) else 0 
                
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

init_db()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# 2. Сессия күйлерін басқару
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""
if "full_name" not in st.session_state:
    st.session_state.full_name = ""
if "chat_query" not in st.session_state:
    st.session_state.chat_query = ""

def get_rooms():
    conn = sqlite3.connect('hotel_system.db')
    df = pd.read_sql_query("SELECT * FROM rooms", conn)
    conn.close()
    return df

df = get_rooms()

# 3. БҮЙІРЛІК ПАНЕЛЬ — Авторизация және ИИ Ассистент
st.sidebar.markdown("## 👤 Жеке Кабинет")

if not st.session_state.logged_in:
    auth_mode = st.sidebar.radio("Мәзір:", ["Кіру", "Тіркелу"])
    
    if auth_mode == "Тіркелу":
        st.sidebar.subheader("Жаңа аккаунт ашу")
        reg_user = st.sidebar.text_input("Логин (Email немесе Nick):", key="reg_u")
        reg_pass = st.sidebar.text_input("Құпия сөз:", type="password", key="reg_p")
        reg_name = st.sidebar.text_input("Аты-жөніңіз:", key="reg_n")
        reg_phone = st.sidebar.text_input("Телефон нөміріңіз:", key="reg_ph")
        
        if st.sidebar.button("Тіркелуді аяқтау"):
            if reg_user and reg_pass and reg_name:
                conn = sqlite3.connect('hotel_system.db')
                cursor = conn.cursor()
                try:
                    cursor.execute("INSERT INTO users (username, password, full_name, phone) VALUES (?, ?, ?, ?)",
                                   (reg_user, hash_password(reg_pass), reg_name, reg_phone))
                    conn.commit()
                    st.sidebar.success("✅ Сәтті тіркелдіңіз! Енді 'Кіру' арқылы кіріңіз.")
                except sqlite3.IntegrityError:
                    st.sidebar.error("⚠ Бұл логин қазірдің өзінде тіркелген!")
                conn.close()
            else:
                st.sidebar.warning("Барлық міндетті өрістерді толтырыңыз!")
    else:
        st.sidebar.subheader("Аккаунтқа кіру")
        log_user = st.sidebar.text_input("Логин:", key="log_u")
        log_pass = st.sidebar.text_input("Құпия сөз:", type="password", key="log_p")
        
        if st.sidebar.button("Жүйеге кіру"):
            conn = sqlite3.connect('hotel_system.db')
            cursor = conn.cursor()
            cursor.execute("SELECT full_name, password FROM users WHERE username = ?", (log_user,))
            user = cursor.fetchone()
            conn.close()
            
            if user and user[1] == hash_password(log_pass):
                st.session_state.logged_in = True
                st.session_state.username = log_user
                st.session_state.full_name = user[0]
                st.sidebar.success(f"Қош келдіңіз, {user[0]}!")
                st.rerun()
            else:
                st.sidebar.error("❌ Логин немесе пароль қате!")
else:
    st.sidebar.success(f"Қош келдіңіз, **{st.session_state.full_name}**!")
    
    st.sidebar.markdown("### 📋 Менің брондауларым:")
    conn = sqlite3.connect('hotel_system.db')
    user_bookings = pd.read_sql_query("SELECT room_type, price, booking_date FROM bookings WHERE username = ?", conn, params=(st.session_state.username,))
    conn.close()
    
    if not user_bookings.empty:
        for idx, row in user_bookings.iterrows():
            st.sidebar.info(f"🛏️ **{row['room_type']}**\n💰 Бағасы: ${row['price']}\n📅 Күні: {row['booking_date'][:10]}")
    else:
        st.sidebar.write("Әзірге брондалған нөмірлеріңіз жоқ.")
        
    if st.sidebar.button("Шығу (Logout)"):
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.session_state.full_name = ""
        st.rerun()

st.sidebar.markdown("---")
st.sidebar.markdown("## 🤖 ИИ Ассистент Чаты")
st.sidebar.write("Іздеу талабын жазыңыз (мысалы: *'1-ші қабат'*, *'пентхаус'*, *'4 адамға'*, *'арзан'*):")

user_input = st.sidebar.text_input("Сұраныс енгізу:", value=st.session_state.chat_query)

col_b1, col_b2 = st.sidebar.columns(2)
with col_b1:
    if st.button("Іздеу"):
        st.session_state.chat_query = user_input
with col_b2:
    if st.button("Тазарту"):
        st.session_state.chat_query = ""
        st.rerun()

st.sidebar.markdown("---")
st.sidebar.markdown("### 🎛️ Қосымша сүзгілер")
filter_balcony = st.sidebar.selectbox("Балкон жағдайы:", ["Барлығы", "Балконы бар", "Балконы жоқ"])
max_price = st.sidebar.slider("Максималды баға ($):", 40, 850, 850)

# 4. НЕГІЗГІ БЕТ — Бөлмелер каталогы
st.markdown('<p class="main-title">🏨 TRYP Hotel — Брондау жүйесі</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-text">Барлық 100 заманауи нөмір қабаттар мен категориялар бойынша реттелген.</p>', unsafe_allow_html=True)

filtered = df[df['price_per_night'] <= max_price]

if filter_balcony == "Балконы бар":
    filtered = filtered[filtered['has_balcony'] == 1]
elif filter_balcony == "Балконы жоқ":
    filtered = filtered[filtered['has_balcony'] == 0]

active_query = st.session_state.chat_query.lower()
if active_query:
    if 'пентхаус' in active_query:
        filtered = filtered[filtered['description'].str.lower().str.contains('пентхаус') | filtered['room_type'].str.contains('10')]
    else:
        floor_match = re.search(r'(\d+)\s*(-ші|-нші|ші|нші)?\s*қабат', active_query)
        if floor_match:
            floor_num = int(floor_match.group(1))
            if 1 <= floor_num <= 9:
                valid_rooms = [f"{floor_num}0{i}" for i in range(1, 10)] + [f"{floor_num}10"]
                pattern = "|".join(valid_rooms)
                filtered = filtered[filtered['room_type'].str.contains(pattern)]
            elif floor_num == 10:
                valid_rooms = [f"100{i}" for i in range(1, 10)] + ["1010"]
                pattern = "|".join(valid_rooms)
                filtered = filtered[filtered['room_type'].str.contains(pattern)]

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

st.markdown(f"### 🎯 Табылған нөмірлер саны: **{len(filtered)}**")
st.markdown("---")

# 5. Нөмірлерді заманауи карточкалар түрінде шығару
if not filtered.empty:
    cols = st.columns(2)
    for index, row in filtered.reset_index().iterrows():
        col = cols[index % 2]
        with col:
            balc_status = "Иә 🌅" if row['has_balcony'] == 1 else "Жоқ ❌"
            
            # HTML карточка арқылы әдемі дизайн құру
            st.markdown(f"""
                <div class="room-card">
                    <div class="room-title">🛏️ {row['room_type']}</div>
                    <div class="room-desc"><b>Сипаттамасы:</b> {row['description']}</div>
                    <div style="display: flex; gap: 10px; margin-bottom: 15px;">
                        <span class="badge-price">💰 ${row['price_per_night']} / түн</span>
                        <span class="badge-info">👥 {row['capacity']} адам</span>
                        <span class="badge-info">🌅 Балкон: {balc_status}</span>
                    </div>
                </div>
            """, unsafe_allow_html=True)
            
            # Брондау батырмасы (Тіркелмегендер үшін жабық)
            if st.session_state.logged_in:
                if st.button(f"Брондау ({row['room_type']})", key=f"book_{row['id']}"):
                    conn = sqlite3.connect('hotel_system.db')
                    cursor = conn.cursor()
                    cursor.execute("INSERT INTO bookings (username, room_type, price) VALUES (?, ?, ?)",
                                   (st.session_state.username, row['room_type'], row['price_per_night']))
                    conn.commit()
                    conn.close()
                    st.success(f"🎉 Құттықтаймыз, {st.session_state.full_name}! Сіз **{row['room_type']}** нөмірін сәтті брондадыңыз.")
            else:
                st.button(f"🔒 Брондау үшін жүйеге кіріңіз", key=f"disabled_{row['id']}", disabled=True)
else:
    st.warning("Өкінішке қарай, бұл талаптарға сай ешқандай нөмір табылмады. Іздеу шарттарын өзгертіп көріңіз.")
