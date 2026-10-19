# Fase 1 — Explorar los datos

Meta: entender los datos de SECOP II **antes** de diseñar la base de datos. Un error común es
diseñar tablas "a ciegas" y descubrir después que los montos vienen como texto o que la mitad de
las fechas están vacías.

Código de esta fase: [`backend/scripts/explorar_secop.py`](../../backend/scripts/explorar_secop.py)

## 1. ¿De dónde salen los datos?

[datos.gov.co](https://www.datos.gov.co/) publica los datos abiertos del Estado colombiano usando
una plataforma llamada **Socrata**. Cada conjunto de datos (*dataset*) tiene un id. El de
**SECOP II – Contratos Electrónicos** es `jbjy-vk9h`, y su URL de API es:

```
https://www.datos.gov.co/resource/jbjy-vk9h.json
```

Ábrela en el navegador agregando `?$limit=3` al final. Verás una lista de contratos en **JSON**:
una lista `[...]` de diccionarios `{"campo": "valor"}`. Eso es una **API REST**: una URL que,
en lugar de una página web, devuelve datos para programas.

> 🔍 **Tarea:** confirma que el id `jbjy-vk9h` sigue siendo el dataset correcto. Busca
> "SECOP II Contratos Electrónicos" en datos.gov.co. Si cambió, actualiza `SECOP_DATASET_ID`
> en tu `.env`.

## 2. SoQL: el "SQL" de la API

Socrata acepta parámetros que empiezan con `$`:

| Parámetro | Ejemplo | Equivale en SQL a |
|---|---|---|
| `$limit` | `$limit=1000` | `LIMIT 1000` |
| `$offset` | `$offset=2000` | `OFFSET 2000` (saltarse filas) |
| `$where` | `$where=departamento='Antioquia'` | `WHERE departamento = 'Antioquia'` |
| `$order` | `$order=:id` | `ORDER BY` |

**Paginación:** la API no te da millones de filas de una vez. Pides de a 1000:
página 1 → `offset=0`, página 2 → `offset=1000`, y así sucesivamente, hasta que una página llega
con menos de 1000 filas. Eso hace el `while` de `descargar_contratos()`.

**¿Por qué `$order=:id`?** Sin un orden fijo, la base de datos puede devolver las filas en
distinto orden en cada petición, y al paginar se repetirían o perderían filas.

## 3. Recorrido por el código

1. **`construir_parametros()`**: una función pequeña y *pura* (misma entrada → misma salida, sin
   efectos secundarios). Es la más fácil de probar.
2. **`descargar_contratos()`**: recibe un `cliente` HTTP **opcional**. En uso normal crea uno
   real. En los tests le pasamos uno falso. Esto se llama **inyección de dependencias** y es la
   base de la arquitectura limpia que usaremos en todo el proyecto.
3. **`a_dataframe()`**: convierte la lista de diccionarios en una tabla de pandas y trata
   `"No Definido"` como vacío. Los datos públicos reales están **sucios**.
4. **`perfilar()`**: por cada columna calcula el % de nulos, los valores únicos y un ejemplo.
5. **`limpiar_valor()`**: la API entrega los montos como **texto** (`"38000000"`). Los pasamos a
   número y tratamos el 0 como dato faltante.
6. **`resumen_negocio()`**: primeras preguntas de negocio. ¿Qué % es contratación directa?
   ¿Cuántos contratos se firmaron en fin de semana? ¿Qué proveedores concentran más dinero?
   Estas preguntas se convertirán en las **banderas rojas** de la Fase 4.

## 4. Ejecútalo

```bash
cd backend
# Sin internet, con los datos de ejemplo:
python -m scripts.explorar_secop --desde-archivo tests/fixtures/secop_contratos_muestra.json

# Con datos reales (guárdalos para no descargarlos cada vez):
python -m scripts.explorar_secop --limite 2000 --guardar data/muestra.json
python -m scripts.explorar_secop --desde-archivo data/muestra.json
```

## 5. Los tests

```bash
pytest -v
```

Mira `tests/test_explorar_secop.py`. El test `test_descargar_contratos_pagina_hasta_que_no_hay_mas_datos`
crea una **API falsa** con `httpx.MockTransport` que tiene 5 registros, pide páginas de 2 y
comprueba que se hicieron exactamente 3 peticiones (offsets 0, 2 y 4). Así probamos la lógica de
paginación sin internet, de forma rápida y repetible.

Cada test sigue el patrón **Arrange → Act → Assert**: preparar datos, ejecutar y verificar.

## 6. Qué descubrimos (y cómo influye en la Fase 2)

| Hallazgo | Decisión de diseño |
|---|---|
| Montos y fechas llegan como texto | Convertirlos a `NUMERIC` y `DATE` al cargar (Fase 3) |
| Hay `"No Definido"`, ceros y campos ausentes | Validación y limpieza con Pydantic antes de guardar |
| Entidad y proveedor se repiten en muchos contratos | Tablas separadas `entidades` y `proveedores` (normalización) |
| NITs con formatos distintos (`890.000.002-5` vs `890000002`) | Normalizar el NIT: solo dígitos y sin dígito de verificación |
| `ultima_actualizacion` en cada registro | Usarla para la ingesta **incremental** (solo traer lo nuevo) |

## 🏋️ Ejercicios

1. Descarga 2000 contratos reales de tu departamento usando `--where`.
2. Agrega a `resumen_negocio()` la clave `"contratos_por_departamento"` y escribe un test para ella.
3. En el perfil de los datos reales, ¿qué columna tiene más nulos? ¿La necesitamos?
4. Escribe una función `normalizar_nit("890.000.002-5")` que devuelva `"890000002"`, con sus
   tests. (Pista: quita el dígito de verificación que va después del guion y deja solo dígitos.)
   La usaremos en la Fase 3.
