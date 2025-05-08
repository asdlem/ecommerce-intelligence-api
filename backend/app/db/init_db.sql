-- 电商平台数据库初始化SQL
-- 创建必要的表并初始化基本数据

-- -----------------------------------------------------
-- 用户表
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    id INT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(100) UNIQUE,
    password VARCHAR(256) NOT NULL,
    phone VARCHAR(20),
    registration_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_login DATETIME,
    status VARCHAR(20) DEFAULT 'active',
    is_admin BOOLEAN DEFAULT false,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 默认管理员用户
INSERT INTO users (username, email, password, is_admin, status)
SELECT 'admin', 'admin@example.com', '$2b$12$tVN1bjLNcd7xNP0pczFqIeCYVLp.JntgBPYwYQ7i7FOjqVLIQjP0O', true, 'active'
WHERE NOT EXISTS (SELECT 1 FROM users WHERE username = 'admin');

-- 默认测试用户
INSERT INTO users (username, email, password, status)
SELECT 'test', 'test@example.com', '$2b$12$tVN1bjLNcd7xNP0pczFqIeCYVLp.JntgBPYwYQ7i7FOjqVLIQjP0O', 'active'
WHERE NOT EXISTS (SELECT 1 FROM users WHERE username = 'test');

-- -----------------------------------------------------
-- 产品类别表
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS categories (
    category_id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL,
    parent_id INT DEFAULT NULL,
    description TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (parent_id) REFERENCES categories(category_id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -----------------------------------------------------
-- 产品表
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS products (
    product_id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    category_id INT,
    price DECIMAL(10,2) NOT NULL,
    cost DECIMAL(10,2),
    inventory INT DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    status VARCHAR(20) DEFAULT 'active',
    FOREIGN KEY (category_id) REFERENCES categories(category_id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -----------------------------------------------------
-- 订单表
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS orders (
    order_id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT,
    order_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    total_amount DECIMAL(12,2) NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    shipping_address TEXT,
    payment_method VARCHAR(50),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -----------------------------------------------------
-- 订单项表
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS order_items (
    item_id INT PRIMARY KEY AUTO_INCREMENT,
    order_id INT,
    product_id INT,
    quantity INT NOT NULL,
    unit_price DECIMAL(10,2) NOT NULL,
    discount DECIMAL(10,2) DEFAULT 0,
    subtotal DECIMAL(10,2) NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (order_id) REFERENCES orders(order_id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(product_id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -----------------------------------------------------
-- 评价表
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS reviews (
    review_id INT PRIMARY KEY AUTO_INCREMENT,
    product_id INT,
    user_id INT,
    rating INT,
    comment TEXT,
    review_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    helpful_votes INT DEFAULT 0,
    FOREIGN KEY (product_id) REFERENCES products(product_id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -----------------------------------------------------
-- 库存历史表
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS inventory_history (
    history_id INT PRIMARY KEY AUTO_INCREMENT,
    product_id INT,
    change_amount INT NOT NULL,
    change_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    reason VARCHAR(100),
    operator VARCHAR(50),
    FOREIGN KEY (product_id) REFERENCES products(product_id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -----------------------------------------------------
-- 促销活动表
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS promotions (
    promotion_id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    discount_type VARCHAR(20) NOT NULL,
    discount_value DECIMAL(10,2) NOT NULL,
    start_date DATETIME NOT NULL,
    end_date DATETIME,
    active BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -----------------------------------------------------
-- 退货表
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS returns (
    return_id INT PRIMARY KEY AUTO_INCREMENT,
    order_id INT,
    product_id INT,
    return_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    quantity INT NOT NULL,
    reason TEXT,
    status VARCHAR(20) DEFAULT 'pending',
    refund_amount DECIMAL(10,2),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (order_id) REFERENCES orders(order_id) ON DELETE SET NULL,
    FOREIGN KEY (product_id) REFERENCES products(product_id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -----------------------------------------------------
-- 供应商表
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS suppliers (
    supplier_id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL,
    contact_person VARCHAR(50),
    email VARCHAR(100),
    phone VARCHAR(20),
    address TEXT,
    status VARCHAR(20) DEFAULT 'active',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -----------------------------------------------------
-- 查询历史表
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS query_history (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT,
    query TEXT NOT NULL,
    query_type VARCHAR(50) DEFAULT 'nl2sql',
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(20) DEFAULT 'success',
    model VARCHAR(50),
    processing_time FLOAT,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -----------------------------------------------------
-- 添加示例数据（产品类别）
-- -----------------------------------------------------
INSERT INTO categories (name, description) VALUES
('电子产品', '各类电子设备和数码产品'),
('服装', '各类服装和服饰'),
('家居', '家具和家居用品'),
('食品', '食品和饮料'),
('图书', '书籍、杂志和电子书');

-- -----------------------------------------------------
-- 电子产品子类别
-- -----------------------------------------------------
INSERT INTO categories (name, parent_id, description) VALUES
('智能手机', 1, '各类智能手机和配件'),
('电脑', 1, '台式电脑和笔记本电脑'),
('音频设备', 1, '耳机、音箱和其他音频产品');

-- -----------------------------------------------------
-- 服装子类别
-- -----------------------------------------------------
INSERT INTO categories (name, parent_id, description) VALUES
('男装', 2, '男士服装'),
('女装', 2, '女士服装'),
('童装', 2, '儿童服装');

-- -----------------------------------------------------
-- 产品示例数据
-- -----------------------------------------------------
INSERT INTO products (name, description, category_id, price, cost, inventory, status) VALUES
('智能手机A', '高性能智能手机，6.7英寸屏幕，超长续航', 6, 2599.00, 1800.00, 120, 'active'),
('无线耳机B', '高音质蓝牙耳机，主动降噪', 8, 699.00, 350.00, 85, 'active'),
('笔记本电脑C', '轻薄商务笔记本，16GB内存', 7, 5999.00, 4200.00, 45, 'active'),
('男士休闲T恤', '纯棉圆领短袖T恤', 9, 129.00, 40.00, 200, 'active'),
('女士连衣裙', '夏季轻薄连衣裙', 10, 239.00, 80.00, 150, 'active'),
('儿童夏季套装', '舒适透气夏季套装', 11, 159.00, 60.00, 100, 'active'),
('办公椅', '人体工学办公椅', 3, 899.00, 450.00, 30, 'active'),
('坚果礼盒', '混合坚果礼盒装', 4, 99.00, 40.00, 80, 'active'),
('经管类书籍', '畅销经管类书籍集合', 5, 159.00, 60.00, 50, 'active'),
('智能手表D', '多功能智能手表，支持心率监测', 6, 899.00, 500.00, 60, 'active');

-- -----------------------------------------------------
-- 创建订单示例数据
-- -----------------------------------------------------
-- 注意：需要确保用户id存在
INSERT INTO orders (user_id, order_date, total_amount, status, payment_method) VALUES
(1, '2023-09-01 10:30:00', 3298.00, 'delivered', '微信支付'),
(1, '2023-10-15 14:20:00', 1598.00, 'delivered', '支付宝'),
(2, '2023-11-20 09:45:00', 6298.00, 'shipped', '银行卡'),
(1, '2023-12-05 16:10:00', 388.00, 'processing', '微信支付'),
(2, '2024-01-10 11:25:00', 998.00, 'pending', '支付宝');

-- -----------------------------------------------------
-- 订单项示例数据
-- -----------------------------------------------------
INSERT INTO order_items (order_id, product_id, quantity, unit_price, subtotal) VALUES
(1, 1, 1, 2599.00, 2599.00),
(1, 2, 1, 699.00, 699.00),
(2, 4, 2, 129.00, 258.00),
(2, 5, 1, 239.00, 239.00),
(2, 8, 1, 99.00, 99.00),
(2, 9, 1, 159.00, 159.00),
(3, 3, 1, 5999.00, 5999.00),
(3, 2, 1, 699.00, 699.00),
(4, 4, 3, 129.00, 387.00),
(5, 7, 1, 899.00, 899.00),
(5, 8, 1, 99.00, 99.00);

-- -----------------------------------------------------
-- 评价表示例数据
-- -----------------------------------------------------
INSERT INTO reviews (product_id, user_id, rating, comment, review_date) VALUES
(1, 1, 5, '非常好用的手机，续航超级棒！', '2023-09-10 15:20:00'),
(2, 1, 4, '音质不错，降噪效果一般', '2023-09-10 15:30:00'),
(3, 2, 5, '轻薄便携，性能强劲', '2023-11-25 10:15:00'),
(4, 1, 4, '衣服质量很好，尺码偏小', '2023-10-20 18:30:00'),
(5, 2, 5, '面料舒适，款式好看', '2023-12-15 09:45:00'); 