\getenv monitor_password POSTGRES_MONITOR_PASSWORD
\getenv workload_password POSTGRES_WORKLOAD_PASSWORD

CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

CREATE ROLE lab_monitor LOGIN PASSWORD :'monitor_password';
GRANT CONNECT ON DATABASE lab_network TO lab_monitor;
GRANT pg_monitor TO lab_monitor;
ALTER ROLE lab_monitor SET default_transaction_read_only = on;

CREATE ROLE lab_workload LOGIN PASSWORD :'workload_password';
GRANT CONNECT ON DATABASE lab_network TO lab_workload;
GRANT USAGE ON SCHEMA public TO lab_monitor, lab_workload;

CREATE TABLE lab_items (id integer PRIMARY KEY, value bigint NOT NULL DEFAULT 0);
INSERT INTO lab_items (id) SELECT generate_series(1, 1000);
GRANT SELECT, UPDATE ON lab_items TO lab_workload;

COMMENT ON TABLE lab_items IS 'Carga real limitada a 1000 registros para demonstração acadêmica';

CREATE TABLE IF NOT EXISTS store_products (
    slug TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    description TEXT NOT NULL,
    specs TEXT NOT NULL,
    price_cents INTEGER NOT NULL CHECK (price_cents > 0),
    stock INTEGER NOT NULL CHECK (stock >= 0),
    image_key TEXT NOT NULL
);

INSERT INTO store_products (slug, name, category, description, specs, price_cents, stock, image_key) VALUES
    ('steam-deck-oled-512', 'Valve Steam Deck OLED 512GB', 'Consoles', 'Console portátil PC com tela HDR OLED de 7,4", bateria de longa duração e controles hápticos.', '7.4" OLED 90Hz · 512GB NVMe · Wi-Fi 6E', 449900, 8, 'steamdeck'),
    ('nintendo-switch-oled', 'Nintendo Switch OLED Branco 64GB', 'Consoles', 'Console híbrido portátil e de mesa com tela OLED vibrante e dock com porta Ethernet RJ-45.', 'Tela OLED 7" · 64GB · Dock LAN RJ-45', 219900, 14, 'switcholed'),
    ('anbernic-rg35xx-plus', 'Anbernic RG35XX Plus Retrô 64GB', 'Consoles', 'Portátil retrô clássico para sistemas 8-bit, 16-bit e PS1 com Wi-Fi 5G e saída mini-HDMI.', 'IPS 3.5" 640x480 · Wi-Fi 5G · 3300mAh', 47900, 19, 'rg35xx'),
    ('8bitdo-sn30-pro', 'Controle 8BitDo SN30 Pro Bluetooth', 'Controles', 'Controle retrô clássico com analógicos Hall Effect, D-pad preciso e vibração rumble.', 'Hall Effect · USB-C · Switch / PC / Android', 29900, 25, 'sn30pro'),
    ('dualsense-ps5-preto', 'Controle Sony DualSense Midnight Black', 'Controles', 'Controle oficial PlayStation 5 e PC com gatilhos adaptáveis e feedback háptico preciso.', 'Gatilhos Adaptáveis · Háptico · USB-C', 44900, 21, 'dualsense'),
    ('keychron-k2-pro', 'Teclado Mecânico Keychron K2 Pro QMK', 'Periféricos', 'Teclado mecânico 75% sem fio programável via QMK/VIA com keycaps PBT double-shot e RGB.', '75% Hot-Swap · Keycaps PBT · BT 5.1 / Cabo', 78900, 15, 'keychron'),
    ('logitech-g-pro-x2', 'Mouse Logitech G Pro X Superlight 2', 'Periféricos', 'Mouse gamer sem fio ultraleve para esports com sensor HERO 2 e switches LIGHTFORCE.', 'HERO 2 32K DPI · 60g · LIGHTSPEED 4000Hz', 89900, 17, 'gprox2'),
    ('hyperx-cloud-iii-wl', 'Headset HyperX Cloud III Wireless', 'Áudio', 'Headset sem fio com arco em alumínio, memory foam e microfone destacável com cancelamento.', 'Drivers 53mm · DTS:X · Bateria até 120h', 84900, 12, 'cloud3'),
    ('lg-ultragear-oled-27', 'Monitor LG UltraGear OLED 27" QHD', 'Monitores', 'Monitor gamer OLED antirreflexo 240Hz com tempo de resposta de 0,03ms e G-SYNC.', '27" QHD OLED · 240Hz · 0.03ms GtG', 529900, 5, 'ultragear'),
    ('rtx-4070-super-asus', 'Placa de Vídeo ASUS Dual RTX 4070 Super', 'Hardware', 'GPU Ada Lovelace para jogos em 1440p no máximo com DLSS 3.5, Ray Tracing e dual fan.', '12GB GDDR6X · DLSS 3.5 · Axial-tech', 439900, 6, 'rtx4070'),
    ('ssd-samsung-990-pro-2tb', 'SSD NVMe Samsung 990 PRO 2TB M.2', 'Hardware', 'SSD PCIe 4.0 x4 de altíssima velocidade para loadings instantâneos em PC e PS5.', 'PCIe 4.0 · Leitura 7450 MB/s · M.2 2280', 124900, 22, 'ssd990'),
    ('cartucho-zelda-alttp-16bit', 'Zelda: A Link to the Past (Ed. Colecionador)', 'Retrô', 'Cartucho clássico 16-bit revisado com bateria de save nova, label preservada e case acrílico.', 'SNES 16-Bit · Bateria CR2032 Nova · Case', 38900, 9, 'cartridge')
ON CONFLICT (slug) DO NOTHING;

CREATE TABLE IF NOT EXISTS store_orders (
    id SERIAL PRIMARY KEY,
    order_code TEXT NOT NULL UNIQUE,
    customer_name TEXT NOT NULL,
    customer_email TEXT NOT NULL,
    total_cents INTEGER NOT NULL CHECK (total_cents >= 0),
    items_json TEXT NOT NULL,
    email_sent BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

GRANT SELECT, UPDATE ON store_products TO lab_workload;
GRANT SELECT, INSERT, UPDATE ON store_orders TO lab_workload;
GRANT USAGE, SELECT ON SEQUENCE store_orders_id_seq TO lab_workload;
