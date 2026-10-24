FROM postgres:16

# *.sql files from this folder run once, on first start with an empty volume
COPY app/REST/db/init/ /docker-entrypoint-initdb.d/
