# phonetrack-server
A simple PostgreSQL server with PostGIS for the Open Source GPS logging app [Phonetrack](https://f-droid.org/en/packages/net.eneiluj.nextcloud.phonetrack/).

## Introduction
The Phonetrack app on Android continuously runs in the background and records the device's GPS location according to various parameters.

While it was mainly built with a Nextcloud instance in mind, the GPS points can be sent to any web server able to receive HTTP GET or POST requests.
If there is no internet connection, points will be buffered until the next time the phone establishes a connection.

phonetrack-server is a simple API endpoint which allows you to store the client's GPS point POSTs to a PostgreSQL database with PostGIS enabled. When it receives a point, it stores it as a `POINT` object in PostGIS and assigns a track ID. Depending on the environment variables set, it will either add the point to an existing track or create a new one. This way, you can visualize tracks directly using a GIS viewer such as QGIS.

## Installation
Use the pre-built image on Docker Hub [`gitc23/phonetrack-server`](https://hub.docker.com/r/gitc23/phonetrack-server) and connect it to a PostgreSQL database with PostGIS enabled.

For nginx to work, you need to have a folder with at least `nginx.conf` present. Copy the sample config to get started right away. If you want to allow only specific clients to be able to connect to the server, uncomment the respective lines in `nginx.conf` and add them to the `allow-list.conf`.

### Using an existing PostgreSQL database

```yaml
services:
  api:
    build: 
      context: ./services/api
      dockerfile: Dockerfile
    command: gunicorn --bind 0.0.0.0:5000 manage:app
    expose:
      - 5000
    environment:
    # use host.docker.internal in URL and as SQL_HOST if the database is on the same machine
      - SQL_HOST=host
      - SQL_PORT=port
      - DATABASE_URL=postgresql://user:password@host:port/dbname
      - DISTANCE_THRESHOLD=500
      - TIME_THRESHOLD=900
  nginx:
    image: nginx:1.25
    volumes:
      - ./services/nginx:/etc/nginx/conf.d
    ports:
      - 8080:80
    depends_on:
      - api
```

### Using the PostGIS Docker image
```yaml
version: '3.8'

services:
  api:
    build: 
      context: ./services/api
      dockerfile: Dockerfile
    command: gunicorn --bind 0.0.0.0:5000 manage:app
    expose:
      - 5000
    environment:
      - SQL_HOST=db
      - SQL_PORT=5432
      - DATABASE_URL=postgresql://PG_USER:PG_PASSWORD@db:5432/phonetrack-server
      - DISTANCE_THRESHOLD=500
      - TIME_THRESHOLD=900
    depends_on:
      - db
  db:
    image: postgis/postgis:16-3.4
    volumes:
      - postgres_data:/var/lib/postgresql/data/
    environment:
      - POSTGRES_USER=PG_USER
      - POSTGRES_PASSWORD=PG_PASSWORD
      - POSTGRES_DB=phonetrack-server
  nginx:
    image: nginx:1.25
    volumes:
      - ./services/nginx:/etc/nginx/conf.d
    ports:
      - 8080:80
    depends_on:
      - api

volumes:
  postgres_data:
```

After running `docker-compose up -d`, create the initial database:
```shell
docker-compose exec api python manage.py create_db
```

You can now connect to it using the credentials set in the `ENV` parameters of the api image:
```shell
docker-compose exec db psql --username=PG_USER --dbname=POSTGRES_DB
```

#### Using the PostGIS image with an SQL dump
If you have an existing database dump you would like to use, supply it as an additional volume mount of the db image
```yaml
  ...
  db:
    image: postgis/postgis:16-3.4
    volumes:
      - ./dump.sql:/docker-entrypoint-initdb.d/dump.sql
      - postgres_data:/var/lib/postgresql/data/
  ...
```

Make sure that this database dump has been created using `pg_dump -Ox -t points -t tracks > dump.sql`
and that the sequence/identity column has not been reset. Otherwise, any new points will start with a resetted sequence.

Check the last lines of your dump file contain the last value of your id column, not 1.
```sql
--
-- Name: points_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.points_id_seq', lastval_of_id_column, true);
```

## Receiving Data
When everything is set up correctly, you should be able to reach the server on the designated port (`8080` in the example).

Set this as `Target address` in the Phonetrack app on your client device: 
```
http://HOST:PORT/post?lat=%LAT&lon=%LON&tst=%TIMESTAMP&alt=%ALT&acc=%ACC&vel=%SPD&sat=%SAT&batt=%BATT&tid=%UA
```
For the endpoint to work, you need at least `LAT`, `LON` and `TIMESTAMP`.

Enable `Use POST method` and you should be good to go.