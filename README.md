# ToDo — gestió de tasques en Django

Aplicació senzilla de tasques ("to-do") amb Django: registre i inici de sessió
d'usuaris, cada usuari veu només les seves tasques, CRUD complet (crear,
editar, marcar com a feta/pendent, esborrar), organització per **projectes**
amb filtres combinables, vista de **pendents** per defecte, admin de Django i
data límit opcional amb avís de tasca endarrerida.

Stack: **Django 6.x · PostgreSQL 16 · Gunicorn · WhiteNoise · Docker Compose**,
llest per desplegar a **Dokploy**.

---

## Estructura

```
todo/
├── manage.py
├── requirements.txt          # dependències Python
├── Dockerfile                # imatge de producció (gunicorn)
├── entrypoint.sh             # collectstatic + migrate + gunicorn
├── docker-compose.yml        # serveis web + postgres (local i Dokploy)
├── .env.example              # plantilla de variables d'entorn
├── config/                   # projecte Django (settings, urls, wsgi)
├── tasks/                    # app de tasques (models, views, forms, tests)
└── static/css/styles.css     # estil mínim
```

## Desenvolupament local (sense Docker)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Obre <http://127.0.0.1:8000>. Sense Docker ni variables d'entorn funciona amb
SQLite, ideal per a proves ràpides. Registra un usuari a
`/accounts/registre/`.

## Desenvolupament local (amb Docker)

```bash
cp .env.example .env       # opcional; si no, fa servir els valors per defecte
docker compose up --build
```

- App: <http://localhost:8000>
- Prova l'admin a `/admin/`: crea el superusuari amb
  `docker compose exec web python manage.py createsuperuser`

## Desplegament a Dokploy

1. **Puja el projecte a un repositori** (GitHub/GitLab): Dokploy es desplega
   des d'un repo.

   ```bash
   git remote add origin git@github.com:el-teu-usuari/todo.git
   git push -u origin main
   ```

2. **Crea l'aplicació a Dokploy**: *Projects → Create → Compose*, tria el
   repositori i la branca `main`. Dokploy llegeix el `docker-compose.yml`
   automàticament (serveis `web` + `db` + volum `pgdata`).

3. **Defineix les variables d'entorn** a la pestanya *Environment* del servei:

   | Variable               | Exemple                          | Notes |
   |------------------------|----------------------------------|-------|
   | `SECRET_KEY`           | cadena aleatòria llarga          | obligatòria; genera'n una amb `openssl rand -hex 32` |
   | `DEBUG`                | `0`                              | sempre apagat en producció |
   | `ALLOWED_HOSTS`        | `todo.elmeudomini.cat`           | el domini que attacharàs |
   | `CSRF_TRUSTED_ORIGINS` | `https://todo.elmeudomini.cat`   | recomanat amb domini HTTPS |
   | `COOKIE_SECURE`        | `1`                              | cookies només per HTTPS (Dokploy amb domini) |
   | `POSTGRES_PASSWORD`    | contrasenya llarga               | canvia el valor per defecte |

4. **Attacha el domini** a la pestanya *Domain*: servei `web`, domini
   `todo.elmeudomini.cat`, **port 8000**. Dokploy fa de proxy invers i
   gestiona el certificat TLS automàticament. Si uses una URL gratuïta
   `.dokploy.app`, posa-la també a `ALLOWED_HOSTS`.

5. **Deploy**. Els logs han de mostrar: `collectstatic`, `migrate`,
   `gunicorn` escoltant a `0.0.0.0:8000`. L'`entrypoint.sh` ja fa migracions i
   estàtics a cada arrencada — no cal cap comanda addicional.

6. **Crea el superusuari** per accedir a `/admin/`: obre la consola/terminal
   del servei `web` a Dokploy i executa `python manage.py createsuperuser`.

### Recerca de problemes

- **`DisallowedHost`** quan entres pel domini: falta el domini a
  `ALLOWED_HOSTS` (el problema típic si alguna cosa no funciona).
- **POSTs fallan amb 403 CSRF**: defineix `CSRF_TRUSTED_ORIGINS` amb l'origen
  complet, amb esquema inclòs, p. ex. `https://todo.elmeudomini.cat`.
- **No arranca / "pending"**: mira els logs del servei `web`; si diu
  "Defineix la variable d'entorn SECRET_KEY", falta el pas 3.

## Notes de producció

- Les dades de la base viuen al volum `pgdata`: un redeploy del `web` no perd
  dades; borrar el servei `db` o el volum, sí.
- Quan canvies el model, només cal redeploy: l'entrada ja executa les
  migracions.
- Amb `COOKIE_SECURE=1` (recomanat amb domini TLS) les cookies de sessió/CSRF
  només s'envien per HTTPS.

## Tests

```bash
# local amb venv
python manage.py test

# amb Docker
docker compose run --rm web python manage.py test
```

Cobren l'inici de sessió obligatori, el registre, el CRUD de tasques i de
projectes, els filtres d'estat i de projecte (pendents per defecte) i que una
usuària no pot manipular les tasques ni els projectes d'una altra (404).
