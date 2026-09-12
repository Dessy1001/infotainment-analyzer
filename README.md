# Информационна система за анализ на инфотейнмънт системи

Практическа част към дипломна теза: „Информационна система за анализ на
инфотеймънт системи в хибридни и електромобили".

## Стек
- **Бекенд:** Python 3.11+, FastAPI, Uvicorn, SQLAlchemy 2.0 (typed ORM, `Mapped[...]`), Pydantic 2
- **База данни:** PostgreSQL (задължителна - виж настройка по-долу)
- **MCDA логика:** NumPy — собствена имплементация на WSM, AHP, TOPSIS (`app/backend/mcda.py`)
- **Фронтенд:** Jinja2 темплейти + чист HTML/CSS/vanilla JS (ES модули, без React/build стъпки) + Chart.js за визуализация

## Структура на проекта
```
infotainment_analyzer/
├── app/
│   ├── main.py             # Тънка входна точка: създава FastAPI app, включва routes
│   ├── backend/
│   │   ├── database.py      # SQLAlchemy engine/session (DeclarativeBase, PostgreSQL)
│   │   ├── routes.py         # Всички HTTP маршрути (изнесени от main.py)
│   │   ├── schemas.py        # Pydantic схеми (request/response валидация)
│   │   ├── mcda.py            # WSM / AHP / TOPSIS имплементации
│   │   └── seed_data.py      # Примерни данни за 32 реални модела
│   ├── models/
│   │   └── db_models.py      # ORM модели (Manufacturer, CarModel, InfotainmentSpec)
│   └── frontend/
│       ├── templates/         # index.html, results.html
│       └── static/
│           ├── style.css
│           └── js/             # api.js, state.js, render.js, modal.js, util.js, home.js, results.js
├── requirements.txt
├── .env.example
└── README.md
```

## Стартиране (локално)

Проектът изисква PostgreSQL - няма SQLite fallback.

**1. Създай база данни и роля** (веднъж, през `psql` или pgAdmin):
```sql
CREATE DATABASE car_infotainment_specs;
CREATE USER car_infotainment_specs_user WITH PASSWORD 'избери-парола';
GRANT ALL PRIVILEGES ON DATABASE car_infotainment_specs TO car_infotainment_specs_user;
\c car_infotainment_specs
GRANT ALL ON SCHEMA public TO car_infotainment_specs_user;
```

**2. Копирай `.env.example` на `.env`** и попълни `DATABASE_URL` с истинската парола:
```
DATABASE_URL=postgresql+psycopg2://car_infotainment_specs_user:избери-парола@localhost:5432/car_infotainment_specs
```
(`.env` не се качва в git.)

**3. Инсталирай зависимостите:**
```bash
cd infotainment_analyzer
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

**4. Зареди примерните данни** (еднократно; пропуска се автоматично, ако базата вече съдържа данни):
```bash
python -m app.backend.seed_data
```

**5. Стартирай сървъра:**
```bash
uvicorn app.main:app --reload
```
Отвори `http://127.0.0.1:8000` в браузър.

> Командите по-горе трябва да се изпълняват от корена на проекта
> (`infotainment_analyzer/`) - `main.py` сочи към `app/frontend/static` и
> `app/frontend/templates` с относителни пътища.

### Достъп от телефон/друго устройство в локалната мрежа
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
Компютърът и устройството трябва да са в една и съща WiFi мрежа. Разбери
локалния IP на компютъра (`ipconfig` на Windows, търси реда с `IPv4 Address`
под активния Wi-Fi/Ethernet адаптер) и отвори `http://<локален-IP>:8000` от
другото устройство. Ако не се отвори, най-честата причина е Windows Firewall
- разреши входящи връзки на порт 8000 (Windows Defender Firewall with
Advanced Security → Inbound Rules → New Rule → Port → TCP → 8000 → Allow).

> Забележка: `navigator.clipboard` (бутонът "Копирай линк") изисква "secure
> context" (HTTPS или `localhost`) - през `http://<локален-IP>` фронтендът
> автоматично пада обратно на `document.execCommand("copy")` (виж
> `static/js/home.js`), затова копирането работи и по локалната мрежа.

## Какво да довършиш за тезата
1. **Количествени/субективни показатели** — качествените/категорийните
   характеристики в `seed_data.py` (тип ОС, CarPlay/Android Auto, физически
   бутони, OTA и т.н.) са изведени от проучване по марки (лични изследователски
   бележки с цитирани източници - не се качват в git, виж `.gitignore`).
   Количествените/субективните показатели обаче (`startup_time_sec`,
   `reaction_time_ms`, `avg_steps_to_task`, `ease_of_use_score`,
   `ergonomics_score`, `safety_distraction_score`) остават примерни/оценъчни -
   само относителната им подредба между моделите на една марка е обоснована
   качествено. Замести ги с реални измервания и/или проведена анкета сред
   потребители (методологията ти вече споменава анкетен подход за
   субективните критерии).
2. **AHP с реална pairwise матрица** — сегашната имплементация третира
   избраните критерии като равностойни по важност (pairwise матрица от
   само единици), затова Consistency Ratio винаги излиза 0. За по-стриктно
   съответствие с класическия AHP метод можеш да добавиш отделен UI екран
   с директно въвеждане на pairwise сравнения (1-9 скала на Saaty) —
   функцията `ahp_weights()` в `mcda.py` вече приема готова матрица.
3. **Валидация/тестове** — добави `pytest` тестове за `mcda.py` (независим
   е от FastAPI/базата, лесно се тества изолирано).
