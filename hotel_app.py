"""
TRYP by Wyndham — система бронирования с ИИ-ассистентом (всплывающее окно).

Запуск:
    pip install -U streamlit pandas anthropic
    streamlit run hotel_app.py

Ассистент работает ВСЕГДА: без API-ключа — встроенный офлайн-движок (kk/ru/en),
с ключом ANTHROPIC_API_KEY — Claude (при сбое API автоматически падает на офлайн).
Нужен Streamlit >= 1.39 (st.dialog + CSS-классы по key).
"""
import hashlib
import hmac
import html
import os
import random
import re
import secrets
import sqlite3
from contextlib import contextmanager
from datetime import date, timedelta

import pandas as pd
import streamlit as st

try:
    import anthropic
except ImportError:
    anthropic = None

DB_PATH = "hotel_system.db"
MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5-5")

st.set_page_config(page_title="TRYP by Wyndham — Брондау", page_icon="🏨", layout="wide")

# ───────────────────────────── ДИЗАЙН ─────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Playfair+Display:wght@600;700&display=swap');
:root{--bg:#0a0e17;--surface:#121826;--line:#232c3d;--gold:#d9b46c;--gold2:#b98a3e;--teal:#22d3ee;--indigo:#6366f1;--muted:#8a95a8}
html,body,.stApp,[class*="css"]{font-family:'Inter',sans-serif}
.stApp{background:radial-gradient(1200px 600px at 80% -10%,#1a2340 0%,transparent 60%),var(--bg);color:#e8edf5}
#MainMenu,footer{visibility:hidden}
header[data-testid="stHeader"]{background:transparent}
[data-testid="stSidebar"]{background:#0d121d;border-right:1px solid var(--line)}
[data-testid="stSidebar"] h2,[data-testid="stSidebar"] h3{color:var(--gold)}

/* HERO */
.hero{position:relative;overflow:hidden;border:1px solid var(--line);border-radius:24px;padding:42px 44px;margin-bottom:26px;
 background:linear-gradient(135deg,rgba(99,102,241,.16),rgba(34,211,238,.06) 55%,rgba(217,180,108,.10))}
.hero:after{content:"";position:absolute;right:-80px;top:-80px;width:320px;height:320px;border-radius:50%;
 background:radial-gradient(circle,rgba(217,180,108,.25),transparent 70%)}
.hero-badge{display:inline-block;letter-spacing:.18em;font-size:.72rem;font-weight:700;color:var(--gold);
 border:1px solid rgba(217,180,108,.4);padding:6px 14px;border-radius:999px;margin-bottom:16px}
.hero h1{font-family:'Playfair Display',serif;font-size:2.7rem;line-height:1.15;margin:0 0 10px;color:#fff}
.hero p{color:var(--muted);font-size:1.05rem;max-width:560px;margin:0 0 24px}
.stats{display:flex;gap:14px;flex-wrap:wrap;position:relative;z-index:1}
.stat{background:rgba(255,255,255,.04);border:1px solid var(--line);border-radius:14px;padding:12px 20px;min-width:110px}
.stat b{display:block;font-size:1.5rem;color:#fff}.stat span{font-size:.8rem;color:var(--muted)}

/* ФИЛЬТР-ПИЛЮЛИ */
.pills{display:flex;gap:8px;flex-wrap:wrap;margin:6px 0 14px}
.pill{background:rgba(99,102,241,.15);border:1px solid rgba(99,102,241,.45);color:#c7caff;padding:5px 12px;border-radius:999px;font-size:.82rem}
.result-head{font-size:1.15rem;font-weight:600;margin:10px 0 18px}
.result-head b{color:var(--gold)}

/* КАРТОЧКА НОМЕРА */
.room-card{--c:#58a6ff;position:relative;background:linear-gradient(180deg,rgba(24,31,48,.92),rgba(16,22,36,.92));
 border:1px solid var(--line);border-top:3px solid var(--c);border-radius:18px;padding:22px 22px 18px;margin-bottom:10px;
 box-shadow:0 10px 30px rgba(0,0,0,.35);transition:transform .25s ease,box-shadow .25s ease,border-color .25s ease}
.room-card:hover{transform:translateY(-4px);box-shadow:0 18px 40px rgba(0,0,0,.5);border-color:var(--c)}
.cat-std{--c:#58a6ff}.cat-dlx{--c:#a78bfa}.cat-ste{--c:#d9b46c}.cat-pre{--c:#f472b6}
.rc-top{display:flex;align-items:center;gap:10px;margin-bottom:10px}
.rc-num{font-family:'Playfair Display',serif;font-size:1.7rem;font-weight:700;color:#fff}
.rc-cat{font-size:.78rem;font-weight:600;color:var(--c);border:1px solid var(--c);padding:3px 10px;border-radius:999px}
.rc-status{margin-left:auto;font-size:.78rem;font-weight:600;padding:3px 10px;border-radius:999px}
.rc-status.free{color:#4ade80;background:rgba(74,222,128,.12)}.rc-status.busy{color:#f87171;background:rgba(248,113,113,.12)}
.room-desc{color:#b6c0d1;font-size:.9rem;line-height:1.55;margin-bottom:14px;min-height:70px}
.badges{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:14px}
.badge{background:#1a2234;border:1px solid var(--line);color:#aab4c6;padding:5px 11px;border-radius:999px;font-size:.8rem}
.rc-price{display:flex;align-items:baseline;gap:8px;border-top:1px dashed var(--line);padding-top:12px}
.rc-price .amt{font-size:1.7rem;font-weight:800;color:#fff}.rc-price .per{color:var(--muted);font-size:.85rem}
.rc-price .tot{margin-left:auto;color:var(--gold);font-weight:600;font-size:.9rem}

/* КНОПКИ */
div.stButton>button{background:linear-gradient(135deg,#e6c07b,var(--gold2));color:#1a1304;border:none;border-radius:12px;
 padding:11px 20px;font-weight:700;width:100%;box-shadow:0 6px 16px rgba(185,138,62,.28);transition:all .25s ease}
div.stButton>button:hover{filter:brightness(1.1);transform:translateY(-1px);color:#1a1304}
div.stButton>button:disabled{background:#1a2234!important;color:#6b778c!important;border:1px solid var(--line);box-shadow:none}
[class*="st-key-chip_"] div.stButton>button{background:#182033;color:#c9d3e6;border:1px solid var(--line);box-shadow:none;padding:8px 10px;font-weight:500;font-size:.85rem}
[class*="st-key-chip_"] div.stButton>button:hover{border-color:var(--indigo);color:#fff;filter:none}

/* ПЛАВАЮЩАЯ КНОПКА ИИ */
.st-key-ai_fab{position:fixed;bottom:28px;right:28px;z-index:1000;width:auto!important}
.st-key-ai_fab div.stButton>button{width:auto;border-radius:999px;padding:15px 26px;font-size:1rem;color:#fff;
 background:linear-gradient(135deg,var(--indigo),var(--teal));box-shadow:0 10px 30px rgba(99,102,241,.55);animation:pulse 2.6s infinite}
.st-key-ai_fab div.stButton>button:hover{color:#fff}
@keyframes pulse{0%{box-shadow:0 0 0 0 rgba(99,102,241,.55)}70%{box-shadow:0 0 0 18px rgba(99,102,241,0)}100%{box-shadow:0 0 0 0 rgba(99,102,241,0)}}

/* ОКНО АССИСТЕНТА */
div[role="dialog"]{background:#0f1521!important;border:1px solid var(--line);border-radius:22px!important;box-shadow:0 30px 80px rgba(0,0,0,.65)}
.ai-status{display:inline-flex;align-items:center;gap:8px;font-size:.8rem;color:var(--muted);margin-bottom:8px}
.dot{width:8px;height:8px;border-radius:50%;background:#4ade80;box-shadow:0 0 8px #4ade80}.dot.off{background:#fbbf24;box-shadow:0 0 8px #fbbf24}
[data-testid="stChatMessage"]{background:rgba(255,255,255,.03);border:1px solid var(--line);border-radius:14px}
@media(max-width:700px){.hero{padding:26px 22px}.hero h1{font-size:1.9rem}}
</style>
""", unsafe_allow_html=True)


# ───────────────────────────── БАЗА ДАННЫХ ─────────────────────────────
@contextmanager
def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# Базовые тарифы (USD/ночь, 1–2 этаж) — позиционирование: 4★ upper-midscale, как Ramada/Park Hotel/DoubleTree в Алматы
BASE_RATES = {"Standard Single": 80, "Standard Double": 95, "Standard Twin": 98, "Standard Triple": 120,
              "Deluxe King": 145, "Deluxe Ocean View": 170, "Deluxe Quiet Zone": 155,
              "Suite Family": 220, "Executive Suite": 290, "Presidential Suite": 420}


def list_price(category: str, floor: int, balcony: int) -> float:
    """Прайс-лист: тариф категории × этаж (+1.5% за этаж, пентхаус +25%) × балкон (+5% только для Standard)."""
    f = 1.25 if floor == 10 else 1 + 0.015 * (floor - 1)
    b = 1.05 if category.startswith("Standard") and balcony else 1.0
    return float(round(BASE_RATES[category] * f * b / 5) * 5)


# ───────────── УНИКАЛЬНЫЕ ОПИСАНИЯ НОМЕРОВ ─────────────
BEDS = {
    "Standard Single": "бір адамдық ортопедиялық төсек (100 см)",
    "Standard Double": "екі кісілік кең төсек (160 см)",
    "Standard Twin": "екі бөлек төсек (әрқайсысы 90 см)",
    "Standard Triple": "бір екі кісілік және бір жеке төсек",
    "Deluxe King": "King-size төсек (180 см)",
    "Deluxe Ocean View": "King-size төсек (180 см)",
    "Deluxe Quiet Zone": "Queen-size төсек (160 см)",
    "Suite Family": "екі жатын бөлме: бір King-size және екі жеке төсек",
    "Executive Suite": "King-size төсек пен диван-төсек, жұмыс аймағы бөлек",
    "Presidential Suite": "екі жатын бөлме (екі King-size төсек), қонақ бөлмесі және диван-төсек",
}
AREA = {"Standard Single": 18, "Standard Double": 22, "Standard Twin": 23, "Standard Triple": 28,
        "Deluxe King": 32, "Deluxe Ocean View": 35, "Deluxe Quiet Zone": 33, "Suite Family": 52,
        "Executive Suite": 60, "Presidential Suite": 110}
VIEWS = {
    1: ["ішкі жасыл аулаға әдемі көрініс", "көше бойындағы ағаштарға қарайтын көрініс",
        "қонақүй аулындағы гүлзарға көрініс"],
    2: ["қала орталығына бағытталған көрініс", "жақын маңдағы саябаққа көрініс",
        "жасыл аула мен қала көшелеріне көрініс", "тыныш көшеге қарайтын көрініс"],
    3: ["қаланың кең панорамасына көрініс", "шағын саябақ пен қала ғимараттарына көрініс",
        "кешкі қала шамдарына көрініс"],
    4: ["қаланың биіктен ашылатын панорамасы", "көкжиекке дейін созылған қала көрінісі"],
    5: ["қала мен көкжиекке 270° панорамалық көрініс", "шатырлар үстінен ашылатын таңғажайып көрініс"],
}
SPECIAL_VIEWS = {
    "Deluxe Ocean View": ["ашық көкжиекке қарайтын кең панорама", "жарық пен кеңістікке толы панорамалық көрініс"],
    "Deluxe Quiet Zone": ["қонақүйдің ең тыныш жағындағы жасыл аулаға көрініс"],
}
SUN = {
    "оңтүстікке": "Терезелері оңтүстікке қараған, сондықтан күн сәулесі күні бойы түседі.",
    "шығысқа": "Терезелері шығысқа қараған, таңертең бөлме күн сәулесімен оянады.",
    "батысқа": "Терезелері батысқа қараған, кешкі күн батудың жарығы бөлмені жылытады.",
    "солтүстікке": "Терезелері солтүстікке қараған, бөлме салқын әрі жұмсақ жарықпен толады.",
}
BALCONY = [
    "Жеке балкон бар: таңертеңгі кофеге өте ыңғайлы.", "Балконға шығатын шыны есік бөлмені жарыққа бөлейді.",
    "Кең балконда демалуға арналған орындықтар қойылған.",
    "Жеке балконнан таза ауа мен көрініске рахаттануға болады.",
    "Балконда кешкі шай ішіп, қала тынысын тыңдауға болады.", "Шағын балкон демалыс пен тыныс алуға арналған.",
    "Балкон бөлмеге қосымша кеңістік пен таза ауа береді.", "Балконнан күн батқанда ерекше әдемі көрініс ашылады.",
]
TERRACE = [
    "Жеке террасасы бар: кешкі уақытты отбасымен өткізуге таптырмас орын.",
    "Кең терраса бөлмені сыртқы кеңістікпен жалғастырады.", "Террасадағы үстел мен орындықтар таңғы асқа ыңғайлы.",
]
NO_BALCONY = [
    "Балкон жоқ, бірақ үлкен терезе бөлмені жарық етеді.",
    "Балконсыз нөмір; орнына терезе алдында жайлы орындық бар.",
    "Балкон қарастырылмаған, бұл бағаны тиімдірек етеді.",
    "Балкон жоқ, орнына терезе алдында кішкентай демалыс бұрышы бар.",
]
A_BASE = ["кондиционер", "жылдам Wi-Fi", "электронды сейф", "Smart TV", "шағын тоңазытқыш", "шай-кофе жинағы",
          "шашты кептіргіш", "жұмыс үстелі", "дыбыс өткізбейтін терезелер", "тегін су мен тәттілер"]
A_PREMIUM = ["Nespresso кофе машинасы", "жылытылатын еден", "жаңбыр душы", "ақылды үй жүйесі",
             "дауыстық көмекші", "халат пен тәпішке", "ванна мен жеке душ", "жұмсақ матрас топпері", "мини-бар"]
A_TOP = ["кең жұмыс аймағы", "принтер мен жоғары жылдамдықты интернет", "welcome-сусын",
         "екі санузел", "жеке мини-асхана", "Bluetooth колонка", "жеке батлер қызметі"]
A_FAMILY = ["балаларға арналған қосымша жиһаз", "балаларға арналған халаттар"]
STYLES = ["жылы құм түстес реңктермен безендірілген", "заманауи минимализм стилінде жасалған",
          "табиғи ағаш пен тас өңдеумен әшекейленген", "жұмсақ көк-сұр реңктерде шешілген",
          "лофт стилінде сәнді безендірілген", "скандинавиялық жеңіл стильде жасалған",
          "классикалық әрі жайлы дизайнмен ерекшеленеді"]
AUDIENCE = {
    "Standard Single": ["Жалғыз саяхатшыларға және қысқа іссапарға тамаша.",
                        "Тыныш демалып, жұмыс істегісі келетін бір қонаққа арналған.",
                        "Бір түндік аялдауға тиімді әрі ыңғайлы таңдау."],
    "Standard Double": ["Жұптар мен достар үшін ыңғайлы таңдау.", "Екі қонаққа арналған жайлы әрі тиімді нұсқа.",
                        "Қала бойынша қысқа сапарға тамаша."],
    "Standard Twin": ["Әріптестер мен достарға ыңғайлы: әрқайсысының жеке төсегі бар.",
                      "Бөлек ұйықтағанды қалайтын екі қонаққа арналған.",
                      "Іссапарға бірге келген әріптестерге таптырмас."],
    "Standard Triple": ["Үш адамдық шағын компания немесе отбасы үшін кең нұсқа.", "Баласы бар отбасыларға ыңғайлы.",
                        "Үш дос бірге демалуға тиімді."],
    "Deluxe King": ["Романтикалық демалысқа немесе ерекше мереке үшін таңдалады.",
                    "Қосымша кеңістік пен жайлылықты қалайтын жұптарға арналған.",
                    "Ұзақ демалысқа жайлы әрі кең нөмір."],
    "Deluxe Ocean View": ["Панорамалық көрінісін бағалайтын қонақтарға арналған.",
                          "Әдемі көрінісі бар таңдаулы нөмір, фотоға таптырмас.",
                          "Көріністі бәрінен жоғары қоятын қонақтарға ең жақсы нұсқа."],
    "Deluxe Quiet Zone": ["Тыныштықты бағалайтын қонақтарға арналған.",
                          "Ұйқысы сезімтал қонақтар үшін қонақүйдің ең тыныш жағы.",
                          "Демалып, күш жинауға арналған орын."],
    "Suite Family": ["Отбасымен демалуға арналған, төрт қонаққа дейін сыяды.",
                     "Балалары бар отбасына екі бөлме мен жеке кеңістік ұсынады.",
                     "Үлкен компанияға ыңғайлы әрі кең."],
    "Executive Suite": ["Бизнес-саяхатшыларға арналған: жұмыс аймағы бөлек.",
                        "Кездесулерге ыңғайлы бөлек қонақ аймағы бар.",
                        "Іссапарда жұмыс пен демалысты ұштастыруға арналған."],
    "Presidential Suite": ["Қонақүйдің ең жоғары деңгейіндегі люкс, бес қонаққа дейін сыяды.",
                           "VIP-қонақтар мен ерекше мерекелерге арналған.",
                           "Ең талғампаз қонақтарға арналған бірегей нөмір."],
}
LOCATION = {"near": ["Лифтке жақын орналасқан, жүгі көп қонаққа ыңғайлы.", "Лифтке бірнеше қадам ғана жерде."],
            "mid": ["Дәліздің ортасында орналасқан.", "Дәліздің ортаңғы бөлігіндегі қолайлы орын.",
            "Лифт пен дәліз шетінен тең қашықтықта орналасқан.", "Дәліздің орта тұсында, тыныш әрі ыңғайлы жерде."],
            "end": ["Дәліздің соңында орналасқан, сондықтан өте тыныш.",
                    "Көршілері аз шеткі нөмір: тыныштықты сүйетіндерге."]}


def make_description(number: int, floor: int, category: str, capacity: int, balcony: int, used: set) -> str:
    """Детерминированное уникальное описание: параметры номера + случайный (по seed=номер) набор деталей."""
    idx = number % 100
    tier = 1 if floor <= 2 else 2 if floor <= 5 else 3 if floor <= 8 else 4 if floor == 9 else 5
    area = AREA[category] + number % 4 + (4 if floor == 10 else 0)
    for attempt in range(50):
        rnd = random.Random(number * 7919 + attempt)
        fl = f"{floor}-қабаттағы" if floor < 10 else "10-қабаттағы (пентхаус деңгейі)"
        fl_loc = f"{floor}-қабатта" if floor < 10 else "10-қабатта (пентхаус деңгейінде)"
        opening = rnd.choice([f"{fl} {area} м² жайлы нөмір: {BEDS[category]}.",
                              f"Көлемі {area} м² бұл нөмір {fl_loc} орналасқан, мұнда {BEDS[category]} бар.",
                              f"{fl} {area} м² нөмірде {BEDS[category]} қарастырылған."])
        view = rnd.choice(SPECIAL_VIEWS.get(category, VIEWS[tier]))
        if balcony:
            outdoor = rnd.choice(TERRACE if category in ("Suite Family", "Presidential Suite") else BALCONY)
        else:
            outdoor = rnd.choice(NO_BALCONY)
        pool = A_BASE + (A_PREMIUM if not category.startswith("Standard") else [])
        if category in ("Executive Suite", "Presidential Suite"):
            pool += A_TOP
        if category == "Suite Family":
            pool += A_FAMILY
        k = 3 if category.startswith("Standard") else 4
        items = rnd.sample(pool, k)
        amen = f"Бөлмеде {', '.join(items[:-1])} және {items[-1]} бар."
        sun_dir = rnd.choice(list(SUN))
        loc = "near" if idx in (1, 2) else "end" if idx in (9, 10) else "mid"
        extras = rnd.sample([f"Интерьері {rnd.choice(STYLES)}.", rnd.choice(AUDIENCE[category]),
                             rnd.choice(LOCATION[loc]), SUN[sun_dir]], 2)
        text = " ".join([opening, f"Терезеден {view} ашылады.", outdoor, amen] + extras)
        if text not in used:
            used.add(text)
            return text
    raise RuntimeError(f"не удалось подобрать уникальное описание для {number}")


def build_rooms():
    categories = [
        ("Standard Single", 40.0, 1, 0, "Бір адамға арналған ықшам және заманауи жайлы стандартты нөмір"),
        ("Standard Double", 60.0, 2, 0, "Екі адамға арналған жарық және таза стандартты нөмір"),
        ("Standard Twin", 65.0, 2, 0, "Екі бөлек төсегі бар жайлы стандартты бөлме"),
        ("Standard Triple", 85.0, 3, 0, "Үш адамдық кең стандартты нөмір"),
        ("Deluxe King", 110.0, 2, 1, "Үлкен корольдік төсегі және панорамалық балконы бар Deluxe нөмір"),
        ("Deluxe Ocean View", 140.0, 2, 1, "Әсем көрінісі мен жеке балконы бар элиталық Deluxe"),
        ("Deluxe Quiet Zone", 125.0, 2, 1, "Қонақүйдің ең тыныш әрі жайлы аймағында орналасқан нөмір"),
        ("Suite Family", 180.0, 4, 1, "Үлкен отбасыға арналған кең люкс нөмір, жеке терассасы бар"),
        ("Executive Suite", 250.0, 3, 1, "Бизнес саяхатшыларға арналған жоғары деңгейдегі премиум люкс"),
        ("Presidential Suite", 380.0, 5, 1, "Президенттік деңгейдегі сәнді террасасы мен люкс жағдайлары бар нөмір"),
    ]
    views = ["Көше жаққа қарайтын панорамалық терезе", "Ішкі жасыл аулаға әдемі көрініс",
             "Қала орталығына бағытталған көрініс", "Саябаққа қарайтын тыныш терезе"]
    amenities = ["кондиционер, Wi-Fi және сейф бар", "шағын тоңазытқыш пен жұмыс үстелімен жабдықталған",
                 "ақылды үй жүйесі мен дауыстық көмекші қосылған", "жылытылатын едені бар премиум бөлме"]
    rows = []
    used_desc = set()
    for floor in range(1, 11):
        for idx in range(1, 11):
            number = floor * 100 + idx if floor < 10 else 1000 + idx
            name, base_price, capacity, base_balcony, text = categories[(idx - 1) % len(categories)]
            balcony = 1 if base_balcony == 1 or floor >= 3 else 0
            price = list_price(name, floor, balcony)
            desc = make_description(number, floor, name, capacity, balcony, used_desc)
            rows.append((f"{number} комната ({name})", price, capacity, balcony, desc, number, floor, name))
    return rows


def init_db():
    with db() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL, full_name TEXT NOT NULL, phone TEXT)""")
        c.execute("""CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT NOT NULL, room_type TEXT NOT NULL,
            price REAL NOT NULL, booking_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
        c.execute("""CREATE TABLE IF NOT EXISTS rooms (
            id INTEGER PRIMARY KEY AUTOINCREMENT, room_type TEXT NOT NULL, price_per_night REAL NOT NULL,
            capacity INTEGER NOT NULL, has_balcony INTEGER NOT NULL, description TEXT)""")
        for table, col, ddl in [("bookings", "room_id", "INTEGER"), ("bookings", "check_in", "TEXT"),
                                ("bookings", "check_out", "TEXT"), ("rooms", "room_number", "INTEGER"),
                                ("rooms", "floor", "INTEGER"), ("rooms", "category", "TEXT"),
                                ("users", "role", "TEXT DEFAULT 'user'")]:
            existing = {r["name"] for r in c.execute(f"PRAGMA table_info({table})")}
            if col not in existing:
                c.execute(f"ALTER TABLE {table} ADD COLUMN {col} {ddl}")
        if c.execute("SELECT COUNT(*) FROM rooms").fetchone()[0] == 0:
            c.executemany("""INSERT INTO rooms (room_type, price_per_night, capacity, has_balcony,
                             description, room_number, floor, category) VALUES (?,?,?,?,?,?,?,?)""", build_rooms())
        for r in c.execute("SELECT id, room_type FROM rooms WHERE room_number IS NULL").fetchall():
            m = re.match(r"(\d+)\s+комната \((.+)\)", r["room_type"])
            if m:
                n = int(m.group(1))
                c.execute("UPDATE rooms SET room_number=?, floor=?, category=? WHERE id=?",
                          (n, n // 100, m.group(2), r["id"]))
        if c.execute("PRAGMA user_version").fetchone()[0] < 2:  # пересчёт цен по новой модели
            for r in c.execute("SELECT id, category, floor, has_balcony FROM rooms").fetchall():
                if r["category"] in BASE_RATES:
                    c.execute("UPDATE rooms SET price_per_night=? WHERE id=?",
                              (list_price(r["category"], r["floor"], r["has_balcony"]), r["id"]))
            c.execute("PRAGMA user_version = 2")
        if c.execute("PRAGMA user_version").fetchone()[0] < 3:  # уникальные описания номеров
            used = set()
            for r in c.execute("""SELECT id, room_number, floor, category, capacity, has_balcony
                                  FROM rooms ORDER BY room_number""").fetchall():
                if r["category"] in BASE_RATES:
                    c.execute("UPDATE rooms SET description=? WHERE id=?",
                              (make_description(r["room_number"], r["floor"], r["category"], r["capacity"],
                                                r["has_balcony"], used), r["id"]))
            c.execute("PRAGMA user_version = 3")


init_db()


@st.cache_data
def get_rooms() -> pd.DataFrame:
    with db() as c:
        return pd.read_sql_query("SELECT * FROM rooms ORDER BY room_number", c)


def booked_room_ids(check_in: date, check_out: date) -> set:
    with db() as c:
        rows = c.execute("""SELECT DISTINCT room_id FROM bookings
                            WHERE room_id IS NOT NULL AND check_in < ? AND check_out > ?""",
                         (check_out.isoformat(), check_in.isoformat())).fetchall()
    return {r["room_id"] for r in rows}


SEASON = {1: 1.10, 2: 0.95, 3: 1.00, 4: 0.95, 5: 1.00, 6: 1.10, 7: 1.15, 8: 1.15,
          9: 1.05, 10: 0.95, 11: 0.90, 12: 1.15}  # ориентир; калибруйте по своей статистике загрузки


def price_multiplier(ci: date, co: date, occupancy: float = 0.0):
    """Общий коэффициент на даты: сезон × выходные × срок до заезда × длительность × загрузка."""
    co = co if co > ci else ci + timedelta(days=1)
    nights = (co - ci).days
    days = [ci + timedelta(d) for d in range(nights)]
    season = sum(SEASON[d.month] for d in days) / nights
    weekend = sum(1.05 if d.weekday() in (4, 5) else 1.0 for d in days) / nights
    lead = (ci - date.today()).days
    lead_f = 0.92 if lead >= 38 else 1.0 if lead >= 14 else 1.05 if lead >= 3 else 1.10
    los_f = 0.90 if nights >= 7 else 0.95 if nights >= 4 else 1.0
    occ_f = 1.12 if occupancy >= 0.8 else 1.06 if occupancy >= 0.6 else 1.0
    parts = [(label, f) for label, f in [("Маусым", season), ("Демалыс күндері", weekend),
                                         ("Брондау мерзімі", lead_f), ("Ұзақ тұру", los_f), ("Жүктеме", occ_f)]
             if abs(f - 1) > 0.004]
    mult = season * weekend * lead_f * los_f * occ_f
    return mult, [f"{label} {(f - 1) * 100:+.0f}%" for label, f in parts]


def with_prices(d: pd.DataFrame, ci: date, co: date):
    """Добавляет price_now (цена за ночь на выбранные даты). Возвращает (df, занятые_id, коэффициент, пояснения)."""
    busy = booked_room_ids(ci, co) if co > ci else set()
    mult, parts = price_multiplier(ci, co, len(busy) / max(len(get_rooms()), 1))
    d = d.copy()
    d["price_now"] = (d["price_per_night"] * mult).round().astype(int)
    return d, busy, mult, parts


def book_room(username, room, check_in: date, check_out: date, night_price: float) -> bool:
    with db() as c:
        c.execute("BEGIN IMMEDIATE")
        busy = c.execute("SELECT 1 FROM bookings WHERE room_id=? AND check_in < ? AND check_out > ?",
                         (int(room["id"]), check_out.isoformat(), check_in.isoformat())).fetchone()
        if busy:
            return False
        c.execute("""INSERT INTO bookings (username, room_type, price, room_id, check_in, check_out)
                     VALUES (?,?,?,?,?,?)""",
                  (username, room["room_type"], float(night_price), int(room["id"]),
                   check_in.isoformat(), check_out.isoformat()))
        return True


# ───────────────────────────── ПАРОЛИ ─────────────────────────────
def hash_password(password: str, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), 200_000).hex()
    return f"{salt}${digest}"


def verify_password(password: str, stored: str) -> bool:
    if "$" in stored:
        return hmac.compare_digest(hash_password(password, stored.split("$", 1)[0]), stored)
    return hmac.compare_digest(hashlib.sha256(password.encode()).hexdigest(), stored)


def _cfg(name):
    try:
        v = st.secrets.get(name)
    except Exception:
        v = None
    return v or os.getenv(name)


@st.cache_resource
def ensure_admin():
    """Создаёт/обновляет админа один раз за запуск сервера. Пароль берётся из ADMIN_PASSWORD
    (переменная окружения или .streamlit/secrets.toml); если не задан — генерируется и печатается в терминал."""
    username = _cfg("ADMIN_USERNAME") or "admin"
    password = _cfg("ADMIN_PASSWORD")
    with db() as c:
        row = c.execute("SELECT password FROM users WHERE username=?", (username,)).fetchone()
        if password:
            if row is None:
                c.execute("INSERT INTO users (username, password, full_name, role) VALUES (?,?,?,'admin')",
                          (username, hash_password(password), "Administrator"))
            elif not verify_password(password, row["password"]):
                c.execute("UPDATE users SET password=?, role='admin' WHERE username=?",
                          (hash_password(password), username))
            else:
                c.execute("UPDATE users SET role='admin' WHERE username=?", (username,))
        elif row is None and not c.execute("SELECT 1 FROM users WHERE role='admin'").fetchone():
            generated = secrets.token_urlsafe(9)
            c.execute("INSERT INTO users (username, password, full_name, role) VALUES (?,?,?,'admin')",
                      (username, hash_password(generated), "Administrator"))
            print(f"\n=== ADMIN CREATED ===  login: {username}  password: {generated}  (смените через ADMIN_PASSWORD)\n")
    return True


ensure_admin()


# ───────────────────────────── ФИЛЬТРЫ ─────────────────────────────
def apply_filters(d: pd.DataFrame, f: dict) -> pd.DataFrame:
    if f.get("floor"):
        d = d[d["floor"] == int(f["floor"])]
    if f.get("room_number"):
        d = d[d["room_number"] == int(f["room_number"])]
    if f.get("min_capacity"):
        d = d[d["capacity"] >= int(f["min_capacity"])]
    pc = "price_now" if "price_now" in d.columns else "price_per_night"
    if f.get("min_price") is not None:
        d = d[d[pc] >= float(f["min_price"])]
    if f.get("max_price") is not None:
        d = d[d[pc] <= float(f["max_price"])]
    if f.get("has_balcony") is not None:
        d = d[d["has_balcony"] == int(bool(f["has_balcony"]))]
    if f.get("category"):
        d = d[d["category"].str.contains(str(f["category"]), case=False, regex=False)]
    return d


FILTER_NAMES = {"floor": "Қабат", "room_number": "Нөмір", "min_capacity": "Адам ≥", "min_price": "Баға ≥ $",
                "max_price": "Баға ≤ $", "has_balcony": "Балкон", "category": "Санат"}


def filter_pills(f: dict) -> str:
    out = []
    for k, v in f.items():
        if k in FILTER_NAMES:
            v = ("Иә" if v else "Жоқ") if isinstance(v, bool) else v
            out.append(f'<span class="pill">{FILTER_NAMES[k]}: {html.escape(str(v))}</span>')
    return "".join(out)


# ───────────────────────────── ОФЛАЙН-АССИСТЕНТ (без API) ─────────────────────────────
TXT = {
    "kk": {"greet": "Сәлем! 👋 Мен қонақүй ассистентімін. Қабат, баға, балкон, адам саны не санатты жазыңыз — нөмір таңдап беремін.",
           "help": "Мысалдар: «3-ші қабат, балкон бар», «4 адамға $250-ге дейін», «люкс», «пентхаус», «тазарту».",
           "thanks": "Оқасы жоқ! Басқа сұрақ болса, жазыңыз 😊", "reset": "Сүзгілер тазартылды ✅",
           "unknown": "Түсінбедім 🤔 Қабат, баға, адам саны, балкон немесе санатты көрсетіңіз.",
           "found": "Табылды: **{n}** бос нөмір, ${lo} – ${hi} / түн. Ең тиімділері:",
           "none": "Бұл талаптарға сай бос нөмір жоқ 😕 Күндерді немесе сүзгіні өзгертіп көріңіз.",
           "fail": "⚠ ИИ-сервис қолжетімсіз, офлайн режим қолданылды.", "apply": "✅ Нәтижені көру ({n})",
           "off": "Офлайн режим (API қажет емес)", "on": "Claude қосулы", "ph": "Не іздеп жүрсіз?"},
    "ru": {"greet": "Привет! 👋 Я ассистент отеля. Напишите этаж, цену, балкон, число гостей или категорию — подберу номер.",
           "help": "Примеры: «3 этаж с балконом», «на 4 человека до $250», «люкс», «пентхаус», «сброс».",
           "thanks": "Пожалуйста! Если что — пишите 😊", "reset": "Фильтры сброшены ✅",
           "unknown": "Не понял 🤔 Укажите этаж, цену, число гостей, балкон или категорию.",
           "found": "Нашёл **{n}** свободных номеров, ${lo} – ${hi} за ночь. Самые выгодные:",
           "none": "Свободных номеров по этим условиям нет 😕 Измените даты или критерии.",
           "fail": "⚠ ИИ-сервис недоступен, использую офлайн-режим.", "apply": "✅ Показать результат ({n})",
           "off": "Офлайн-режим (API не нужен)", "on": "Claude подключён", "ph": "Что ищете?"},
    "en": {"greet": "Hi! 👋 I'm the hotel assistant. Tell me the floor, price, balcony, guests or category and I'll find a room.",
           "help": "Try: “3rd floor with balcony”, “for 4 guests under $250”, “suite”, “penthouse”, “reset”.",
           "thanks": "You're welcome! Ask anything else 😊", "reset": "Filters cleared ✅",
           "unknown": "I didn't get that 🤔 Mention a floor, price, guests, balcony or category.",
           "found": "Found **{n}** available rooms, ${lo} – ${hi} per night. Best value:",
           "none": "No available rooms match that 😕 Try other dates or criteria.",
           "fail": "⚠ AI service unavailable, using offline mode.", "apply": "✅ Show results ({n})",
           "off": "Offline mode (no API needed)", "on": "Claude connected", "ph": "What are you looking for?"},
}

KK_LETTERS = set("әғқңөұүһі")
KK_WORDS = r"\b(арзан|бар|жоқ|керек|болсын|тиімді|бөлме|нөмір|қымбат|тазарту|рахмет|сәлем)\b"
CATS = [(r"президент|president", "Presidential"), (r"executive|бизнес|business|командиров", "Executive"),
        (r"делюкс|deluxe", "Deluxe"), (r"люкс|suite|сюит", "Suite"),
        (r"standard|стандарт", "Standard"), (r"single|одномест|бір кісілік", "Single"),
        (r"double|двуспал|екі кісілік", "Double"), (r"twin|твин", "Twin"),
        (r"triple|трёхмест|трехмест", "Triple"), (r"ocean|океан|вид на море|теңіз", "Ocean View"),
        (r"тыныш|тихий|тихо|quiet", "Quiet Zone")]
MAXP = [r"(?:до|under|up to|max|не дороже)\s*\$?\s*(\d{2,4})", r"\$\s*(\d{2,4})",
        r"(\d{2,4})\s*(?:\$|долл|usd)\w*", r"(\d{2,4})\s*-?\s*(?:ге|ға|қа|ке)\s*дейін"]
MINP = [r"(?:от|бастап|from|over|min)\s*\$?\s*(\d{2,4})"]


def detect_lang(text: str, last: str = "ru") -> str:
    t = text.lower()
    if any(ch in KK_LETTERS for ch in t) or re.search(KK_WORDS, t):
        return "kk"
    if re.search(r"[а-яё]", t):
        return "ru"
    return "en" if re.search(r"[a-z]", t) else last


def _take(patterns, t):
    for p in patterns:
        m = re.search(p, t)
        if m:
            val = next(g for g in m.groups() if g)
            return int(val), t[:m.start()] + " " + t[m.end():]
    return None, t


def local_parse(text: str):
    """Возвращает (фильтры, интент). Интенты: reset/greet/thanks/help/filter/unknown."""
    t = text.lower().strip()
    if re.search(r"тазарт|сброс|заново|очист|reset|clear", t):
        return {}, "reset"
    f = {}
    v, t = _take(MAXP, t)
    if v: f["max_price"] = v
    v, t = _take(MINP, t)
    if v: f["min_price"] = v
    if re.search(r"пентхаус|пентхауз|penthouse", t):
        f["floor"] = 10
    elif (m := re.search(r"(\d+)\s*-?\s*(?:ші|нші|ой|й|st|nd|rd|th)?\s*(?:қабат|этаж|floor)", t)) or \
         (m := re.search(r"(?:қабат|этаж|floor)\s*(\d+)", t)):
        f["floor"] = int(m.group(1)); t = t[:m.start()] + " " + t[m.end():]
    if m := re.search(r"(\d+)\s*(?:адам|орын|кісі|чел|человек|гост|people|guests?|persons?|pax)", t):
        f["min_capacity"] = int(m.group(1)); t = t[:m.start()] + " " + t[m.end():]
    elif re.search(r"отбасы|семь|семей|family|дет[иь]|балал|kids", t):
        f["min_capacity"] = 4
    if "floor" not in f and (m := re.search(r"\b(\d{3,4})\b", t)) and 101 <= int(m.group(1)) <= 1010:
        f["room_number"] = int(m.group(1))
    for pattern, cat in CATS:
        if re.search(pattern, t):
            f["category"] = cat; break
    if re.search(r"романтик|медов|honeymoon|romantic", t):
        f["has_balcony"] = True; f.setdefault("category", "Deluxe")
    if "балкон" in t or "balcon" in t:
        f["has_balcony"] = not re.search(r"жоқ|сыз|без|нет|\bno\b|without", t)
    if "max_price" not in f and re.search(r"арзан|бюджет|тиімді|дешев|недорог|cheap|budget", t):
        f["max_price"] = round(float(get_rooms()["price_per_night"].quantile(0.25)) / 5) * 5
    elif "min_price" not in f and re.search(r"қымбат|премиум|дорог|expensive|premium", t):
        f["min_price"] = round(float(get_rooms()["price_per_night"].quantile(0.75)) / 5) * 5
    if f:
        return f, "filter"
    if re.search(r"рахмет|спасибо|thank", t): return {}, "thanks"
    if re.search(r"көмек|помощь|помоги|help|что умеешь|не істей", t): return {}, "help"
    if re.search(r"^\s*(сәлем|салем|сәлеметсіз|привет|здравствуй|добрый|hello|hi|hey)", t): return {}, "greet"
    return {}, "unknown"


def free_rooms(filters: dict, ci: date, co: date) -> pd.DataFrame:
    d, busy, _, _ = with_prices(get_rooms(), ci, co)
    res = apply_filters(d, filters)
    return res[~res["id"].isin(busy)]


def summarize(filters: dict, ci: date, co: date, lang: str) -> str:
    T, res = TXT[lang], free_rooms(filters, ci, co)
    if res.empty:
        return T["none"]
    head = T["found"].format(n=len(res), lo=f"{res.price_now.min():.0f}", hi=f"{res.price_now.max():.0f}")
    top = res.sort_values("price_now").head(3)
    lines = [f"- **№{r.room_number}** · {r.category} · ${r.price_now:.0f}{' · 🌅' if r.has_balcony else ''}"
             for r in top.itertuples()]
    return head + "\n" + "\n".join(lines)


# ───────────────────────────── ИИ (Claude, опционально) ─────────────────────────────
SEARCH_TOOL = {
    "name": "search_rooms",
    "description": ("Применить фильтры к каталогу номеров. Вызывай, когда гость называет пожелания. "
                    "Передавай ПОЛНЫЙ набор критериев, который должен действовать сейчас (с учётом диалога); "
                    "лишнее не указывай. reset=true сбрасывает фильтры."),
    "input_schema": {"type": "object", "properties": {
        "floor": {"type": "integer", "minimum": 1, "maximum": 10, "description": "Этаж; пентхаус = 10"},
        "room_number": {"type": "integer"}, "min_capacity": {"type": "integer", "minimum": 1, "maximum": 5},
        "min_price": {"type": "number"}, "max_price": {"type": "number"}, "has_balcony": {"type": "boolean"},
        "category": {"type": "string", "description": "Standard, Deluxe, Suite, Single, Double, Twin, Triple, "
                     "King, Ocean View, Quiet Zone, Family, Executive, Presidential"},
        "reset": {"type": "boolean"}}},
}


def get_api_key():
    try:
        key = st.secrets.get("ANTHROPIC_API_KEY")
    except Exception:
        key = None
    return key or os.getenv("ANTHROPIC_API_KEY")


def ai_available() -> bool:
    return anthropic is not None and bool(get_api_key())


def ask_ai(history, text, d):
    system = (f"Ты — ИИ-консьерж отеля TRYP by Wyndham. Сегодня {date.today().isoformat()}. "
              f"Каталог: {len(d)} номеров, 10 этажей (10-й — пентхаус), цены ${d.price_per_night.min():.0f}–"
              f"${d.price_per_night.max():.0f}/ночь, вместимость 1–5, категории Standard/Deluxe/Suite/Executive/"
              "Presidential. С 3-го этажа у всех номеров есть балкон. Отвечай на языке гостя (kk/ru/en), 1–2 "
              "предложения. При пожеланиях вызывай search_rooms; не выдумывай цены и наличие. Бронирование — "
              "кнопкой на карточке после входа и выбора дат.")
    client = anthropic.Anthropic(api_key=get_api_key(), timeout=30.0)
    msgs = [{"role": m["role"], "content": m["content"]} for m in history[-10:]] + [{"role": "user", "content": text}]
    resp = client.messages.create(model=MODEL, max_tokens=500, system=system, tools=[SEARCH_TOOL], messages=msgs)
    reply = "".join(b.text for b in resp.content if b.type == "text").strip()
    flt = next((dict(b.input) for b in resp.content if b.type == "tool_use"), None)
    return reply, flt


def handle_message(text: str, ci: date, co: date):
    ss = st.session_state
    lang = detect_lang(text, ss.get("lang", "ru"))
    ss.lang, T = lang, TXT[lang]
    reply, new, intent, replace = "", None, "filter", False

    if ai_available():
        try:
            reply, flt = ask_ai(ss.chat_history, text, get_rooms())
            new, intent, replace = (flt or {}), ("filter" if flt is not None else "chat"), True
        except Exception:
            reply = T["fail"] + "\n\n"
    if new is None:  # офлайн-движок (нет ключа или сбой API)
        new, intent = local_parse(text)
        if intent in ("greet", "thanks", "help", "reset", "unknown"):
            reply += T[intent] + ("\n\n" + T["help"] if intent == "greet" else "")

    if new.pop("reset", False) or intent == "reset":
        ss.filters = {}
    if new:
        ss.filters = new if replace else {**ss.filters, **new}
    if intent == "filter":
        reply = (reply + "\n\n" if reply.strip() else "") + summarize(ss.filters, ci, co, lang)
    ss.chat_history += [{"role": "user", "content": text}, {"role": "assistant", "content": reply or T["unknown"]}]


# ───────────────────────────── СЕССИЯ ─────────────────────────────
for k, v in {"logged_in": False, "username": "", "full_name": "", "chat_history": [],
             "filters": {}, "flash": None, "lang": "kk", "role": "user", "view": "Каталог"}.items():
    st.session_state.setdefault(k, v)

df = get_rooms()

# ───────────────────────────── САЙДБАР ─────────────────────────────
sb = st.sidebar
sb.markdown("## 👤 Жеке Кабинет")

if not st.session_state.logged_in:
    mode = sb.radio("Мәзір:", ["Кіру", "Тіркелу"])
    if mode == "Тіркелу":
        reg_user = sb.text_input("Логин (Email немесе Nick):", key="reg_u")
        reg_pass = sb.text_input("Құпия сөз (кемінде 6 таңба):", type="password", key="reg_p")
        reg_name = sb.text_input("Аты-жөніңіз:", key="reg_n")
        reg_phone = sb.text_input("Телефон нөміріңіз:", key="reg_ph")
        if sb.button("Тіркелуді аяқтау"):
            if not (reg_user and reg_pass and reg_name):
                sb.warning("Барлық міндетті өрістерді толтырыңыз!")
            elif len(reg_pass) < 6:
                sb.warning("Құпия сөз тым қысқа (кемінде 6 таңба).")
            else:
                try:
                    with db() as c:
                        c.execute("INSERT INTO users (username, password, full_name, phone) VALUES (?,?,?,?)",
                                  (reg_user.strip(), hash_password(reg_pass), reg_name.strip(), reg_phone.strip()))
                    sb.success("✅ Сәтті тіркелдіңіз! Енді 'Кіру' арқылы кіріңіз.")
                except sqlite3.IntegrityError:
                    sb.error("⚠ Бұл логин қазірдің өзінде тіркелген!")
    else:
        log_user = sb.text_input("Логин:", key="log_u")
        log_pass = sb.text_input("Құпия сөз:", type="password", key="log_p")
        if sb.button("Жүйеге кіру"):
            with db() as c:
                user = c.execute("SELECT full_name, password, role FROM users WHERE username=?",
                                 (log_user.strip(),)).fetchone()
                if user and verify_password(log_pass, user["password"]):
                    if "$" not in user["password"]:
                        c.execute("UPDATE users SET password=? WHERE username=?",
                                  (hash_password(log_pass), log_user.strip()))
                    st.session_state.update(logged_in=True, username=log_user.strip(), full_name=user["full_name"],
                                            role=user["role"] or "user")
                    st.rerun()
                else:
                    sb.error("❌ Логин немесе пароль қате!")
else:
    sb.success(f"Қош келдіңіз, **{st.session_state.full_name}**!")
    if st.session_state.role == "admin":
        sb.radio("Бөлім:", ["Каталог", "Админ-панель"], key="view")
    sb.markdown("### 📋 Менің брондауларым")
    with db() as c:
        my = c.execute("""SELECT id, room_type, price, check_in, check_out, booking_date FROM bookings
                          WHERE username=? ORDER BY id DESC""", (st.session_state.username,)).fetchall()
    if my:
        for b in my:
            if b["check_in"]:
                n = (date.fromisoformat(b["check_out"]) - date.fromisoformat(b["check_in"])).days
                info = f"📅 {b['check_in']} → {b['check_out']} ({n} түн)\n💰 Барлығы: ${b['price'] * n:.2f}"
            else:
                info = f"💰 ${b['price']}  ·  📅 {str(b['booking_date'])[:10]}"
            sb.info(f"🛏️ **{b['room_type']}**\n{info}")
            if b["check_in"] and sb.button("Бас тарту", key=f"chip_cancel_{b['id']}"):
                with db() as c:
                    c.execute("DELETE FROM bookings WHERE id=? AND username=?", (b["id"], st.session_state.username))
                st.rerun()
    else:
        sb.write("Әзірге брондалған нөмірлеріңіз жоқ.")
    if sb.button("Шығу (Logout)"):
        st.session_state.update(logged_in=False, username="", full_name="", role="user")
        st.rerun()

sb.markdown("---")
sb.markdown("### 📅 Күндер")
check_in = sb.date_input("Келу күні:", value=date.today(), min_value=date.today())
check_out = sb.date_input("Кету күні:", value=date.today() + timedelta(days=1),
                          min_value=date.today() + timedelta(days=1))
dates_ok = check_out > check_in
if not dates_ok:
    sb.error("Кету күні келу күнінен кейін болуы керек.")
nights = max((check_out - check_in).days, 1)

sb.markdown("### 🎛️ Сүзгілер")
filter_balcony = sb.selectbox("Балкон:", ["Барлығы", "Балконы бар", "Балконы жоқ"])
p_lo = int(df["price_per_night"].min() * 0.8 // 10 * 10)
p_hi = int(df["price_per_night"].max() * 1.5 // 10 * 10 + 10)
max_price = sb.slider("Максималды баға ($ / түн):", p_lo, p_hi, p_hi)
only_free = sb.checkbox("Тек бос нөмірлер", value=True)


# ───────────────────────────── ОКНО ИИ-АССИСТЕНТА ─────────────────────────────
def assistant_ui():
    ss = st.session_state
    T = TXT[ss.lang]
    online = ai_available()
    st.markdown(f'<div class="ai-status"><span class="dot {"" if online else "off"}"></span>'
                f'{T["on"] if online else T["off"]}</div>', unsafe_allow_html=True)

    box = st.container(height=330)

    chips = [("🏙️ 3-ші қабат", "3-ші қабат"), ("👨‍👩‍👧 Отбасыға", "4 адамға"), ("💸 Арзан", "арзан нөмір"),
             ("🌅 Балкон", "балконы бар"), ("👑 Люкс", "люкс"), ("♻️ Тазарту", "тазарту")]
    cols = st.columns(3)
    clicked = None
    for i, (label, query) in enumerate(chips):
        if cols[i % 3].button(label, key=f"chip_q{i}"):
            clicked = query

    with st.form("ai_form", clear_on_submit=True, border=False):
        typed = st.text_input("msg", placeholder=T["ph"], label_visibility="collapsed")
        sent = st.form_submit_button("➤")

    text = clicked or (typed.strip() if sent else "")
    if text:
        handle_message(text[:500], check_in, check_out)

    with box:
        T = TXT[ss.lang]
        if not ss.chat_history:
            st.chat_message("assistant").write(T["greet"] + "\n\n" + T["help"])
        for m in ss.chat_history[-14:]:
            st.chat_message(m["role"]).write(m["content"])

    n = len(free_rooms(ss.filters, check_in, check_out))
    if st.button(T["apply"].format(n=n), key="ai_apply"):
        st.rerun()  # закрывает окно и применяет фильтры к каталогу


if hasattr(st, "dialog"):
    assistant_dialog = st.dialog("🤖 ИИ Ассистент", width="large")(assistant_ui)
    if st.button("🤖  ИИ Ассистент", key="ai_fab"):
        assistant_dialog()
else:  # старый Streamlit — показываем в раскрывающемся блоке
    with st.expander("🤖 ИИ Ассистент", expanded=False):
        assistant_ui()

# ───────────────────────────── АДМИН-ПАНЕЛЬ ─────────────────────────────
def admin_panel():
    me = st.session_state.username
    with db() as c:  # роль перепроверяем в БД, а не только в сессии
        r = c.execute("SELECT role FROM users WHERE username=?", (me,)).fetchone()
    if not r or r["role"] != "admin":
        st.error("Қол жеткізуге рұқсат жоқ.")
        return

    st.markdown('<div class="hero"><div class="hero-badge">ADMIN</div><h1>Әкімші панелі</h1>'
                '<p>Барлық пайдаланушылар мен брондауларды басқару.</p></div>', unsafe_allow_html=True)
    if st.session_state.flash:
        st.success(st.session_state.flash)
        st.session_state.flash = None

    with db() as c:
        users = pd.read_sql_query("""SELECT u.id, u.username, u.full_name, u.phone,
                COALESCE(u.role,'user') AS role, COUNT(b.id) AS bookings
                FROM users u LEFT JOIN bookings b ON b.username=u.username GROUP BY u.id ORDER BY u.id""", c)
        bk = pd.read_sql_query("""SELECT b.id, b.username, u.full_name, b.room_type, b.check_in, b.check_out,
                b.price AS price_per_night, b.booking_date FROM bookings b
                LEFT JOIN users u ON u.username=b.username ORDER BY b.id DESC""", c)
    if not bk.empty:
        bk["total"] = bk.apply(lambda x: x["price_per_night"] * (
            (date.fromisoformat(x["check_out"]) - date.fromisoformat(x["check_in"])).days) if x["check_in"]
            else x["price_per_night"], axis=1)
    revenue = float(bk["total"].sum()) if not bk.empty else 0.0
    m1, m2, m3 = st.columns(3)
    m1.metric("Пайдаланушылар", len(users))
    m2.metric("Брондаулар", len(bk))
    m3.metric("Жалпы сома", f"${revenue:,.0f}")

    t_users, t_book = st.tabs(["👥 Пайдаланушылар", "📖 Брондаулар"])

    with t_users:
        st.dataframe(users, hide_index=True)
        st.download_button("⬇ CSV жүктеу", users.to_csv(index=False).encode("utf-8-sig"), "users.csv", "text/csv")
        st.markdown("#### Басқару")
        sel = st.selectbox("Пайдаланушы:", users["username"], key="adm_sel")
        row = users[users["username"] == sel].iloc[0]
        c1, c2 = st.columns(2)
        with c1:
            new_pw = st.text_input("Жаңа құпия сөз (кемінде 6 таңба):", type="password", key="adm_pw")
            if st.button("🔑 Құпия сөзді ауыстыру", key="adm_resetpw"):
                if len(new_pw) < 6:
                    st.warning("Құпия сөз тым қысқа.")
                else:
                    with db() as c:
                        c.execute("UPDATE users SET password=? WHERE username=?", (hash_password(new_pw), sel))
                    st.success(f"{sel}: құпия сөз жаңартылды.")
        with c2:
            role_new = st.selectbox("Рөл:", ["user", "admin"], index=0 if row["role"] == "user" else 1,
                                    key=f"adm_role_{sel}")
            if st.button("💾 Рөлді сақтау", key="adm_saverole"):
                if sel == me and role_new != "admin":
                    st.error("Өзіңіздің әкімші рөліңізді алып тастауға болмайды.")
                else:
                    with db() as c:
                        c.execute("UPDATE users SET role=? WHERE username=?", (role_new, sel))
                    st.session_state.flash = f"{sel}: рөл → {role_new}"
                    st.rerun()
        confirm = st.checkbox(f"**{sel}** пайдаланушысын және оның брондауларын жоюды растаймын", key=f"adm_del_{sel}")
        if st.button("🗑 Пайдаланушыны жою", key="adm_delete", disabled=(not confirm) or sel == me):
            with db() as c:
                c.execute("DELETE FROM bookings WHERE username=?", (sel,))
                c.execute("DELETE FROM users WHERE username=?", (sel,))
            st.session_state.flash = f"{sel} жойылды."
            st.rerun()

    with t_book:
        st.dataframe(bk, hide_index=True)
        if not bk.empty:
            st.download_button("⬇ CSV жүктеу", bk.to_csv(index=False).encode("utf-8-sig"), "bookings.csv", "text/csv")
            bid = st.selectbox("Брондау ID:", bk["id"], key="adm_bid")
            if st.button("❌ Брондауды бас тарту", key="adm_cancel"):
                with db() as c:
                    c.execute("DELETE FROM bookings WHERE id=?", (int(bid),))
                st.session_state.flash = f"Брондау #{bid} жойылды."
                st.rerun()


if st.session_state.logged_in and st.session_state.role == "admin" and st.session_state.view == "Админ-панель":
    admin_panel()
    st.stop()

# ───────────────────────────── ГЛАВНАЯ СТРАНИЦА ─────────────────────────────
df_p, busy_ids, price_mult, price_parts = with_prices(df, check_in, check_out)

st.markdown(f"""
<div class="hero">
  <div class="hero-badge">TRYP BY WYNDHAM · BRONDAU</div>
  <h1>Өзіңізге лайық нөмірді<br>бір минутта табыңыз</h1>
  <p>Қабат, санат, баға және балкон бойынша сүзіңіз немесе ИИ ассистентке өз тілімен жазыңыз.</p>
  <div class="stats">
    <div class="stat"><b>{len(df)}</b><span>нөмір</span></div>
    <div class="stat"><b>{df['floor'].nunique()}</b><span>қабат</span></div>
    <div class="stat"><b>${df_p['price_now'].min():.0f}</b><span>бастап / түн</span></div>
    <div class="stat"><b>{nights}</b><span>түн таңдалды</span></div>
  </div>
</div>""", unsafe_allow_html=True)

if st.session_state.flash:
    st.success(st.session_state.flash)
    st.session_state.flash = None

filtered = df_p[df_p["price_now"] <= max_price]
if filter_balcony == "Балконы бар":
    filtered = filtered[filtered["has_balcony"] == 1]
elif filter_balcony == "Балконы жоқ":
    filtered = filtered[filtered["has_balcony"] == 0]

if st.session_state.filters:
    filtered = apply_filters(filtered, st.session_state.filters)
    pc1, pc2 = st.columns([5, 1])
    pc1.markdown(f'<div class="pills"><span class="pill">🤖 ИИ сүзгілері</span>'
                 f'{filter_pills(st.session_state.filters)}</div>', unsafe_allow_html=True)
    if pc2.button("✕ Тазарту", key="chip_clear"):
        st.session_state.filters = {}
        st.rerun()

if only_free:
    filtered = filtered[~filtered["id"].isin(busy_ids)]

if price_parts:
    st.markdown('<div class="pills"><span class="pill">💡 Баға факторлары</span>'
                + "".join(f'<span class="pill">{html.escape(x)}</span>' for x in price_parts)
                + f'<span class="pill">Σ ×{price_mult:.2f}</span></div>', unsafe_allow_html=True)
st.markdown(f'<div class="result-head">🎯 Табылған нөмірлер: <b>{len(filtered)}</b></div>', unsafe_allow_html=True)

CAT_CLASS = [("Presidential", "pre"), ("Suite", "ste"), ("Deluxe", "dlx"), ("Standard", "std")]

if filtered.empty:
    st.warning("Бұл талаптарға сай нөмір табылмады. Сүзгілерді немесе күндерді өзгертіп көріңіз.")
else:
    cols = st.columns(2)
    for i, (_, row) in enumerate(filtered.reset_index(drop=True).iterrows()):
        with cols[i % 2]:
            cls = next((c for key, c in CAT_CLASS if key in row["category"]), "std")
            is_busy = row["id"] in busy_ids
            status = '<span class="rc-status busy">● Бос емес</span>' if is_busy else '<span class="rc-status free">● Бос</span>'
            balc = "🌅 Балкон" if row["has_balcony"] == 1 else "Балконсыз"
            st.markdown(f"""
            <div class="room-card cat-{cls}">
              <div class="rc-top"><span class="rc-num">№{row['room_number']}</span>
                <span class="rc-cat">{html.escape(row['category'])}</span>{status}</div>
              <div class="room-desc">{html.escape(str(row['description']))}</div>
              <div class="badges"><span class="badge">👥 {row['capacity']} адам</span>
                <span class="badge">🏢 {row['floor']}-қабат</span><span class="badge">{balc}</span></div>
              <div class="rc-price"><span class="amt">${row['price_now']:.0f}</span><span class="per">/ түн</span>
                <span class="tot">{nights} түн · ${row['price_now'] * nights:.0f}</span></div>
            </div>""", unsafe_allow_html=True)

            if not st.session_state.logged_in:
                st.button("🔒 Брондау үшін жүйеге кіріңіз", key=f"disabled_{row['id']}", disabled=True)
            elif st.button(f"Брондау · №{row['room_number']}", key=f"book_{row['id']}",
                           disabled=(not dates_ok) or is_busy):
                if book_room(st.session_state.username, row, check_in, check_out, float(row["price_now"])):
                    st.session_state.flash = (f"🎉 {st.session_state.full_name}, сіз **{row['room_type']}** "
                                              f"нөмірін {check_in} → {check_out} аралығына брондадыңыз.")
                else:
                    st.session_state.flash = "⚠ Кешіріңіз, бұл нөмір осы күндерге жаңа ғана брондалды."
                st.rerun()
            st.write("")