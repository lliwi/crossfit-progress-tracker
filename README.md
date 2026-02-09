# CrossFit Progress Tracker

Aplicacion web para registrar y seguir tu progreso en CrossFit: marcas personales (PRs), skills desbloqueados, benchmarks y WODs semanales.

## Stack

- **Backend:** Flask + SQLAlchemy + PostgreSQL
- **Auth:** Flask-Login + bcrypt
- **Frontend:** Bootstrap 5 (dark/light mode)
- **Infra:** Docker Compose (web + db + adminer)

## Inicio rapido

### 1. Configurar variables de entorno

```bash
cp .env.example .env
```

Edita `.env` y cambia al menos `SECRET_KEY` por un string aleatorio:

```
FLASK_APP=wsgi.py
FLASK_ENV=development
SECRET_KEY=tu-clave-secreta-aqui
DATABASE_URL=postgresql://crossfit:crossfit@db:5432/crossfit_tracker
POSTGRES_USER=crossfit
POSTGRES_PASSWORD=crossfit
POSTGRES_DB=crossfit_tracker
```

### 2. Arrancar con Docker

```bash
./start.sh
```

Esto hace build, levanta los contenedores, aplica migraciones y muestra los logs. La app queda disponible en:

- **App:** http://localhost:5000
- **Adminer (DB):** http://localhost:8080

### 3. Arrancar manualmente

```bash
docker compose build
docker compose up -d
```

## Funcionalidades

| Modulo | Ruta | Descripcion |
|---|---|---|
| **Dashboard** | `/` | Vista general con resumen de PRs y actividad |
| **Marcas** | `/lifts` | Registro de PRs por ejercicio (1RM, 3RM) |
| **WODs** | `/wods` | Entrenamientos semanales (cargados desde JSON) |
| **Benchmarks** | `/benchmarks` | Girls y hero WODs con historial de resultados |
| **Skills** | `/skills` | Seguimiento de skills desbloqueados |
| **Crono** | `/timer` | Cronometro para WODs |
| **Perfil** | `/profile` | Foto, email, password y modo oscuro/claro |

## WODs semanales

Los WODs se cargan desde `data/week-workout.json`. Este archivo es generado externamente por una IA via n8n. La aplicacion es resiliente a errores comunes del JSON generado (llaves sin cerrar, estructura anidada, etc.).

## Estadisticas del sistema

El script `stats.sh` consulta la base de datos y muestra estadisticas. Se ejecuta desde fuera del contenedor:

```bash
# Resumen general (usuarios, marcas, skills, benchmarks)
./stats.sh

# Detalle por usuario con sus registros
./stats.sh --detail
```

## Seguridad

- Passwords hasheados con **bcrypt** (salt automatico)
- Proteccion **CSRF** en todos los formularios (Flask-WTF)
- **Rate limiting** en login (10/min) y registro (5/min) via Flask-Limiter
- Validacion de redirect en login (prevencion de open redirect)
- Logout via **POST** con token CSRF
- Proteccion contra **path traversal** en subida de fotos
- Cookies de sesion con `Secure`, `HttpOnly` y `SameSite=Lax` en produccion
- `SECRET_KEY` obligatoria en produccion (falla si no esta definida)
- Consultas via **SQLAlchemy ORM** (sin SQL crudo, prevencion de SQL injection)

## Estructura del proyecto

```
.
├── app/
│   ├── __init__.py          # Factory, extensiones, seeds
│   ├── config.py            # Configuracion dev/prod
│   ├── models.py            # Modelos SQLAlchemy
│   ├── blueprints/
│   │   ├── auth.py          # Login, registro, logout
│   │   ├── dashboard.py     # Pagina principal
│   │   ├── lifts.py         # CRUD de marcas
│   │   ├── wods.py          # WODs semanales (JSON)
│   │   ├── benchmarks.py    # Benchmarks y resultados
│   │   ├── skills.py        # Skills desbloqueados
│   │   ├── timer.py         # Cronometro
│   │   └── profile.py       # Perfil de usuario
│   ├── templates/           # Templates Jinja2
│   └── static/              # CSS, JS, imagenes
├── data/
│   └── week-workout.json    # WODs (generado por n8n)
├── migrations/              # Flask-Migrate
├── docker-compose.yml
├── Dockerfile
├── entrypoint.sh            # Migraciones + gunicorn
├── start.sh                 # Script de arranque
├── stats.sh                 # Estadisticas del sistema
├── requirements.txt
└── wsgi.py
```
