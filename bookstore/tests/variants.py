"""Таблиця варіантів. НЕ РЕДАГУЙТЕ: тести беруть вимоги звідси.

scheme       — "token" (DRF Token) або "jwt" (simplejwt)
permission   — P1..P4, див. умову
anon_rate    — ліміт для аноніма, запитів на годину
user_rate    — ліміт для автентифікованого, запитів на добу
integration  — I1..I5, див. умову
"""

VARIANTS = {
    1: {"scheme": "token", "permission": "P1", "anon_rate": 5, "user_rate": 100, "integration": "I1"},
    2: {"scheme": "jwt", "permission": "P2", "anon_rate": 8, "user_rate": 150, "integration": "I2"},
    3: {"scheme": "token", "permission": "P3", "anon_rate": 10, "user_rate": 200, "integration": "I3"},
    4: {"scheme": "jwt", "permission": "P4", "anon_rate": 12, "user_rate": 250, "integration": "I4"},
    5: {"scheme": "token", "permission": "P2", "anon_rate": 15, "user_rate": 300, "integration": "I5"},
    6: {"scheme": "jwt", "permission": "P3", "anon_rate": 6, "user_rate": 120, "integration": "I1"},
    7: {"scheme": "token", "permission": "P4", "anon_rate": 9, "user_rate": 180, "integration": "I2"},
    8: {"scheme": "jwt", "permission": "P1", "anon_rate": 11, "user_rate": 220, "integration": "I3"},
    9: {"scheme": "token", "permission": "P1", "anon_rate": 14, "user_rate": 280, "integration": "I4"},
    10: {"scheme": "jwt", "permission": "P2", "anon_rate": 7, "user_rate": 140, "integration": "I5"},
    11: {"scheme": "token", "permission": "P3", "anon_rate": 13, "user_rate": 260, "integration": "I1"},
    12: {"scheme": "jwt", "permission": "P4", "anon_rate": 16, "user_rate": 320, "integration": "I2"},
    13: {"scheme": "token", "permission": "P2", "anon_rate": 18, "user_rate": 360, "integration": "I3"},
    14: {"scheme": "jwt", "permission": "P1", "anon_rate": 20, "user_rate": 400, "integration": "I4"},
    15: {"scheme": "token", "permission": "P4", "anon_rate": 4, "user_rate": 80, "integration": "I5"},
    16: {"scheme": "jwt", "permission": "P3", "anon_rate": 17, "user_rate": 340, "integration": "I1"},
}
