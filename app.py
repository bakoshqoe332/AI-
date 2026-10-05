import streamlit as st
import sqlite3
import pandas as pd

st.title("🏨 ИИ арқылы отель нөмірін брондау жүйесі")
st.write("Әрбір сөзіңізді түсінетін ақылды іздеу жүйесі.")

# 1. Деректер базасы мен 15 нөмірді жасау
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
        ('Standard Single', 45.0, 1, 0, 'Бір адамға арналған ықшам және жайлы нөмір'),
        ('Standard Double', 70.0, 2, 0, 'Екі адамға арналған стандартты нөмір'),
        ('Standard Twin', 75.0, 2, 0, 'Екі бөлек төсегі бар стандартты нөмір'),
        ('Deluxe King', 120.0, 2, 1, 'Үлкен корольдік төсегі және балконы бар жақсартылған нөмір'),
        ('Deluxe Ocean View', 150.0, 2, 1, 'Теңізге қарайтын керемет көрінісі мен балконы бар Deluxe нөмір'),
        ('Suite Family', 220.0, 4, 1, 'Үлкен отбасыға арналған кең люкс нөмір'),
        ('Executive Suite', 280.0, 3, 1, 'Бизнес саяхатшыларға арналған жоғары деңгейдегі нөмір'),
        ('Presidential Suite', 450.0, 5, 1, 'Барлық қолайлы жағдайлары мен панорамалық көрінісі бар премиум нөмір'),
        ('Standard Budget', 40.0, 1, 0, 'Қонақтар үшін ең тиімді бағадағы экономикалық нөмір'),
        ('Deluxe Quiet Zone', 130.0, 2, 1, 'Тыныш аймақта орналасқан, демалуға өте қолайлы нөмір'),
        ('Studio Apartment', 110.0, 2, 1, 'Ішінде шағын асүйі бар ыңғайлы студия нөмір'),
        ('Superior Twin', 90.0, 2, 1, 'Жақсартылған екі төсекті жайлы нөмір'),
        ('Penthouse', 500.0, 4, 1, 'Соңғы қабатта орналасқан сәнді пентхаус'),
        ('Standard Triple', 95.0, 3, 0, 'Үш адамға арналған кең стандартты нөмір'),
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

# 2. ИИ арқылы еркін мәтінді терең түсіну жолағы
st.subheader("🤖 ИИ Мәтіндік Ассистенті")
user_query = st.text_input(
    "Қажеттілігіңізді толық жазыңыз:", 
    placeholder="Мысалы: балконы бар, тыныш, отбасылық немесе deluxe нөмір"
)

# Бүйірлік панель сүзгілері
st.sidebar.header("🔍 Қосымша параметрлер")
max_price = st.sidebar.slider("Максималды баға ($):", 30, 600, 200)
min_capacity = st.sidebar.slider("Адам саны:", 1, 5, 1)

# Бастапқы сүзу (баға мен адам саны бойынша)
filtered = df[(df['price_per_night'] <= max_price) & (df['capacity'] >= min_capacity)]

# 3. Мәтіндегі әрбір маңызды сөзді талдау логикасы
if user_query:
    query_lower = user_query.lower()
    
    # Егер сұрауда "балкон" сөзі болса
    if 'балкон' in query_lower:
        filtered = filtered[filtered['has_balcony'] == 1]
        
    # Егер сұрауда "тыныш" немесе "демалу" сөздері болса
    if 'тыныш' in query_lower or 'демалу' in query_lower:
        filtered = filtered[filtered['description'].str.lower().str.contains('тыныш|демалу')]
        
    # Егер сұрауда "отбасы" немесе "family" сөздері болса
    if 'отбасы' in query_lower or 'family' in query_lower:
        filtered = filtered[filtered['room_type'].str.lower().str.contains('family|suite')]

    # Жалпы мәтін бойынша сәйкестік іздеу
    keywords = query_lower.split()
    # Егер арнайы сөздерден бөлек басқа да сөздер жазылса, соларды да тексереміз
    text_filter = filtered['room_type'].str.lower().str.contains('|'.join(keywords)) | \
                  filtered['description'].str.lower().str.contains('|'.join(keywords))
    filtered = filtered[text_filter]

st.write(f"### 🎯 Сіздің сұрауыңызға сай табылған нөмірлер ({len(filtered)}):")
if not filtered.empty:
    st.dataframe(filtered[['room_type', 'price_per_night', 'capacity', 'has_balcony', 'description']])
else:
    st.warning("Өкінішке қарай, бұл сипаттамаға сай ешқандай нөмір табылмады. Басқаша сипаттап көріңіз!")
