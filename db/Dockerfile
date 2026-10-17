FROM postgres:16

# Every *.sql file in this folder runs once, on first start with an empty volume
COPY init/ /docker-entrypoint-initdb.d/
