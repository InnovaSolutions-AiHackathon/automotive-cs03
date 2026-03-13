CREATE DATABASE automotive_cs03 CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'cs03_user'@'localhost' IDENTIFIED BY 'cs03_pass';
GRANT ALL PRIVILEGES ON automotive_cs03.* TO 'cs03_user'@'localhost';
FLUSH PRIVILEGES;
USE automotive_cs03;

CREATE TABLE IF NOT EXISTS customers (
  id          INT AUTO_INCREMENT PRIMARY KEY,
  name        VARCHAR(100) NOT NULL,
  email       VARCHAR(150) UNIQUE NOT NULL,
  phone       VARCHAR(20),
  created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS vehicles (
  id              INT AUTO_INCREMENT PRIMARY KEY,
  vehicle_code    VARCHAR(20) UNIQUE NOT NULL,
  vin             VARCHAR(17) UNIQUE NOT NULL,
  make            VARCHAR(50) NOT NULL,
  model           VARCHAR(50) NOT NULL,
  year            INT NOT NULL,
  odometer        INT DEFAULT 0,
  purchase_date   DATE NOT NULL,
  customer_id     INT,
  fuel_level      INT DEFAULT 100,
  battery_voltage DECIMAL(4,2) DEFAULT 12.6,
  engine_temp     INT DEFAULT 90,
  oil_life        INT DEFAULT 100,
  FOREIGN KEY (customer_id) REFERENCES customers(id)
);

CREATE TABLE IF NOT EXISTS active_fault_codes (
  id         INT AUTO_INCREMENT PRIMARY KEY,
  vehicle_id INT NOT NULL,
  dtc_code   VARCHAR(10) NOT NULL,
  detected_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  resolved   BOOLEAN DEFAULT FALSE,
  FOREIGN KEY (vehicle_id) REFERENCES vehicles(id)
);

CREATE TABLE IF NOT EXISTS warranty_records (
  id               INT AUTO_INCREMENT PRIMARY KEY,
  vehicle_id       INT NOT NULL,
  coverage_type    VARCHAR(50) NOT NULL,
  start_date       DATE NOT NULL,
  end_date         DATE NOT NULL,
  mileage_limit    INT NOT NULL,
  is_extended      BOOLEAN DEFAULT FALSE,
  FOREIGN KEY (vehicle_id) REFERENCES vehicles(id)
);

CREATE TABLE IF NOT EXISTS service_appointments (
  id             INT AUTO_INCREMENT PRIMARY KEY,
  vehicle_id     INT NOT NULL,
  service_type   VARCHAR(100) NOT NULL,
  scheduled_date DATE NOT NULL,
  scheduled_time TIME NOT NULL,
  technician     VARCHAR(50),
  status         ENUM('pending','confirmed','in_progress','completed') DEFAULT 'pending',
  warranty_covered BOOLEAN DEFAULT FALSE,
  notes          TEXT,
  created_at     DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (vehicle_id) REFERENCES vehicles(id)
);

CREATE TABLE IF NOT EXISTS agent_sessions (
  id          INT AUTO_INCREMENT PRIMARY KEY,
  session_id  VARCHAR(100) UNIQUE NOT NULL,
  vehicle_id  VARCHAR(20),
  history_json LONGTEXT,
  updated_at  DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- Seed sample data
INSERT INTO customers (name, email, phone) VALUES
  ('John Smith', 'john@example.com', '555-0101'),
  ('Sarah Lee',  'sarah@example.com', '555-0102');

INSERT INTO vehicles (vehicle_code,vin,make,model,year,odometer,purchase_date,customer_id,fuel_level,battery_voltage,engine_temp,oil_life)
VALUES
  ('VH001','1HGBH41JXMN109186','Honda','Accord',2022,28500,'2022-06-15',1,65,12.4,92,45),
  ('VH002','2T1BURHE0JC034301','Toyota','Camry',2021,41200,'2021-03-10',2,80,12.6,88,70);

INSERT INTO active_fault_codes (vehicle_id,dtc_code) VALUES (1,'P0300'),(2,'P0171');

INSERT INTO warranty_records (vehicle_id,coverage_type,start_date,end_date,mileage_limit) VALUES
  (1,'bumper_to_bumper','2022-06-15','2025-06-15',36000),
  (1,'powertrain','2022-06-15','2027-06-15',60000);
  
  commit;