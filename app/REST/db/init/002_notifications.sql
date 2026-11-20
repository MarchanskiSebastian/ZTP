-- All times are stored as TIMESTAMPTZ (UTC instants)
CREATE TABLE IF NOT EXISTS notifications (
    id              SERIAL PRIMARY KEY,
    channel         VARCHAR(10)  NOT NULL CHECK (channel IN ('EMAIL', 'PUSH')),
    recipient       VARCHAR(255) NOT NULL,
    subject         VARCHAR(255) NOT NULL DEFAULT '',
    message         TEXT         NOT NULL,
    status          VARCHAR(10)  NOT NULL DEFAULT 'PENDING'
                    CHECK (status IN ('PENDING', 'SENT', 'FAILED', 'CANCELLED')),
    scheduled_at    TIMESTAMPTZ  NOT NULL,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
    sent_at         TIMESTAMPTZ,
    attempts        INTEGER      NOT NULL DEFAULT 0,
    last_error      TEXT,
    idempotency_key VARCHAR(100) UNIQUE
);

CREATE INDEX IF NOT EXISTS idx_notifications_ready ON notifications(status, scheduled_at);

-- Sample data for observing /metrics: some are due now (the worker sends them on start),
-- some are due in the next minutes, plus one of every terminal status
INSERT INTO notifications (channel, recipient, subject, message, status, scheduled_at, sent_at, attempts, last_error, idempotency_key) VALUES
    ('EMAIL', 'jan@example.com',  'Witaj',        'Dziękujemy za rejestrację.',   'PENDING',   now(),                        NULL,  0, NULL, 'seed-1'),
    ('PUSH',  'ztp-demo',         'Promocja',     'Monitor4K -10% tylko dziś!',   'PENDING',   now(),                        NULL,  0, NULL, 'seed-2'),
    ('EMAIL', 'anna@example.com', 'Zamówienie',   'Twoje zamówienie wysłano.',    'PENDING',   now() + interval '1 minute',  NULL,  0, NULL, 'seed-3'),
    ('PUSH',  'ztp-demo',         'Przypomnienie','Masz produkty w koszyku.',     'PENDING',   now() + interval '2 minutes', NULL,  0, NULL, 'seed-4'),
    ('EMAIL', 'ola@example.com',  'Newsletter',   'Nowości tygodnia.',            'PENDING',   now() + interval '5 minutes', NULL,  0, NULL, 'seed-5'),
    ('PUSH',  'ztp-demo',         'Archiwalne',   'Wysłane wcześniej.',           'SENT',      now() - interval '1 hour',    now() - interval '1 hour', 1, NULL, 'seed-6'),
    ('EMAIL', 'bad@example.com',  'Błąd',         'Nie udało się dostarczyć.',    'FAILED',    now() - interval '1 hour',    NULL,  1, 'SMTP connection refused', 'seed-7'),
    ('EMAIL', 'piotr@example.com','Anulowane',    'To powiadomienie anulowano.',  'CANCELLED', now() + interval '1 day',     NULL,  0, NULL, 'seed-8');
