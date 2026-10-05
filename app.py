import streamlit as st
import sqlite3
import pandas as pd
import re
import hashlib

# Беттің конфигурациясы
st.set_page_config(page_title="TRYP by Wyndham — Отель Брондау", page_icon="🏨", layout="wide")

# CSS стильдер (Қараңғы режимге ыңғайлы карточкалар мен дизайн)
st.markdown("""
    <style>
    .stApp {
        background-color: #0e1117;
    }
    
    /* Бөлме карточкаларының дизайны */
    div[data-testid="stVerticalBlock"] > div.stElementContainer div[data-testid="stContainer"] {
        background-color: #161b22 !important;
        color: #ffffff !important;
        padding: 20px;
        border-radius: 10px;
        border: 1px solid #30363d;
        box-shadow: 0 4px 10px rgba(0,0,0,0.3);
    }
    
    /* Батырмалардың дизайны */
    div.stButton > button {
        background-color: #238636;
        color: white;
        border-radius: 6px;
        border: none;
        padding: 8px 16px;
        font-weight: 600;
        width: 100%;
        transition: 0.3s;
    }
    div.stButton > button:hover {
        background-color: #2ea043;
        color: #fff;
    }
    </style>
""", unsafe_allow_html=True)

# 1. Дерекқорды инициализациялау (Нөмірлер, Қолданушылар, Брондаулар)
def init_db():
    conn = sqlite3.connect('hotel_system.db')
    cursor = conn.cursor()
    
    # Қолданушылар кестесі
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            full_name TEXT NOT NULL,
            phone TEXT
        )
    ''')
    
    # Брондаулар кестесі
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            room_type TEXT NOT NULL,
            price REAL NOT NULL,
            booking_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Нөмірлер кестесі бар-жоғын тексеру
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
            ("Standard Single", 40.0, 1, 0, "Бір адамға арналған ықшам және жайлы стандартты нөмір"),
            ("Standard Double", 60.0, 2, 0, "Екі адамға арналған жарық және таза стандартты нөмір"),
            ("Standard Twin", 65.0, 2, 0, "Екі бөлек төсегі бар стандартты бөлме"),
            ("Standard Triple", 85.0, 3, 0, "Үш адамдық кең стандартты нөмір"),
            ("Deluxe King", 110.0, 2, 1, "Үлкен корольдік төсегі және керемет балконы бар Deluxe нөмір"),
            ("Deluxe Ocean View", 140.0, 2, 1, "Панорамалық көрінісі мен жеке балконы бар Deluxe"),
            ("Deluxe Quiet Zone", 125.0, 2, 1, "Қонақүйдің ең тыныш аймағында орналасқан демалыс бөлмесі"),
            ("Suite Family", 180.0, 4, 1, "Үлкен отбасыға арналған кең люкс нөмір, балконы бар"),
            ("Executive Suite", 250.0, 3, 1, "Бизнес саяхатшыларға арналған жоғары деңгейдегі премиум люкс"),
            ("Presidential Suite", 380.0, 5, 1, "Жеке террасасы мен элитті жағдайлары бар президенттік нөмір")
        ]
        
        views = ["Көше жаққа қарайтын терезе", "Ішкі аулаға әдемі көрініс", "Қала орталығына бағытталған панорама", "Саябаққа қарайтын тыныш терезе"]
        amenities = ["кондиционер, Wi-Fi және сейф бар", "шағын тоңазытқыш пен жұмыс үстелімен жабдықталған", "ақылды үй жүйесі қосылған", "жылытылатын едені бар жайлы бөлме"]

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

# 2. Сессия күйлерін басқару (Авторизация)
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
    
    # Жеке кабинеттегі брондаулар тізімін көрсету
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
st.sidebar.write("Қажеттілігіңізді жазыңыз (мысалы: *'1-ші қабат'*, *'4 адамға'*, *'арзан'*):")

user_input = st.sidebar.text_input("Сұраныс енгізу:", value=st.session_state.chat_query)

if st.sidebar.button("Іздеуді орындау"):
    st.session_state.chat_query = user_input

if
