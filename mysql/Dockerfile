
FROM mysql:latest

# Set root password and create database
ENV MYSQL_ROOT_PASSWORD=password
ENV MYSQL_DATABASE=events

# Copy SQL script to initialize the database
COPY init.sql /docker-entrypoint-initdb.d/1-init.sql

# Expose the MySQL port
EXPOSE 3306

# Start MySQL service
CMD ["mysqld"]