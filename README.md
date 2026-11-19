# Bookstore API — автентифікація і захист

## Варіант

- Номер варіанта: 6
- Схема: JWT
- Право: P3
- Throttle: 6 запитів/год для аноніма · 120 запитів/добу для користувача
- Інтеграція: I1
- Відеозахист :закреслено завдання

## Запуск

```bash
python3 -m venv venv              # Windows: py -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed             # автори, 30 книг, користувачі й групи
python manage.py runserver
python manage.py test
```

Тестові користувачі (`python manage.py seed`), пароль `pass12345`:

| Користувач | Пошта | Акаунт | Група / роль |
|---|---|---|---|
| alice | alice@kpi.edu.ua | 30 днів | Editors, власниця третини книг |
| bob | bob@lnu.edu.ua | 30 днів | Editors |
| carol | carol@gmail.com | 30 днів | — |
| newbie | newbie@kpi.edu.ua | щойно | Editors |
| moder | moder@gmail.com | 30 днів | Moderators |
| staff | staff@gmail.com | 30 днів | `is_staff` |
| admin | admin@example.com | — | суперкористувач, пароль `admin` |

## Результат тестів
Found 59 test(s).
Creating test database for alias 'default'...
System check identified no issues (0 silenced).
Ran 59 tests in 12.831s

OK (skipped=37)

(37 тестів пропущено: вони для інших варіантів.)

## Журнал `curl -i`

Для кожного пункту — команда і **перші рядки** відповіді (статус і важливі заголовки).

### 1. Вхід і вихід
Вхід:

curl -i -X POST http://127.0.0.1:8000/api/v1/auth/jwt/create/ -H "Content-Type: application/json" -d '{"username":"admin","password":"admin"}'

HTTP/1.1 200 OK
Content-Type: application/json
{"refresh":"eyJ...","access":"eyJ..."}

Вихід (refresh у чорний список): відповідь 200, {"detail":"ok"}. [ЗАПОВНИТИ: повторний logout з тим самим refresh → 401, вставте вивід]

### 2. Право доступу: дозволено і заборонено
Запис без токена:

curl -i -X POST http://127.0.0.1:8000/api/v1/books/ -H "Content-Type: application/json" -d '{}'

HTTP/1.1 401 Unauthorized
WWW-Authenticate: Bearer realm="api"

bob видаляє чужу книгу (книга 3 належить alice):

curl -i -X DELETE http://127.0.0.1:8000/api/v1/books/3/ -H "Authorization: Bearer $ACCESS"

HTTP/1.1 403 Forbidden
{"detail":"У вас нема дозволу робити цю дію."}

bob видаляє свою книгу (книга 10): [ЗАПОВНИТИ: вставте вивід, очікується 204 No Content]
### 3. Throttling: останній дозволений запит і `429`
for i in $(seq 1 7); do curl -i -s http://127.0.0.1:8000/api/v1/authors/ | head -1; done

HTTP/1.1 200 OK
HTTP/1.1 200 OK
HTTP/1.1 200 OK
HTTP/1.1 200 OK
HTTP/1.1 200 OK
HTTP/1.1 429 Too Many Requests
HTTP/1.1 429 Too Many Requests

429 з'явився на шостому запиті циклу, бо перед ним був ще один анонімний запит — вхід /auth/jwt/create/ (він теж рахується як анонімний). Разом 5 + 1 = 6 запитів на годину.

### 4. Інтеграційна вимога
[ЗАПОВНИТИ: вставте curl -s http://127.0.0.1:8000/api/v1/books/ -H "Authorization: Bearer $ACCESS" | python3 -m json.tool | head -30 — видно author як об'єкт і owner як рядок]

## Журнал помилок

Щонайменше дві помилки, на які ви справді натрапили.

## Журнал помилок

| Що побачили | Причина | Що змінили |
|---|---|---|
| 404 Not Found на `/api/v1/auth/jwt/create/`; у списку URL були `auth/login/`, `auth/refresh/`, `auth/logout/` | Адреси в `core/urls.py` не збігались із вимогою завдання | Змінила адреси на `auth/jwt/create/`, `auth/jwt/refresh/`, `auth/jwt/logout/` |
| 403 замість 401 на `/auth/jwt/logout/` | У в'юхи `authentication_classes = []`: DRF не має заголовка `WWW-Authenticate` і замінює 401 на 403 | Поставила `authentication_classes = [JWTAuthentication]` |
| `ImportError: cannot import name 'JWTLogoutView'` | Файл `auth_views.py` був порожній | Вставила код класу і зберегла файл |
| `That port is already in use`, самі `429` | Старий `runserver` працював і тримав лічильник | `pkill -f "manage.py runserver"` і запуск заново |

## Дослідницькі питання

Своїми словами, з посиланням на джерело (документація, рядок вихідного коду пакета).
Claims. Я розкодувала access і refresh на jwt.io. В обох є однакові поля: token_type, exp, iat, jti, user_id. Різниця в token_type: в одного там access, в іншого refresh. За ним сервер і розуміє, який це токен.
ROTATE і BLACKLIST. Коли я оновлюю токен через /refresh/, сервер дає новий access і новий refresh. А старий refresh одразу йде в чорний список, і ним уже не можна користуватись ще раз. Для цього треба було додати token_blacklist в INSTALLED_APPS і зробити migrate.
Старий access після logout. [ЗАПОВНИТИ: який код вийшов у вас.] Logout вбиває тільки refresh. Access просто перевіряється за підписом і за часом, у чорний список сервер не дивиться. Тому він працює, поки не мине його час. Через це час життя access роблять маленьким, у мене 15 хвилин.
Порядок у APIView.initial(). Спершу йде перевірка автентифікації, потім прав, потім лімітів. Якщо анонім отримав 401 на правах, до лімітів запит не доходить, тому ліміт не витрачається. У мене це видно: до 429 було 5 запитів до /authors/ і 1 вхід, разом 6, а запит POST /books/ без токена з відповіддю 401 не порахувався.
Джерело: https://django-rest-framework-simplejwt.readthedocs.io/ (питання 1 і 2)
Джерело: https://www.django-rest-framework.org/api-guide/throttling/ та метод APIView.initial() у rest_framework/views.py

## Якщо користувались ШІ

Користувалась ШІ (Claude), щоб розібратись з кодом і помилками. Не все підійшло одразу: logout спершу давав 403 замість 401, довелось змінити authentication_classes. Готовий settings.py не збігався з моїм, тому я вставляла зміни вручну. Адреси в core/urls.py треба було виправити за завданням. А пояснення, чому прийшов перший 429, було неправильне, і я перевірила його сама за результатами запитів.