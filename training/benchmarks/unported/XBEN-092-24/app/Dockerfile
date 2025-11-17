FROM php:8.0-apache

WORKDIR /var/www/html

RUN apt-get update && apt-get install -y \
    zip \
    unzip \
    git \
    sqlite3 \
    libsqlite3-dev \
    && docker-php-ext-install pdo pdo_sqlite

COPY --from=composer:latest /usr/bin/composer /usr/bin/composer

COPY . /var/www/html
COPY composer.json /var/www/html/composer.json

COPY wwwconf/app_conf.conf /etc/apache2/app_conf.conf
COPY wwwconf/app_conf.conf /etc/apache2/sites-available/app_conf.conf

RUN groupadd -g 1000 appuser && \
    useradd -u 1000 -g appuser -m appuser

RUN chown -R appuser:appuser /var/www/html

    RUN mkdir -p /var/db && \
    chown -R www-data:www-data /var/db

USER appuser
RUN composer install 

USER root
RUN chown -R www-data:www-data /var/www/html/vendor

EXPOSE 8081

CMD ["apache2-foreground"]
