# Power BI dashboard

Power BI Desktop reads the same PostgreSQL database as the app, through the `review_facts` view: one row per review
with its date, stars, group (Spanish text, other language, stars only) and the model's prediction. With DirectQuery
and automatic page refresh, the report shows new reviews as soon as they are downloaded (decisions D-006, D-023).

Power BI Desktop is free and runs on Windows. Menu names below are those of the Spanish interface.

## 1. Before starting

1. Start the project with Docker: `docker compose up --build` (see the README). PostgreSQL listens on
   `localhost:5432`, database `impacto`, user `impacto`, password `impacto` (or `POSTGRES_PASSWORD` from `.env`).
2. Install **Power BI Desktop** from the Microsoft Store (free; no account needed for local reports).

## 2. Connect to the database

1. **Inicio → Obtener datos → Más… → Base de datos → Base de datos PostgreSQL → Conectar.**
2. **Servidor:** `localhost:5432` · **Base de datos:** `impacto` · **Modo de conectividad de datos: DirectQuery**.
   DirectQuery queries the database every time the report refreshes, instead of copying the data into the file.
   It is what allows automatic page refresh.
3. Credentials: tab **Base de datos**, user `impacto`, password `impacto`.
   If Power BI warns that the connection is not encrypted, accept connecting without encryption: the database only
   listens on this computer.
4. In the **Navegador**, tick only `public.review_facts` and press **Cargar**. The view already joins the tables, so
   the raw tables are not needed.
5. Power BI names the table `public review_facts`. Rename it to `review_facts` (**Datos** pane, right click →
   **Cambiar nombre**) so the measures below work as written.

| Column | Meaning |
|---|---|
| `place_name` | Business |
| `published_at`, `published_date`, `published_month` | Publication date and time, day, and first day of the month |
| `stars` | 1 to 5 |
| `low_stars` | 1 if the review has 1–2 stars |
| `review_group` | `Texto en español`, `Texto en otro idioma` or `Solo estrellas` |
| `model_label` | `Good` / `Bad` (empty if the model cannot read the review) |
| `model_bad` | 1 bad, 0 good, empty if not classified |
| `model_probability` | Probability of good according to the model |
| `text`, `likes` | Review text and likes |

## 3. Measures

Each measure holds a single formula. For each line below: select `review_facts` in the **Datos** pane, press
**Inicio → Nueva medida**, replace the text of the formula bar with the line and press Enter.

```dax
Reseñas = COUNTROWS ( review_facts )
```

```dax
Nota media = AVERAGE ( review_facts[stars] )
```

```dax
% malas (modelo) = DIVIDE ( SUM ( review_facts[model_bad] ), COUNT ( review_facts[model_bad] ) )
```

```dax
% 1-2 estrellas = DIVIDE ( SUM ( review_facts[low_stars] ), COUNTROWS ( review_facts ) )
```

`COUNT` skips empty values, so `% malas (modelo)` only counts the reviews the model classified, as in the app. Give
the two percentage measures the percentage format (**Herramientas de medición → Formato → Porcentaje**).

## 4. Visuals

The same story as the app, in the same colours (model blue `#2a78d6`, stars orange `#eb6834`, good blue `#2a78d6`,
bad red `#e34948`):

1. **Segmentación de datos** with `place_name`: choose the business.
2. **Tarjetas** with `Reseñas`, `Nota media`, `% malas (modelo)` and `% 1-2 estrellas`.
3. **Gráfico de líneas:** eje X `published_month`, eje Y `% malas (modelo)` and `% 1-2 estrellas`. One axis only,
   both are percentages.
4. **Gráfico de columnas agrupadas:** eje X `published_month`, eje Y `Reseñas`, in gray. Volume goes in its own chart,
   never as a second axis of the line chart.
5. **Gráfico de barras 100 % apiladas:** eje Y `stars`, leyenda `model_label`, valores `Reseñas`, with a visual filter
   `model_label` "no está en blanco": how the model classifies each star rating.
6. **Tabla** with `published_date`, `stars`, `model_label`, `text`, filtered by `model_label = Bad` and sorted by date:
   the latest bad reviews.

## 5. Automatic page refresh

1. Click on an empty area of the page.
2. **Visualizaciones → Formato de la página (brush icon) → Actualización de la página → Activado.**
3. **Tipo de actualización: Intervalo fijo**, for example every 5 minutes.

Power BI Desktop allows any interval with DirectQuery. In the Power BI service without a paid licence the minimum is
30 minutes (D-006). New reviews arrive when someone presses "Actualizar reseñas" in the app or runs
`pipeline/update_reviews.py` (updates are manual, D-022).

## 6. Save

Save the report as `powerbi/impacto.pbix`. In DirectQuery mode the file keeps the report design, not the data.
