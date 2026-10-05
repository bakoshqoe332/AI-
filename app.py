import streamlit as st
import sqlite3
import pandas as pd
import re

# Беттің конфигурациясы
st.set_page_config(page_title="Smart Hotel — Отель Брондау", page_icon="🏨", layout="wide")

# 1. 100 нөмірді қабаттар бойынша және қабат сайын бағасы артатын етіп генерациялау
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
        ("Standard Single", 40.0, 1, 0, "Бір адамға арналған ықшам және қолжетімді стандартты нөмір"),
        ("Standard Double", 60.0, 2, 0, "Екі адамға арналған жайлы стандартты нөмір"),
        ("Standard Twin", 65.0, 2, 0, "Екі бөлек төсегі бар стандартты бөлме"),
        ("Standard Triple", 85.0, 3, 0, "Үш адамдық кең стандартты нөмір"),
        ("Deluxe King", 110.0, 2, 1, "Үлкен корольдік төсегі және керемет балконы бар Deluxe нөмір"),
        ("Deluxe Ocean View", 135.0, 2, 1, "Теңізге қарайтын панорамалық көрінісі мен балконы бар Deluxe"),
        ("Deluxe Quiet Zone", 120.0, 2, 1, "Қонақүйдің ең тыныш аймағында орналасқан демалыс бөлмесі"),
        ("Suite Family", 180.0, 4, 1, "Үлкен отбасыға арналған кең люкс нөмір, балконы бар"),
        ("Executive Suite", 250.0, 3, 1, "Бизнес саяхатшыларға арналған жоғары деңгейдегі премиум люкс"),
        ("Presidential Suite", 400.0, 5, 1, "Жеке террасасы мен барлық элитті жағдайлары бар президенттік нөмір")
    ]
    
    views = ["Көше жаққа қарайтын терезе", "Ішкі аулаға көрініс", "Қала орталығына бағытталған панорама", "Саябаққа қарайтын тыныш терезе"]
    amenities = ["кондиционер, Wi-Fi және сейф бар", "шағын тоңазытқыш пен жұмыс үстелімен жабдықталған", "ақылды үй жүйесі қосылған", "жылытылатын едені бар жайлы бөлме"]

    sample_rooms = []
    
    # 10 қабат, әр қабатта 10 нөмір (101-110, 201-210, ..., 1001-1010)
    for floor in range(1, 11):
        for room_idx in range(1, 11):
            room_number = floor * 100 + room_idx if floor < 10 else 1000 + room_idx
            
            cat_index = (room_idx - 1) % len(room_categories)
            base = room_categories[cat_index]
            
            # Қабат жоғарылаған сайын бағаға үстеме қосылады (әр қабат үшін +$4 немесе +$5)
            floor_extra = (floor - 1) * 6.0
            price = round(base[1] + floor_extra + ((room_number * 2) % 10), 2)
            
            floor_name = f"{floor}-ші қабат" if floor < 10 else "10-ші қабат (Пентхаус)"
            r_type = f"{room_number} комната ({base[0]})"
            capacity = base[2]
            balcony = 1 if base[3] == 1 or (floor >= 5) else 0 # 5-қабаттан жоғарылардың көбінде балкон бар
            
            v_choice = views[room_number % len(views)]
            a_choice = amenities[(room_number * 3) % len(amenities)]
            balc_text = "Жеке балконы бар." if balcony == 1 else "Балконы жоқ."
            
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

# 2. Сессия күйін басқару
if "chat_query" not in st.session_state:
    st.session_state.chat_query = ""

# 3. БҮЙІРЛІК ПАНЕЛЬ — ИИ Ассистент чаты және сүзгілер
st.sidebar.markdown("## 🤖 ИИ Ассистент Чаты")
st.sidebar.write("Қажеттілігіңізді жазыңыз (мысалы: *'1-ші қабат'*, *'9 қабат'*, *'105 комната'*, *'арзан'*):")

user_input = st.sidebar.text_input("Сұраныс жазу:", value=st.session_state.chat_query)

if st.sidebar.button("Іздеуді орындау"):
    st.session_state.chat_query = user_input

if st.sidebar.button("Барлық бөлмелерді көрсету"):
    st.session_state.chat_query = ""
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.markdown("### 🎛️ Қосымша сүзгілер")
filter_balcony = st.sidebar.selectbox("Балкон жағдайы:", ["Барлығы", "Балконы бар", "Балконы жоқ"])
max_price = st.sidebar.slider("Максималды баға ($):", 40, 700, 700)

# 4. НЕГІЗГІ БЕТ — Бөлмелерді карточкалармен көрсету
st.title("🏨 Smart Hotel — Нөмірлер Каталогы")
st.write("Қонақүйдің 100 нөмірі қабаттар бойынша бөлінген (жоғары қабаттарға қарай баға біртіндеп өседі).")

# Деректерді сүзу
filtered = df[df['price_per_night'] <= max_price]

if filter_balcony == "Балконы бар":
    filtered = filtered[filtered['has_balcony'] == 1]
elif filter_balcony == "Балконы жоқ":
    filtered = filtered[filtered['has_balcony'] == 0]

# ИИ арқылы келген сұрауды талдау
active_query = st.session_state.chat_query.lower()
if active_query:
    # Қабат бойынша іздеу
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

    # Нақты бөлме нөмірін іздеу
    room_num_match = re.search(r'(\d{3,4})', active_query)
    if room_num_match and not floor_match:
        target_num = room_num_match.group(1)
        filtered = filtered[filtered['room_type'].str.contains(target_num)]
    
    # Адам санын анықтау
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
        
    st.info(f"🤖 ИИ Ассистент түсінді: «{st.session_state.chat_query}» шарттары бойынша ізделінді.")

st.write(f"### 🎯 Табылған нөмірлер саны: {len(filtered)}")

# 5. Нөмірлерді карточкалар түрінде шығару
if not filtered.empty:
    cols = st.columns(2)
    for index, row in filtered.reset_index().iterrows():
        col = cols[index % 2]
        with col:
            with st.container(border=True):
                st.subheader(f"🛏️ {row['room_type']}")
                st.write(f"**Сипаттамасы:** {row['description']}")
                
                m1, m2, m3 = st.columns(3)
                m1.metric("Бағасы", f"${row['price_per_night']}")
                m2.metric("Сиымдылығы", f"{row['capacity']} адам")
                balc_status = "Иә 🌅" if row['has_balcony'] == 1 else "Жоқ ❌"
                m3.metric("Балкон", balc_status)
                
                if st.button(f"Брондау ({row['room_type']})", key=f"book_{row['id']}"):
                    st.success(f"🎉 Құттықтаймыз! Сіз сәтті түрде **{row['room_type']}** нөмірін брондадыңыз!")
else:
    st.warning("Өкінішке қарай, бұл талаптарға сай ешқандай нөмір табылмады. Іздеу шарттарын өңгеріп көріңіз.")
