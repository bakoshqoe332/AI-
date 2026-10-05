import streamlit as st
import sqlite3
import pandas as pd
import re

st.title("🏨 ИИ арқылы отель нөмірін брондау жүйесі")
st.write("100 түрлі нөмірді қамтитын кеңейтілген ақылды іздеу жүйесі.")

# 1. 100 нөмірді автоматты түрде генерациялайтын және базаға қосатын функция
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
    
    # 100 түрлі нөмір тізімін генерациялау
    room_types = [
        ("Standard Single", 40.0, 45.0, 1, 0, "Бір адамға арналған ықшам және қолжетімді стандартты нөмір, балконы жоқ"),
        ("Standard Double", 65.0, 80.0, 2, 0, "Екі адамға арналған жайлы стандартты нөмір"),
        ("Standard Twin", 70.0, 85.0, 2, 0, "Екі бөлек төсегі бар стандартты бөлме"),
        ("Standard Triple", 90.0, 110.0, 3, 0, "Үш адамдық кең стандартты нөмір"),
        ("Deluxe King", 110.0, 140.0, 2, 1, "Үлкен корольдік төсегі және керемет балконы бар Deluxe нөмір"),
        ("Deluxe Ocean View", 140.0, 180.0, 2, 1, "Теңізге қарайтын панорамалық көрінісі мен балконы бар Deluxe"),
        ("Deluxe Quiet Zone", 125.0, 155.0, 2, 1, "Қонақүйдің ең тыныш аймағында орналасқан демалыс бөлмесі"),
        ("Suite Family", 200.0, 260.0, 4, 1, "Үлкен отбасыға арналған кең люкс нөмір, балконы бар"),
        ("Executive Suite", 270.0, 350.0, 3, 1, "Бизнес саяхатшыларға арналған жоғары деңгейдегі премиум люкс"),
        ("Presidential Suite", 450.0, 600.0, 5, 1, "Жеке террасасы мен барлық элитті жағдайлары бар президенттік нөмір"),
        ("Studio Apartment", 100.0, 130.0, 2, 1, "Ішінде шағын асүйі мен балконы бар студия нөмір"),
        ("Penthouse", 480.0, 700.0, 4, 1, "Соңғы қабатта орналасқан сәнді пентхаус және панорама")
    ]
    
    sample_rooms = []
    id_counter = 1
    
    # 100 бөлме шыққанша цикл арқылы әртүрлі вариацияда генерациялаймыз
    while id_counter <= 100:
        base = room_types[(id_counter - 1) % len(room_types)]
        r_type = f"{base[0]} #{id_counter}"
        # Бағаны әр бөлме үшін сәл өзгертіп әртараптандырамыз
        price = round(base[1] + ((id_counter * 3) % 25), 2)
        capacity = base[3]
        balcony = base[4]
        desc = f"{base[5]}. Заманауи жабдықталған таза және жайлы бөлме."
        
        # Кейбір нөмірлердің балкон қасиетін өзгертіп тұрамыз
        if id_counter % 5 == 0 and balcony == 1:
            balcony = 0
            desc += " (Балконы жоқ нұсқасы)"
            
        sample_rooms.append((r_type, price, capacity, balcony, desc))
        id_counter += 1

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
    placeholder="Мысалы: 4 адамдық нөмір, арзан бөлме, немесе балконы жоқ тыныш аймақ"
)

# Бастапқы DataFrame
filtered = df.copy()

# 3. Кеңейтілген ИИ мәтінді талдау логикасы (NLP Parser)
if user_query:
    q = user_query.lower()
    
    # Адам санын автоматты түрде анықтау
    capacity_match = re.search(r'(\d+)\s*(адам|орын|кісі)', q)
    if capacity_match:
        cap_val = int(capacity_match.group(1))
        filtered = filtered[filtered['capacity'] >= cap_val]
    
    # «Арзан» немесе «бюджетті» сөздерін түсіну
    if 'арзан' in q or 'бюджет' in q or 'тиімді' in q:
        filtered = filtered[filtered['price_per_night'] <= 80]
        
    # «Қымбат» немесе «люкс» сөздерін түсіну
    elif 'қымбат' in q or 'люкс' in q or 'премиум' in q:
        filtered = filtered[filtered['price_per_night'] >= 250]

    # Нақты бағаны санмен көрсеткенді талдау
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
