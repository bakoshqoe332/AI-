import streamlit as st
import sqlite3
import pandas as pd

st.title("🏨 ИИ арқылы отель нөмірін брондау жүйесі")
st.write("Шарттарды (мысалы: 'балконы жоқ', 'тыныш', 'отбасылық') терең түсінетін ақылды жүйе.")

# 1. Деректер базасы мен 15 нөмірді құру функциясы
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
    sample_rooms = [
        ('Standard Single', 45.0, 1, 0, 'Бір адамға арналған ықшам және жайлы нөмір, балконы жоқ'),
        ('Standard Double', 70.0, 2, 0, 'Екі адамға арналған стандартты нөмір, балконы жоқ'),
        ('Standard Twin', 75.0, 2, 0, 'Екі бөлек төсегі бар стандартты нөмір'),
        ('Deluxe King', 120.0, 2, 1, 'Үлкен корольдік төсегі және балконы бар жақсартылған нөмір'),
        ('Deluxe Ocean View', 150.0, 2, 1, 'Теңізге қарайтын керемет көрінісі мен балконы бар Deluxe нөмір'),
        ('Suite Family', 220.0, 4, 1, 'Үлкен отбасыға арналған кең люкс нөмір, балконы бар'),
        ('Executive Suite', 280.0, 3, 1, 'Бизнес саяхатшыларға арналған жоғары деңгейдегі нөмір'),
        ('Presidential Suite', 450.0, 5, 1, 'Барлық қолайлы жағдайлары мен панорамалық көрінісі бар премиум нөмір'),
        ('Standard Budget', 40.0, 1, 0, 'Қонақтар үшін ең тиімді бағадағы экономикалық нөмір'),
        ('Deluxe Quiet Zone', 130.0, 2, 1, 'Тыныш аймақта орналасқан, демалуға өте қолайлы нөмір'),
        ('Studio Apartment', 110.0, 2, 1, 'Ішінде шағын асүйі бар ыңғайлы студия нөмір'),
        ('Superior Twin', 90.0, 2, 1, 'Жақсартылған екі төсекті жайлы нөмір'),
        ('Penthouse', 500.0, 4, 1, 'Соңғы қабатта орналасқан сәнді пентхаус'),
        ('Standard Triple', 95.0, 3, 0, 'Үш адамға арналған кең стандартты нөмір, балконы жоқ'),
        ('Deluxe Corner', 140.0, 2, 1, 'Бұрыштық орналасуы мен екі жақты көрінісі бар Deluxe нөмір')
    ]
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

# 2. ИИ Мәтіндік іздеу интерфейсі
st.subheader("🤖 ИИ Смарт Іздеу Ассистенті")
user_query = st.text_input(
    "Қажеттілігіңізді еркін түрде жазыңыз:", 
    placeholder="Мысалы: балконы жоқ, тыныш аймақ, немесе отбасылық"
)

# Бүйірлік панель сүзгілері
st.sidebar.header("🔍 Қосымша параметрлер")
max_price = st.sidebar.slider("Максималды баға ($):", 30, 600, 200)
min_capacity = st.sidebar.slider("Адам саны:", 1, 5, 1)

# Бастапқы іріктеу
filtered = df[(df['price_per_night'] <= max_price) & (df['capacity'] >= min_capacity)]

# 3. Мәтінді талдау және шарттарды түсіну логикасы (NLP)
if user_query:
    q = user_query.lower()
    
    # Балкон шарттарын тексеру (теріс және оң мәндер)
    if 'балконы жоқ' in q or 'балконсыз' in q or 'балкон жоқ' in q:
        filtered = filtered[filtered['has_balcony'] == 0]
    elif 'балкон' in q or 'балконы бар' in q:
        filtered = filtered[filtered['has_balcony'] == 1]
        
    # Тыныш аймақ шарты
    if 'тыныш' in q or 'демалу' in q:
        filtered = filtered[filtered['description'].str.lower().str.contains('тыныш|демалу')]
        
    # Отбасы шарты
    if 'отбасы' in q or 'family' in q or 'үлкен' in q:
        filtered = filtered[(filtered['capacity'] >= 3) | (filtered['room_type'].str.lower().str.contains('family|suite'))]

st.write(f"### 🎯 Сіздің сұрауыңызға сай табылған нөмірлер ({len(filtered)}):")

if not filtered.empty:
    # Кестеде has_balcony мәнін түсінікті ету үшін өзгертеміз
    display_df = filtered.copy()
    display_df['has_balcony'] = display_df['has_balcony'].apply(lambda x: 'Иә' if x == 1 else 'Жоқ')
    st.dataframe(display_df[['room_type', 'price_per_night', 'capacity', 'has_balcony', 'description']])
else:
    st.warning("Өкінішке қарай, бұл талаптарға сай ешқандай нөмір табылмады. Басқаша сипаттап көріңіз!")
