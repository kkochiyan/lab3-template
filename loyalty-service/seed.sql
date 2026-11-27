INSERT INTO loyalty (username, reservation_count, status, discount)
VALUES ('Test Max', 25, 'GOLD', 10)
ON CONFLICT (username) DO NOTHING;
