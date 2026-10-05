def init_db():
    conn = sqlite3.connect('hotel_system.db')
    cursor = conn.cursor()
    
    # Ескі кестені толығымен өшіріп, жаңадан құру (Барлық 15 нөмір шығуы үшін)
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
