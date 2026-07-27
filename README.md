# Simulador de Exámenes de Radioafición Chile

Simulador de práctica para licencias de radioaficionado en Chile, basado en los exámenes oficiales de **SUBTEL**. Incluye 1,022 preguntas extraídas de los apéndices oficiales, cubriendo las 4 categorías de licencia: CD, CA, CE y XQ.

Complementa la herramienta existente de [CE3AA](https://www.ce3aa.cl/) enfocándose en el **aprendizaje**: seguimiento de progreso, historial, detección de debilidades y explicaciones.

## Quick path

```bash
git clone https://github.com/gismodes37/simulador-examenes.git
cd simulador-examenes
cp .env.example .env
docker-compose up -d --build
docker-compose exec web python simulador_examenes/manage.py migrate
docker-compose exec web python simulador_examenes/manage.py load_questions --all
docker-compose exec web python simulador_examenes/manage.py createsuperuser
```

Abrí [http://localhost:8000](http://localhost:8000) y elegí una categoría para empezar.

## Categorías de licencia

| Código | Nombre | Preguntas | Reglamento | Técnica | Umbral |
|--------|--------|-----------|------------|---------|--------|
| CD | Aspirante | 30 | 18 | 12 | 70% |
| CA | Novicio | 30 | 15 | 15 | 70% |
| CE | General | 30 | 12 | 18 | 70% |
| XQ | Superior | 30 | 6 | 24 | 70% |

## Stack

| Componente | Tecnología |
|------------|------------|
| Backend | Django 5.x, Python 3.12 |
| Base de datos | PostgreSQL 16 |
| Frontend | Bootstrap 5, HTMX |
| Contenedores | Docker, Docker Compose |
| Testing | pytest-django |
| PDF parsing | PyMuPDF |

## Estructura del proyecto

```
simulador-examenes/
├── docker-compose.yml          # PostgreSQL + Django services
├── Dockerfile                  # Python 3.12-slim
├── requirements.txt            # Python dependencies
├── pyproject.toml              # Project metadata, pytest config
├── conftest.py                 # Shared test fixtures
├── .env.example                # Environment template
│
├── data/                       # Parsed questions (JSON)
│   ├── cd_reglamento.json
│   ├── cd_tecnica.json
│   ├── ca_reglamento.json
│   ├── ca_tecnica.json
│   ├── ce_reglamento.json
│   ├── ce_tecnica.json
│   ├── xq_reglamento.json
│   ├── xq_tecnica.json
│   ├── schema.json
│   └── sample_questions.json
│
├── scripts/
│   ├── parse_pdfs.py           # Initial PDF parser
│   └── parse_pdfs_v2.py        # Improved parser for SUBTEL appendices
│
└── simulador_examenes/         # Django project
    ├── manage.py
    ├── config/
    │   ├── settings.py
    │   └── urls.py
    ├── apps/
    │   ├── users/
    │   │   └── models.py       # Custom User (callsign, radio_amateur)
    │   └── exams/
    │       ├── models.py       # Category, Area, Tema, Question, ExamAttempt
    │       ├── views.py        # 8 views (home, setup, start, page, submit, finish, results, history)
    │       ├── urls.py
    │       └── management/
    │           └── commands/
    │               └── load_questions.py  # Import from JSON
    ├── static/
    │   ├── css/custom.css      # Dark mode, gradients, animations
    │   └── js/theme.js         # Light/dark toggle with localStorage
    └── templates/
        ├── base.html           # Layout, navbar, footer
        └── exams/
            ├── home.html       # Landing with hero, categories, how-it-works
            ├── exam_setup.html # Mode selection (exam vs training)
            ├── exam_page.html  # HTMX-powered exam flow
            ├── question_card.html  # HTMX fragment for question swap
            ├── results.html    # Score breakdown, wrong answers
            └── history.html    # Past attempts
```

## Modelos de datos

### User (extensión del modelo de Django)

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `callsign` | CharField (opcional) | Indicativo de radioaficionado |
| `is_radio_amateur` | BooleanField | Si tiene licencia de radioaficionado |

### Category, Area, Tema

Estructura jerárquica: **Category** → **Area** (Reglamentación / Técnica) → **Tema** → **Question**.

### Question

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `text` | TextField | Texto de la pregunta |
| `option_a` … `option_d` | CharField | 4 opciones de respuesta |
| `correct_answer` | CharField (A/B/C/D) | Respuesta correcta |
| `explanation` | TextField (opcional) | Explicación de la respuesta correcta |
| `category` | FK → Category | Categoría de licencia |
| `area` | FK → Area | Reglamentación o Técnica |
| `tema` | FK → Tema (opcional) | Tema específico |

### ExamAttempt

Registra cada intento de examen con modo (examen/entrenamiento), puntuación y timestamps.

### AnswerAttempt

Respuesta individual dentro de un intento: pregunta, respuesta seleccionada, si es correcta, tiempo empleado.

## Modos de práctica

| Modo | Descripción |
|------|-------------|
| **Examen** | Cronometrado (60 min), sin retroalimentación, resultado al finalizar, umbral de 70% |
| **Entrenamiento** | Sin tiempo, retroalimentación inmediata por pregunta, aprendizaje libre |

## Uso

### Importar preguntas

```bash
# Importar todas las categorías
docker-compose exec web python simulador_examenes/manage.py load_questions --all

# Importar una categoría específica
docker-compose exec web python simulador_examenes/manage.py load_questions --file data/ce_reglamento.json

# Dry run (sin escribir)
docker-compose exec web python simulador_examenes/manage.py load_questions --all --dry-run
```

### Crear superusuario

```bash
docker-compose exec web python simulador_examenes/manage.py createsuperuser
```

### Admin panel

Accedé a [http://localhost:8000/admin](http://localhost:8000/admin) para gestionar categorías, preguntas, intentos y usuarios.

## Variables de entorno

Copiá `.env.example` a `.env` y ajustá según tu entorno:

| Variable | Default | Descripción |
|----------|---------|-------------|
| `DEBUG` | `true` | Modo debug de Django |
| `SECRET_KEY` | `change-me-in-production` | Clave secreta de Django |
| `ALLOWED_HOSTS` | `localhost,127.0.0.1` | Hosts permitidos (coma-separados) |
| `DB_NAME` | `simulador_examenes` | Nombre de la base de datos |
| `DB_USER` | `simulador` | Usuario de PostgreSQL |
| `DB_PASSWORD` | `simulador_secret` | Contraseña de PostgreSQL |
| `DB_HOST` | `localhost` | Host de PostgreSQL |
| `DB_PORT` | `2086` | Puerto de PostgreSQL |

> **Nota:** El puerto 2086 está elegido por compatibilidad con Cloudflare (puertos no estándar).

## Testing

```bash
# Ejecutar todos los tests
docker-compose exec web pytest

# Con coverage
docker-compose exec web pytest --cov=simulador_examenes

# Tests específicos
docker-compose exec web pytest simulador_examenes/apps/exams/tests.py -v
```

## Producción

### Gunicorn

```bash
pip install gunicorn
gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 3
```

### Variables para producción

```env
DEBUG=false
SECRET_KEY=tu-clave-secreta-aqui
ALLOWED_HOSTS=tu-dominio.com
DB_HOST=tu-host-postgresql
DB_PASSWORD=tu-password-seguro
```

## Contribuir

1. Fork el repositorio
2. Creá una rama para tu feature (`git checkout -b feature/nueva-funcionalidad`)
3. Hacé commit de tus cambios (`git commit -m 'Add nueva funcionalidad'`)
4. Push a la rama (`git push origin feature/nueva-funcionalidad`)
5. Abrí un Pull Request

## Licencia

MIT

## Créditos

- Preguntas oficiales: [SUBTEL](https://www.subtel.gob.cl/) — Reglamento General de Radioafición
- Inspiración: [CE3AA Simulador](https://www.ce3aa.cl/)
