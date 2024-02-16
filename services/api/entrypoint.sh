#!/bin/sh

if [ "$DATABASE" = "postgres" ]
then
    echo "Waiting for location database..."

    while ! nc -z $SQL_HOST $SQL_PORT; do
      sleep 0.1
    done

    echo "PostgreSQL started"
fi

exec "$@"