-- ============================================================
-- Run this once on your MySQL server to create all agent schemas
-- and grant the application user access to each.
--
--   mysql -u root -p < scripts/create_schemas.sql
-- ============================================================

CREATE DATABASE IF NOT EXISTS cs03_vehicle    CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE DATABASE IF NOT EXISTS cs03_warranty   CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE DATABASE IF NOT EXISTS cs03_scheduler  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE DATABASE IF NOT EXISTS cs03_telematics CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE DATABASE IF NOT EXISTS cs03_auth       CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE DATABASE IF NOT EXISTS cs03_agent      CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE DATABASE IF NOT EXISTS cs03_insurance  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- Grant cs03_user access to all schemas
-- Replace 'admin' with your actual password
CREATE USER IF NOT EXISTS 'cs03_user'@'localhost' IDENTIFIED BY 'admin';

GRANT ALL PRIVILEGES ON cs03_vehicle.*    TO 'cs03_user'@'localhost';
GRANT ALL PRIVILEGES ON cs03_warranty.*   TO 'cs03_user'@'localhost';
GRANT ALL PRIVILEGES ON cs03_scheduler.*  TO 'cs03_user'@'localhost';
GRANT ALL PRIVILEGES ON cs03_telematics.* TO 'cs03_user'@'localhost';
GRANT ALL PRIVILEGES ON cs03_auth.*       TO 'cs03_user'@'localhost';
GRANT ALL PRIVILEGES ON cs03_agent.*      TO 'cs03_user'@'localhost';
GRANT ALL PRIVILEGES ON cs03_insurance.*  TO 'cs03_user'@'localhost';

FLUSH PRIVILEGES;

SELECT 'All schemas created and permissions granted.' AS status;
