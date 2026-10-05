import sqlite3

def init_db():
    # 'hotel_system.db' атты файл жасалады (егер жоқ болса)
    conn = sqlite3.connect('hotel_system.db')
    cursor = conn.cursor()

    # 1. Нөмірлер кестесін құру
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS rooms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            room_type TEXT NOT NULL,
            price_per_night REAL NOT NULL,
            capacity INTEGER NOT NULL,
            has_balcony INTEGER NOT NULL, -- 1 (Иә), 0 (Жоқ)
            description TEXT
        )
    ''')

    # 2. Брондаулар кестесін құру
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            room_id INTEGER,
            client_name TEXT NOT NULL,
            check_in_date TEXT NOT NULL,
            check_out_date TEXT NOT NULL,
            FOREIGN KEY (room_id) REFERENCES rooms (id)
        )
    ''')

    # Мысал ретінде базаға алғашқы нөмірлерді қосу (тек бір рет қосылады)
    cursor.execute("SELECT COUNT(*) FROM rooms")
    if cursor.fetchone()[0] == 0:
        sample_rooms = [
            ('Standard', 70.0, 2, 0, 'Ықшам әрі жайлы стандартты нөмір'),
            ('Deluxe', 120.0, 2, 1, 'Керемет көрінісі бар және балконы бар жақсартылған нөмір'),
            ('Suite', 250.0, 4, 1, 'Үлкен отбасыға арналған люкс нөмір')
        ]
        cursor.executemany('''
            INSERT INTO rooms (room_type, price_per_night, capacity, has_balcony, description)
            VALUES (?, ?, ?, ?, ?)
        ''', sample_rooms)

    conn.commit()
    conn.close()
    print("Деректер базасы сәтті құрылып, бастапқы деректер енгізілді!")

if __name__ == '__main__':
    init_db()
