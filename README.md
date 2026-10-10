# ResetPro — listo para Vercel

Un solo repositorio con todo: sitio web (HTML/CSS/JS), API en Python (FastAPI) y base de datos PostgreSQL.
El front y la API viven en el mismo dominio, así que no hace falta configurar CORS ni URLs.

## Estructura

```
├── vercel.json            configuración de Vercel (rutas /api → Python)
├── requirements.txt       dependencias de Python
├── .python-version        versión de Python (3.12)
├── api/
│   └── index.py           entrada de la función serverless
├── backend/               API: modelos, rutas, seguridad y datos de ejemplo
│   ├── main.py, database.py, models.py, schemas.py, security.py, deps.py
│   ├── init_db.py         crea las tablas y carga los datos de ejemplo
│   └── routers/           auth, usuarios, profesores, turnos, dietas, archivos, admin
├── database/
│   └── schema.sql         esquema de referencia (las tablas se crean solas)
└── public/                el sitio (index, logins, paneles usuario/profesor/admin, estado.html)
```

## Desplegar en Vercel (3 pasos)

1. **Subí el repo a GitHub** (todo en la raíz del repositorio, tal cual está acá).
2. En Vercel: **Add New → Project**, importá el repo y dejá todo por defecto
   (Framework Preset: *Other*, sin Build Command). Deploy.
3. En el proyecto: **Storage → Create Database → Neon (Postgres)** y conectala al proyecto.
   Esto agrega `DATABASE_URL` automáticamente. Luego **Redeploy** (las variables nuevas solo se toman en un deploy nuevo).

Después abrí **`https://TU-PROYECTO.vercel.app/estado.html`**: tiene que mostrar *API OK* y *Base de datos conectada*.
La primera consulta tarda unos segundos: crea las tablas y carga los datos de ejemplo.

## Cuentas de ejemplo

| Rol | Email | Contraseña | Entra por |
|---|---|---|---|
| Administrador | admin@resetpro.app | admin123 | Ingresar (Profesor) → pestaña Administrador |
| Profesor | mariano@resetpro.app | profesor123 | Ingresar (Profesor) |
| Usuario | sarah@resetpro.app | usuario123 | Ingresar (Usuario) |

Hay además 2 profesores y 5 alumnos más (`daniela@`, `ignacio@`, `julian@`, `camila@`, `lucas@`, `valentina@`, `nico@` + `@resetpro.app`).

## Antes de usarlo con gente real

Esas contraseñas están en el repositorio, o sea que son públicas. Dos opciones:

- **Cambiarlas:** abrí `/api/docs`, logueate con `POST /api/auth/login`, tocá *Authorize* con el token y usá `POST /api/auth/cambiar-password`.
- **Empezar sin datos de ejemplo:** antes del primer arranque definí en Vercel `SEED_DEMO_DATA=false`,
  `ADMIN_EMAIL`, `ADMIN_PASSWORD` (y opcional `ADMIN_NAME`). Si ya se cargaron los datos de ejemplo,
  vaciá la base en el SQL Editor de Neon (`DROP SCHEMA public CASCADE; CREATE SCHEMA public;`) y hacé un Redeploy.

## Recuperar contraseña

En los dos logins, **¿Olvidaste tu contraseña?** lleva a `recuperar.html`. La persona ingresa su email y:

- **Si configuraste el envío de emails**, recibe un enlace que vale 60 minutos y se usa una sola vez
  (`restablecer.html`), donde crea su contraseña nueva. La respuesta es siempre la misma exista o no el email.
- **Si no configuraste emails**, el pedido queda en el panel del administrador
  (sección *Recuperación de contraseñas*) y desde ahí se genera un enlace de 24 horas
  para enviárselo por WhatsApp o mail. El admin también puede generar uno en cualquier momento
  con el botón **Enlace de clave** de la tabla de alumnos o de profesores.

Para activar los emails, en Vercel (Settings → Environment Variables) definí **una** de estas opciones y hacé Redeploy:

| Opción | Variables |
|---|---|
| Resend | `RESEND_API_KEY` y `MAIL_FROM` (con un dominio verificado en Resend) |
| SMTP (Gmail con contraseña de aplicación, Brevo, etc.) | `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD` y `MAIL_FROM` |

En `/estado.html` aparece si el envío de emails quedó configurado. Los enlaces se guardan en la base solo como hash
(nunca el token), vencen y dejan de servir al usarse. Si olvida su clave el **único administrador**, otro admin le genera el enlace;
por eso conviene tener dos cuentas de administrador.

## Eliminar alumnos y profesores

En el panel de administración, cada fila de **Estudiantes activos** y de **Profesores** tiene el botón **Eliminar** (con confirmación).
Borrar un alumno elimina su cuenta, turnos, plan nutricional y PDFs. Borrar un profesor elimina su cuenta y los turnos que tenía asignados
(el aviso muestra cuántos). No se puede deshacer.

Variables opcionales: `JWT_SECRET_KEY` (si no está, se deriva de `DATABASE_URL`), `APP_TIMEZONE` (por defecto `America/Argentina/Cordoba`, define qué es "hoy" en los paneles).

## Qué hace cada panel

- **Usuario:** semana de entrenamiento por grupo muscular, próximo turno con el profesor (se puede cancelar), macros del plan y descarga de rutina/dieta en PDF.
- **Profesor:** agenda de los próximos 7 días con cada alumno, su grupo muscular y la rutina en PDF (descargar, cargar o actualizar).
- **Administrador:** alta de usuarios/profesores/admins, dashboard de estudiantes (último turno, último acceso, activos de la semana), asignar turnos (evita doble reserva del profesor), macros/micros y PDFs por alumno. El admin no tiene restricciones.

Los PDF se guardan dentro de PostgreSQL (máx. 4 MB cada uno), porque Vercel no conserva archivos subidos.

## Probar en tu computadora

```bash
python -m venv venv && source venv/bin/activate     # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn backend.main:app --reload
```

Abrí http://127.0.0.1:8000 (sirve el sitio y la API juntos). Sin `DATABASE_URL` usa un SQLite temporal
solo para pruebas; para usar PostgreSQL local, copiá `.env.example` a `.env`, completá `DATABASE_URL`
y exportala (`export DATABASE_URL=...`).

## Notas

- Si cambiás los modelos más adelante, `create_all` no modifica tablas existentes; habría que migrar (por ejemplo con Alembic).
- La API está documentada en `/api/docs`.
