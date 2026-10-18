# Seguridad y rendimiento — refactor de octubre 2026

Refactor a la estructura de afrodita, Python 3.15 y Django 6.1. El
comportamiento se verificó contra el código anterior: las 76 respuestas de las
queries y mutations que usa el frontend (más REST y HTML) se compararon sobre
la misma base de datos, en PostgreSQL y en SQLite. 67 son idénticas; las 9
restantes son los cambios de seguridad de la tabla. Tests:
`app/tests/security/`, `app/tests/schema/`, `honeypot/tests/`.

## Vulnerabilidades encontradas y corregidas

| # | Severidad | Hallazgo | Corrección |
|---|---|---|---|
| 1 | Crítica | 8 mutations sin autenticación: `createDriver`, `updateDriver`, `deleteDriver`, `createRoute`, `updateRoute`, `deleteRoute`, `deleteTrip`, `deleteTicket`. Cualquiera podía borrar viajes (con sus tiquetes) y tiquetes | `@login_required` en todas; un test recorre el esquema y falla si aparece una operación nueva sin sesión |
| 2 | Crítica | `POST /drivers/<id>/upload-documents/` sin autenticación: cualquiera podía reemplazar la cédula, la licencia o la firma de un conductor | Exige el mismo `Authorization: JWT …` que el frontend ya envía |
| 3 | Alta | El honeypot leía la primera entrada de `X-Forwarded-For`: se podía hacer bloquear la IP de otra persona (o la del admin) | IP confiable (`TRUSTED_PROXY_COUNT`) y, detrás de Cloudflare, IP real restaurada en nginx |
| 4 | Alta | `tokenAuth` sin límite de intentos (fuerza bruta de contraseñas) | 10 fallos cada 15 min por IP; los inicios de sesión correctos no cuentan |
| 5 | Alta | Login del admin sin límite de intentos | 10 intentos cada 15 min (Django) + 10/min (nginx) |
| 6 | Alta | Sin límites en GraphQL: alias, profundidad, tamaño; introspección abierta | `app/utils/graphql_limits.py`: 15 alias, profundidad 8, 300 campos, 12 KB / 2.500 tokens; introspección cerrada sin DEBUG |
| 7 | Alta | Los errores internos (SQL, bugs) llegaban al cliente, p. ej. `duplicate key value violates unique constraint "driver_driver_dni_key"` | Mensaje genérico en producción; detalle en los logs. Los mensajes propios («Route not found», «… does not exist», permisos) se mantienen |
| 8 | Media | `/graphiql/` y Swagger abiertos; los errores de GraphQL sugerían nombres de campos («Did you mean…») aun con la introspección cerrada | En producción GraphiQL y Swagger no se enrutan (404) ni se carga `drf_yasg`; sin sugerencias. En local (`DEBUG`), GraphiQL para superusuarios y Swagger para staff |
| 9 | Media | `DEBUG=True` por defecto; sin cookies seguras ni HSTS | `DEBUG=False` por defecto y forzado en `ci/docker-compose.yml` aunque `.env` diga otra cosa; cookies Secure, HSTS. Producción no arranca con `SECRET_KEY` < 50 caracteres ni `ALLOWED_HOSTS` con `*` |
| 10 | Media | Contenedores como root, imagen de 1,5 GB con compiladores | Imagen slim multi-stage (466 MB), usuario sin privilegios |
| 11 | Baja | El honeypot consultaba la lista negra en la base de datos en cada petición | Lista en caché (Valkey), se refresca al cambiar |

## Protección contra DDoS (capas)

1. **Cloudflare** delante (el dominio ya resuelve a Cloudflare).
2. **nginx** (`nginx/nginx.conf.template`):
   - IP real del visitante desde `CF-Connecting-IP`, aceptada solo desde los
     rangos de Cloudflare (no se puede falsificar conectando directo).
   - 15 peticiones/s por IP (ráfaga 40); 30 conexiones por IP. Ráfaga de 80
     peticiones paralelas: pasan 43, 429 al resto.
   - Subida de documentos: 2/s (ráfaga 10), 80 MB máx.; resto 1 MB.
   - Admin login 10/min; honeypot 5/min (cada POST escribe en la base).
   - Timeouts cortos (Slowloris), solo GET/HEAD/POST/OPTIONS, archivos
     ocultos 404, escáneres `.php`/`.asp` cerrados sin respuesta (444).
3. **Django**: límites atómicos en Valkey compartidos por todos los
   procesos; `statement_timeout` de 10 s en PostgreSQL.
4. **GraphQL**: límites de forma de la consulta (ver #6).

## IP de origen oculta y sin huellas de tecnología

Herramientas como Shodan, FOFA o Censys escanean todo internet y guardan lo
que responde cada IP; las de descubrimiento de origen (CloudFlair y
similares) piden el sitio a IPs candidatas con `Host: <dominio>` y comparan.
Wappalyzer, WhatWeb o graphw00f reconocen la tecnología por sus firmas.

| Capa | Qué hace |
|---|---|
| nginx: solo Cloudflare | Toda conexión que no venga de los rangos de Cloudflare (ni de la propia máquina o sus redes privadas) se cierra sin responder un byte (444): ni página, ni cabecera, ni banner que correlacionar. Un cliente directo tampoco puede falsificar `CF-Connecting-IP`. `ORIGIN_ONLY_CLOUDFLARE = 0` lo desactiva (origen sin Cloudflare) |
| Cloudflare Tunnel (opcional, recomendado) | `COMPOSE_PROFILES` con `tunnel`, `TUNNEL_TOKEN` y `NGINX_BIND = "127.0.0.1"`: el tráfico entra por una conexión saliente hacia Cloudflare y el servidor no necesita ningún puerto abierto |
| Cookies | `sid`, `xsrf`, `flash` en lugar de `sessionid`, `csrftoken`, `messages` |
| Páginas de error | 400/403/404/500 y fallo CSRF como texto plano («Not Found»), sin el HTML de Django |
| Django REST framework | Sin cabecera `Allow`, sin metadatos en `OPTIONS` (405), `detail` genérico («Unauthorized») en lugar de sus frases |
| GraphQL | En producción, sintaxis, validación, límites, introspección y variables responden «Invalid query.» (graphw00f identifica el motor por esos textos, y las sugerencias «Did you mean…?» revelaban el esquema). Se mantienen los errores de los resolvers que lee el frontend (permisos, «… not found») |
| Admin y honeypot | Sin «Django administration» ni «Django site admin»; el honeypot sin `csrfmiddlewaretoken` |

Verificado con redes simuladas: desde un rango de Cloudflare responde 200 y
registra la IP real del visitante; desde otra IP pública, con `Host` del
dominio o con `CF-Connecting-IP` falsificado, la conexión se cierra sin
respuesta.

### Lo que no se resuelve desde el código

- **Historial DNS.** Si el dominio apuntó alguna vez a la IP del servidor sin
  el proxy de Cloudflare (nube gris), servicios como SecurityTrails o Censys
  la guardan para siempre. Tras activar el candado o el túnel, **cambia la IP
  del servidor** (otra IP en el proveedor) y no la publiques nunca.
- **Todos los registros DNS con proxy.** Cualquier subdominio sin la nube
  naranja que apunte al mismo servidor, o un registro MX/correo enviado desde
  él, revela la IP. Revisa la zona completa en Cloudflare.
- **Puerto cerrado con el túnel.** Con `NGINX_BIND = "127.0.0.1"` nginx solo
  escucha en la propia máquina. Cierra también el puerto en el firewall del
  proveedor: Docker publica puertos por encima de `ufw`, que no los bloquea.
- **Cloudflare.** «Always Use HTTPS» y Bot Fight Mode activos.
- **Rastros que quedan.** El admin (ruta secreta) sigue siendo el de Django
  para quien la conozca, y sus estáticos existen en `/static/admin/`. Que el
  API es GraphQL se ve en el propio endpoint; lo que ya no se ve es qué motor
  lo sirve.

## Rendimiento (hardware pequeño)

| Medida | Antes | Después |
|---|---|---|
| Lista de viajes (`getTripList`, 15 por página) | 64 SQL | 4 SQL |
| Viaje (`getTripById`) | 9 SQL | 3 SQL |
| Viajes recientes | 33 SQL | 3 SQL |
| Lista de tiquetes | 34 SQL | 5 SQL |
| Lista de viajes, 1 CPU, 8 clientes | 3,2 req/s, p50 2,5 s, p95 3,1 s (runserver) | 13,6 req/s, p50 0,5 s, p95 1,0 s (gunicorn 2×4) |
| Granian frente a gunicorn (misma imagen y datos, 1 CPU, 8 clientes) | gunicorn 2×4: 28 req/s, p50 282 ms, p95 520 ms | Granian 2×4: 42 req/s, p50 194 ms, p95 360 ms, misma RAM (~200 MiB) |

Además:
- Granian (servidor HTTP en Rust, interfaz WSGI) con hilos en lugar de
  `runserver`; workers reemplazados cada 6 h o al pasar de 320 MiB;
  contrapresión de 32 peticiones por worker (503 inmediato en vez de cola);
  conexiones persistentes a la base de datos.
- El middleware JWT se ejecutaba en cada campo de la respuesta (más de 500
  por lista de viajes); ahora solo en los campos raíz.
- Cada documento GraphQL se parsea y valida una vez por proceso (caché LRU
  de 256), no en cada petición.
- SQLite (si se usa): WAL, `synchronous=NORMAL`, transacciones `IMMEDIATE`
  y espera de 20 s (sin «database is locked» con varios procesos).
- PostgreSQL local dimensionado para 1–2 GB; Valkey 32 MB sin disco; nginx
  con gzip y estáticos del admin servidos directamente; logs de Docker con
  rotación (10 MB × 3).
- Venta simultánea de tiquetes: el número consecutivo (`index`) se reintenta
  en vez de fallar con un 500.

## Comportamientos heredados que se mantienen (decisión pendiente)

- `updateTrip` sin `dispatcher` guarda el texto `"False"` (el frontend
  siempre lo envía).
- Los JWT no expiran (`django-graphql-jwt` por defecto). Activar
  `JWT_VERIFY_EXPIRATION` obliga al frontend a renovar el token.
- `deleteTrip` y `deleteTicket` borran de verdad; el resto desactiva.
- `getTicketList` y `getVesselList` no tienen orden definido.

## Lista para producción

- [ ] Copia de seguridad de la base de datos antes del primer despliegue.
- [ ] `SECRET_KEY` ≥ 50 caracteres aleatorios, `ALLOWED_HOSTS` y `CORS_ALLOWED_ORIGINS` con los hosts reales (`DEBUG` ya va forzado a `False`).
- [ ] `APP_UID`/`APP_GID` del dueño de la carpeta del proyecto.
- [ ] `make prod-up` (genera y aplica las migraciones; adopta las tablas existentes).
- [ ] Si se sale de Cloudflare o se añade otro proxy, revisar `set_real_ip_from` y `TRUSTED_PROXY_COUNT`.
- [ ] Cloudflare: «Always Use HTTPS» activo (Django no redirige a HTTPS por su cuenta).
