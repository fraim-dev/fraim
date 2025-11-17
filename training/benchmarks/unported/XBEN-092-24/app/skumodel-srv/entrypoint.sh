#!/bin/sh

# Start PHP-FPM
php-fpm -D

# Start Nginx
app_conf -g 'daemon off;'
