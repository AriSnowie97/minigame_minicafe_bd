-- =========================================================
-- MiniCafe: схема та початкові дані для PostgreSQL (Railway)
-- Можна запускати багато разів без шкоди (IF NOT EXISTS / ON CONFLICT DO NOTHING).
-- Назви таблиць і колонок збігаються із запитами в database/queries.py,
-- а ID страв і столиків — з тими, що використовує сама гра.
-- =========================================================

CREATE TABLE IF NOT EXISTS menucategories (
    id   INT PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS products (
    id            INT PRIMARY KEY,
    name          VARCHAR(50) NOT NULL UNIQUE,
    unit          VARCHAR(10) NOT NULL,
    unitprice     NUMERIC(8, 2) NOT NULL CHECK (unitprice > 0),
    shelflifedays INT
);

CREATE TABLE IF NOT EXISTS menuitems (
    id             INT PRIMARY KEY,
    name           VARCHAR(50) NOT NULL UNIQUE,
    categoryid     INT NOT NULL REFERENCES menucategories(id),
    price          NUMERIC(8, 2) NOT NULL CHECK (price > 0),
    cookingtimemin INT NOT NULL CHECK (cookingtimemin > 0),
    recipe         TEXT
);

CREATE TABLE IF NOT EXISTS menuitemingredients (
    id         INT PRIMARY KEY,
    menuitemid INT NOT NULL REFERENCES menuitems(id) ON DELETE CASCADE,
    productid  INT NOT NULL REFERENCES products(id),
    quantity   NUMERIC(6, 3) NOT NULL CHECK (quantity > 0),
    UNIQUE (menuitemid, productid)
);

CREATE TABLE IF NOT EXISTS cafetables (
    id          INT PRIMARY KEY,
    tablenumber INT NOT NULL UNIQUE,
    capacity    INT NOT NULL CHECK (capacity > 0),
    location    VARCHAR(30)
);

-- Персонал кафе — котики-персонажі гри
CREATE TABLE IF NOT EXISTS employees (
    id       INT PRIMARY KEY,
    fullname VARCHAR(100) NOT NULL,
    position VARCHAR(20) NOT NULL
);

-- Для баз, створених старою версією скрипта: прибираємо зайве (телефони, дати, «адміністратор»)
ALTER TABLE employees DROP COLUMN IF EXISTS phone;
ALTER TABLE employees DROP COLUMN IF EXISTS hiredate;
ALTER TABLE employees DROP CONSTRAINT IF EXISTS employees_position_check;
DELETE FROM employees WHERE id > 4;
ALTER TABLE employees ADD CONSTRAINT employees_position_check CHECK (position IN ('офіціант', 'бариста', 'кухар'));

CREATE TABLE IF NOT EXISTS orders (
    id            SERIAL PRIMARY KEY,
    tableid       INT NOT NULL REFERENCES cafetables(id),
    employeeid    INT NOT NULL REFERENCES employees(id),
    orderdatetime TIMESTAMP NOT NULL DEFAULT NOW(),
    status        VARCHAR(20) NOT NULL DEFAULT 'відкрито'
                  CHECK (status IN ('відкрито', 'оплачено', 'скасовано'))
);

-- Ігровий день, офіціант, який розніс замовлення, та окрас гостя-котика (для статистики)
ALTER TABLE orders ADD COLUMN IF NOT EXISTS gameday INT;
ALTER TABLE orders ADD COLUMN IF NOT EXISTS waiterid INT REFERENCES employees(id);
ALTER TABLE orders ADD COLUMN IF NOT EXISTS guestbreed VARCHAR(20);

CREATE TABLE IF NOT EXISTS orderitems (
    id           SERIAL PRIMARY KEY,
    orderid      INT NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    menuitemid   INT NOT NULL REFERENCES menuitems(id),
    quantity     INT NOT NULL CHECK (quantity > 0),
    priceatorder NUMERIC(8, 2) NOT NULL CHECK (priceatorder > 0),
    UNIQUE (orderid, menuitemid)
);

-- ---------------------------------------------------------
-- Початкові дані
-- ---------------------------------------------------------
INSERT INTO menucategories (id, name) VALUES
    (1, 'Напої'),
    (2, 'Випічка'),
    (3, 'Основні страви'),
    (4, 'Десерти'),
    (5, 'Закуски'),
    (6, 'Сніданки')
ON CONFLICT DO NOTHING;

INSERT INTO products (id, name, unit, unitprice, shelflifedays) VALUES
    (1,  'Кава в зернах',   'кг', 450.00, 365),
    (2,  'Молоко',          'л',  35.00,  7),
    (3,  'Чайне листя',     'кг', 300.00, 540),
    (4,  'Яйця',            'шт', 4.50,   21),
    (5,  'Бекон',           'кг', 220.00, 30),
    (6,  'Творог',          'кг', 110.00, 10),
    (7,  'Куряче філе',     'кг', 160.00, 5),
    (8,  'Салатний мікс',   'кг', 90.00,  5),
    (9,  'Помідори чері',   'кг', 80.00,  7),
    (10, 'Хліб',            'шт', 25.00,  3),
    (11, 'Маскарпоне',      'кг', 280.00, 14),
    (12, 'Печиво Савоярді', 'кг', 200.00, 180),
    (13, 'Борошно',         'кг', 30.00,  365),
    (14, 'Буряк',           'кг', 25.00,  30)
ON CONFLICT DO NOTHING;

-- Меню: id збігаються з ID страв у грі
INSERT INTO menuitems (id, name, categoryid, price, cookingtimemin, recipe) VALUES
    (1,  'Кава',            1, 50.00,  4, 'Еспресо у чашці.'),
    (2,  'Чай чорний',      1, 40.00,  3, 'Заварити чайне листя окропом.'),
    (3,  'Печиво',          2, 65.00,  5, 'Домашнє шоколадне печиво.'),
    (4,  'Айс лате',        1, 85.00,  6, 'Еспресо, холодне молоко, лід.'),
    (5,  'Тортик',          4, 110.00, 8, 'Святковий тортик з кремом.'),
    (6,  'Брускета',        5, 70.00,  5, 'Підсмажений хліб, помідори чері, спеції.'),
    (7,  'Сирники',         6, 90.00,  6, 'Обсмажити сирники з творогу.'),
    (8,  'Омлет з беконом', 6, 100.00, 7, 'Збити яйця, обсмажити з беконом.'),
    (9,  'Салат Цезар',     3, 105.00, 6, 'Куряче філе, салатний мікс, соус, сухарики.'),
    (10, 'Тірамісу',        4, 120.00, 7, 'Маскарпоне, печиво Савоярді, кава.'),
    (11, 'Борщ',            3, 130.00, 8, 'Традиційний борщ з буряком.'),
    (12, 'Лате',            1, 60.00,  4, 'Еспресо, велика частка молока.'),
    (13, 'Кава з собою',    1, 45.00,  3, 'Кава в паперовому стаканчику.'),
    (14, 'Круасан',         2, 55.00,  4, 'Свіжий хрусткий круасан.'),
    (15, 'Капучино',        1, 65.00,  4, 'Еспресо та збите молоко.')
ON CONFLICT DO NOTHING;

INSERT INTO menuitemingredients (id, menuitemid, productid, quantity) VALUES
    (1,  1,  1,  0.018),
    (2,  2,  3,  0.005),
    (3,  3,  13, 0.050),
    (4,  4,  1,  0.018),
    (5,  4,  2,  0.150),
    (6,  5,  13, 0.100),
    (7,  5,  4,  2.000),
    (8,  6,  10, 1.000),
    (9,  6,  9,  0.080),
    (10, 7,  6,  0.200),
    (11, 8,  4,  3.000),
    (12, 8,  5,  0.080),
    (13, 9,  7,  0.150),
    (14, 9,  8,  0.100),
    (15, 10, 11, 0.120),
    (16, 10, 12, 0.060),
    (17, 11, 14, 0.150),
    (18, 12, 1,  0.018),
    (19, 12, 2,  0.180),
    (20, 13, 1,  0.018),
    (21, 14, 13, 0.080),
    (22, 15, 1,  0.018),
    (23, 15, 2,  0.100)
ON CONFLICT DO NOTHING;

-- Столики: 1-4, 9, 10 — зал; 5-8 — тераса
INSERT INTO cafetables (id, tablenumber, capacity, location) VALUES
    (1,  1,  2, 'зал'),
    (2,  2,  2, 'зал'),
    (3,  3,  4, 'зал'),
    (4,  4,  4, 'зал'),
    (5,  5,  2, 'тераса'),
    (6,  6,  4, 'тераса'),
    (7,  7,  2, 'тераса'),
    (8,  8,  4, 'тераса'),
    (9,  9,  2, 'зал'),
    (10, 10, 2, 'зал')
ON CONFLICT DO NOTHING;

-- Співробітники: гра записує замовлення на того, хто готує (бариста або кухар), і на офіціанта, який його розніс
INSERT INTO employees (id, fullname, position) VALUES
    (1, 'Бариста Мура',     'бариста'),
    (2, 'Офіціант Мурлик',  'офіціант'),
    (3, 'Шеф-кухар Мурчик', 'кухар'),
    (4, 'Офіціант Пушок',   'офіціант')
ON CONFLICT (id) DO UPDATE SET fullname = EXCLUDED.fullname, position = EXCLUDED.position;
