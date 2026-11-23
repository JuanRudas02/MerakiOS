# Mautic 5 para Railway: imagen oficial + arranque que persiste config/media en un
# solo volumen, se instala sola y corre web + tareas programadas en un servicio.
FROM mautic/mautic:5-apache

# PHP con mod_php requiere el MPM prefork. Se garantiza un único MPM: en Railway
# (amd64) Apache fallaba con "More than one MPM loaded".
RUN a2dismod -f mpm_event mpm_worker >/dev/null 2>&1 || true \
    && a2enmod mpm_prefork >/dev/null \
    && ls /etc/apache2/mods-enabled/ | grep -c '^mpm_.*\.load$' | grep -qx 1

# Verificación de salud: Apache responde /healthz con un archivo fuera de la app,
# sin pasar por Mautic (que redirige a https cuando el healthcheck interno llega
# por http). Railway no acepta rutas con punto, por eso es /healthz.
RUN echo ok > /var/www/healthz.txt \
    && printf 'Alias /healthz /var/www/healthz.txt\n<Location /healthz>\n  Require all granted\n</Location>\n' \
       > /etc/apache2/conf-enabled/healthz.conf

COPY railway-entrypoint.sh /railway-entrypoint.sh
RUN chmod +x /railway-entrypoint.sh

# Railway enruta al puerto de la variable PORT; Apache escucha en 80 (PORT=80).
EXPOSE 80
ENTRYPOINT ["/railway-entrypoint.sh"]
CMD ["apache2-foreground"]
