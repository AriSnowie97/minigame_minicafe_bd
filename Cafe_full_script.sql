-- =========================================================
-- Фізична модель бази даних "Cafe"
-- Лабораторна робота №1. Варіант 26 — Кафе
-- =========================================================

-- Створюємо базу даних Cafe
USE master;
GO
CREATE DATABASE Cafe;
GO

-- Вибираємо базу даних для подальшої роботи
USE Cafe;
GO

-- Створення таблиці MenuCategories (Категорії меню)
CREATE TABLE MenuCategories (
    ID   INT PRIMARY KEY,
    Name NVARCHAR(50) NOT NULL UNIQUE
);
GO

-- Створення таблиці Products (Продукти / інгредієнти)
CREATE TABLE Products (
    ID            INT PRIMARY KEY,
    Name          NVARCHAR(50) NOT NULL UNIQUE,
    Unit          NVARCHAR(10) NOT NULL,
    UnitPrice     DECIMAL(8, 2) NOT NULL CHECK (UnitPrice > 0),
    ShelfLifeDays INT NULL
);
GO

-- Створення таблиці Suppliers (Постачальники)
CREATE TABLE Suppliers (
    ID    INT PRIMARY KEY,
    Name  NVARCHAR(100) NOT NULL UNIQUE,
    Phone NVARCHAR(20) NOT NULL UNIQUE,
    City  NVARCHAR(50) NOT NULL
);
GO

-- Створення таблиці Deliveries (Поставки) — асоціація Suppliers <-> Products
CREATE TABLE Deliveries (
    ID           INT PRIMARY KEY,
    SupplierID   INT NOT NULL,
    ProductID    INT NOT NULL,
    Quantity     DECIMAL(8, 3) NOT NULL CHECK (Quantity > 0),
    Price        DECIMAL(8, 2) NOT NULL CHECK (Price >= 0),
    DeliveryDate DATETIME NOT NULL,
    FOREIGN KEY (SupplierID) REFERENCES Suppliers(ID),
    FOREIGN KEY (ProductID) REFERENCES Products(ID),
    UNIQUE (SupplierID, ProductID, DeliveryDate)
);
GO

-- Створення таблиці MenuItems (Меню — страви і напої)
CREATE TABLE MenuItems (
    ID              INT PRIMARY KEY,
    Name            NVARCHAR(50) NOT NULL UNIQUE,
    CategoryID      INT NOT NULL,
    Price           DECIMAL(8, 2) NOT NULL CHECK (Price > 0),
    CookingTimeMin  INT NOT NULL CHECK (CookingTimeMin > 0),
    Recipe          NVARCHAR(MAX) NULL,
    FOREIGN KEY (CategoryID) REFERENCES MenuCategories(ID)
);
GO

-- Створення таблиці MenuItemIngredients (Склад страви) — асоціація MenuItems <-> Products
CREATE TABLE MenuItemIngredients (
    ID         INT PRIMARY KEY,
    MenuItemID INT NOT NULL,
    ProductID  INT NOT NULL,
    Quantity   DECIMAL(6, 3) NOT NULL CHECK (Quantity > 0),
    FOREIGN KEY (MenuItemID) REFERENCES MenuItems(ID) ON DELETE CASCADE,
    FOREIGN KEY (ProductID) REFERENCES Products(ID),
    UNIQUE (MenuItemID, ProductID)
);
GO

-- Створення таблиці CafeTables (Столики)
CREATE TABLE CafeTables (
    ID          INT PRIMARY KEY,
    TableNumber INT NOT NULL UNIQUE,
    Capacity    INT NOT NULL CHECK (Capacity > 0),
    Location    NVARCHAR(30) NULL
);
GO

-- Створення таблиці Employees (Співробітники)
CREATE TABLE Employees (
    ID       INT PRIMARY KEY,
    FullName NVARCHAR(100) NOT NULL,
    Position NVARCHAR(20) NOT NULL CHECK (Position IN (N'офіціант', N'бариста', N'кухар', N'адміністратор')),
    Phone    NVARCHAR(20) NOT NULL UNIQUE,
    HireDate DATE NOT NULL
);
GO

-- Створення таблиці Orders (Замовлення)
CREATE TABLE Orders (
    ID            INT PRIMARY KEY,
    TableID       INT NOT NULL,
    EmployeeID    INT NOT NULL,
    OrderDateTime DATETIME NOT NULL DEFAULT GETDATE(),
    Status        NVARCHAR(20) NOT NULL DEFAULT N'відкрито' CHECK (Status IN (N'відкрито', N'оплачено', N'скасовано')),
    FOREIGN KEY (TableID) REFERENCES CafeTables(ID),
    FOREIGN KEY (EmployeeID) REFERENCES Employees(ID)
);
GO

-- Створення таблиці OrderItems (Позиції замовлення) — асоціація Orders <-> MenuItems
CREATE TABLE OrderItems (
    ID           INT PRIMARY KEY,
    OrderID      INT NOT NULL,
    MenuItemID   INT NOT NULL,
    Quantity     INT NOT NULL CHECK (Quantity > 0),
    PriceAtOrder DECIMAL(8, 2) NOT NULL CHECK (PriceAtOrder > 0),
    FOREIGN KEY (OrderID) REFERENCES Orders(ID) ON DELETE CASCADE,
    FOREIGN KEY (MenuItemID) REFERENCES MenuItems(ID),
    UNIQUE (OrderID, MenuItemID)
);
GO
-- =========================================================
-- Наповнення бази даних Cafe тестовими даними
-- =========================================================
USE Cafe;
GO

-- Категорії меню
INSERT INTO MenuCategories (ID, Name) VALUES
(1, N'Напої'),
(2, N'Сніданки'),
(3, N'Основні страви'),
(4, N'Десерти'),
(5, N'Закуски');
GO

-- Продукти
INSERT INTO Products (ID, Name, Unit, UnitPrice, ShelfLifeDays) VALUES
(1,  N'Кава в зернах',      N'кг', 450.00, 365),
(2,  N'Молоко',             N'л',  35.00,  7),
(3,  N'Чайне листя',        N'кг', 300.00, 540),
(4,  N'Яйця',               N'шт', 4.50,   21),
(5,  N'Бекон',              N'кг', 220.00, 30),
(6,  N'Творог',             N'кг', 110.00, 10),
(7,  N'Куряче філе',        N'кг', 160.00, 5),
(8,  N'Салатний мікс',      N'кг', 90.00,  5),
(9,  N'Помідори чері',      N'кг', 80.00,  7),
(10, N'Хліб',               N'шт', 25.00,  3),
(11, N'Маскарпоне',         N'кг', 280.00, 14),
(12, N'Печиво Савоярді',    N'кг', 200.00, 180);
GO

-- Постачальники
INSERT INTO Suppliers (ID, Name, Phone, City) VALUES
(1, N'ТОВ "Кавовий Дім"',      N'+380671112233', N'Київ'),
(2, N'ФОП "Молочна Ферма"',    N'+380502223344', N'Біла Церква'),
(3, N'ТОВ "Свіжі Продукти"',   N'+380631234567', N'Київ');
GO

-- Поставки
INSERT INTO Deliveries (ID, SupplierID, ProductID, Quantity, Price, DeliveryDate) VALUES
(1, 1, 1,  20.000, 9000.00, '2026-08-01'),
(2, 2, 2,  100.000, 3500.00, '2026-08-02'),
(3, 1, 3,  5.000,  1500.00, '2026-08-02'),
(4, 3, 4,  500.000, 2250.00, '2026-08-03'),
(5, 3, 8,  15.000, 1350.00, '2026-08-04'),
(6, 3, 9,  10.000, 800.00,  '2026-08-04'),
(7, 2, 6,  8.000,  880.00,  '2026-08-05'),
(8, 3, 7,  25.000, 4000.00, '2026-08-05');
GO

-- Меню (страви і напої)
INSERT INTO MenuItems (ID, Name, CategoryID, Price, CookingTimeMin, Recipe) VALUES
(1, N'Капучино',              1, 65.00,  5,  N'Еспресо, збите молоко.'),
(2, N'Лате',                  1, 70.00,  5,  N'Еспресо, велика частка молока.'),
(3, N'Чай чорний',            1, 40.00,  3,  N'Заварити чайне листя окропом.'),
(4, N'Сирники зі сметаною',   2, 95.00,  12, N'Обсмажити сирники з творогу, подати зі сметаною.'),
(5, N'Омлет з беконом',       2, 110.00, 10, N'Збити яйця, обсмажити з беконом.'),
(6, N'Салат "Цезар"',         3, 150.00, 15, N'Куряче філе, салатний мікс, соус, сухарики.'),
(7, N'Борщ український',      3, 120.00, 20, N'Традиційний борщ з м''ясним бульйоном.'),
(8, N'Тірамісу',              4, 130.00, 8,  N'Маскарпоне, печиво Савоярді, кава.'),
(9, N'Брускета з томатами',   5, 85.00,  7,  N'Хліб, помідори чері, спеції.');
GO

-- Склад страв (використані продукти на 1 порцію)
INSERT INTO MenuItemIngredients (ID, MenuItemID, ProductID, Quantity) VALUES
(1,  1, 1, 0.018),
(2,  1, 2, 0.100),
(3,  2, 1, 0.018),
(4,  2, 2, 0.180),
(5,  3, 3, 0.005),
(6,  4, 6, 0.200),
(7,  4, 4, 0.050),
(8,  5, 4, 0.150),
(9,  5, 5, 0.080),
(10, 6, 7, 0.150),
(11, 6, 8, 0.100),
(12, 7, 7, 0.100),
(13, 7, 9, 0.050),
(14, 8, 11, 0.120),
(15, 8, 12, 0.060),
(16, 9, 10, 0.100),
(17, 9, 9, 0.080);
GO

-- Столики
INSERT INTO CafeTables (ID, TableNumber, Capacity, Location) VALUES
(1, 1, 2, N'зал'),
(2, 2, 2, N'зал'),
(3, 3, 4, N'зал'),
(4, 4, 4, N'тераса'),
(5, 5, 6, N'тераса'),
(6, 6, 2, N'зал');
GO

-- Співробітники
INSERT INTO Employees (ID, FullName, Position, Phone, HireDate) VALUES
(1, N'Коваленко Ірина',   N'бариста',       N'+380671000001', '2024-03-01'),
(2, N'Петренко Олег',     N'офіціант',      N'+380671000002', '2024-05-15'),
(3, N'Сидоренко Марія',   N'кухар',         N'+380671000003', '2023-11-20'),
(4, N'Бондаренко Андрій', N'адміністратор', N'+380671000004', '2022-09-10');
GO

-- Замовлення
INSERT INTO Orders (ID, TableID, EmployeeID, OrderDateTime, Status) VALUES
(1, 1, 2, '2026-09-01 10:15:00', N'оплачено'),
(2, 3, 2, '2026-09-01 12:40:00', N'оплачено'),
(3, 4, 2, '2026-09-01 13:05:00', N'відкрито'),
(4, 2, 1, '2026-09-02 09:20:00', N'оплачено'),
(5, 5, 2, '2026-09-02 19:30:00', N'скасовано');
GO

-- Позиції замовлень
INSERT INTO OrderItems (ID, OrderID, MenuItemID, Quantity, PriceAtOrder) VALUES
(1,  1, 1, 2, 65.00),
(2,  1, 4, 1, 95.00),
(3,  2, 6, 1, 150.00),
(4,  2, 3, 2, 40.00),
(5,  2, 8, 1, 130.00),
(6,  3, 7, 2, 120.00),
(7,  3, 9, 1, 85.00),
(8,  4, 2, 1, 70.00),
(9,  4, 5, 1, 110.00),
(10, 5, 1, 3, 65.00);
GO
