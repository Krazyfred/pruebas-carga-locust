# Pruebas de carga de una API REST con Locust

Diseño y ejecución de **pruebas de carga** sobre la API REST de una tienda online (catálogo de pósters, carrito, pedidos y usuarios) usando **[Locust](https://locust.io/)** en Python. Las métricas de rendimiento se analizaron con **Grafana**.

> Práctica de la asignatura *Evaluación de Sistemas Informáticos* (3º Grado en Ingeniería Informática, Universidad de Valladolid, curso 2024-25).

## Qué simula

`locustfile.py` define un usuario virtual (`WebStoreUser`) que inicia sesión y ejecuta tareas **ponderadas** que reproducen un uso realista de la tienda:

| Endpoint | Método | Peso | Descripción |
|---|---|---|---|
| `/api/productos` | GET | 10 | Listado de productos |
| `/api/cart/add` | POST | 8 | Añadir al carrito (el stock insuficiente se trata como respuesta válida) |
| `/api/productos/{id}` | GET | 5 | Detalle de producto |
| `/api/carrito` | GET | 4 | Ver carrito |
| `/api/menu`, `/api/pedidos` | GET | 3 | Menú y pedidos |
| `/api/productos/{id}` | PATCH / PUT | 2 / 1 | Actualización parcial / completa de productos |
| `/api/pedidos/{id}` | GET | 2 | Detalle de un pedido creado por el propio usuario |
| `/api/checkout` | POST | 1 | Compra, validando la respuesta y guardando el `order_id` |
| `/api/registro`, `/api/carrito/vaciar` | POST / DELETE | 1 | Alta de usuarios nuevos y vaciado del carrito |

Se usan `catch_response` para validar respuestas a nivel de negocio y nombres agrupados (`/api/productos/[idurl]`) para que las estadísticas no se dispersen por URL.

## Resultados

Escenarios ejecutados con carga creciente (usuarios concurrentes / tasa de llegada / duración). Datos completos en [`resultados/`](resultados/).

| Usuarios | Llegada | Duración | Peticiones | Peticiones/s | Mediana (ms) | P95 (ms) | Errores |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 10 | 2/s | 1 min | 305 | 5,1 | 12 | 120 | 0,00 % |
| 25 | 5/s | 2 min | 1488 | 12,4 | 11 | 59 | 0,00 % |
| 50 | 10/s | 3 min | 4402 | 24,5 | 10 | 120 | 0,02 % |
| 100 | 20/s | 5 min | 14714 | 49,1 | 12 | 140 | 0,05 % |
| 150 | 30/s | 5 min | 20777 | 69,3 | 23 | 290 | 0,13 % |
| 200 | 50/s | 5 min | 24556 | 81,8 | 170 | 1100 | 0,25 % |

**Conclusiones principales**

- El sistema escala de forma casi lineal hasta ~150 usuarios, con medianas por debajo de 25 ms.
- Con **200 usuarios** la mediana se multiplica por 7 y el P95 supera 1 s: es el punto de saturación.
- El cuello de botella es el **login** (mediana de 16 s con 200 usuarios) y el **registro** (~700 ms), probablemente por el coste del *hash* de contraseñas y el acceso a base de datos.
- Los únicos errores son `400` en `/api/checkout`, causados por conflictos de stock entre usuarios concurrentes.

## Cómo ejecutarlo

```bash
pip install -r requirements.txt
locust -f locustfile.py --host http://<servidor>:5000
# abrir http://localhost:8089 y configurar usuarios y tasa de llegada
```

Modo sin interfaz, exportando CSV:

```bash
locust -f locustfile.py --host http://<servidor>:5000 --headless -u 100 -r 20 -t 5m --csv resultados/prueba
```

## Autores

Trabajo en grupo (G02) de **Alfredo del Val** ([@Krazyfred](https://github.com/Krazyfred)) y compañeros.
