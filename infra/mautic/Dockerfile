# Mautic 5 para Railway: imagen oficial + arranque que persiste config/media en un
# solo volumen, se instala sola y corre web + tareas programadas en un servicio.
FROM mautic/mautic:5-apache

COPY railway-entrypoint.sh /railway-entrypoint.sh
RUN chmod +x /railway-entrypoint.sh

# Railway enruta al puerto de la variable PORT; Apache escucha en 80 (PORT=80).
EXPOSE 80
ENTRYPOINT ["/railway-entrypoint.sh"]
CMD ["apache2-foreground"]
