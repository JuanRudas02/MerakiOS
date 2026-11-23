#!/bin/bash
# Arranque de Mautic 5 para Railway (un solo servicio: web + tareas programadas).
#
# Railway permite un volumen por servicio y no lo comparte entre servicios, así que:
#   - config/ y media/ viven en el volumen ($MAUTIC_DATA_DIR) mediante enlaces.
#   - el cron de Mautic corre en segundo plano en este mismo contenedor.
#   - la primera vez se instala sola con MAUTIC_SITE_URL / MAUTIC_ADMIN_* .
# Variables: MAUTIC_DB_HOST, MAUTIC_DB_PORT, MAUTIC_DB_DATABASE, MAUTIC_DB_USER,
# MAUTIC_DB_PASSWORD, MAUTIC_SITE_URL, MAUTIC_ADMIN_EMAIL, MAUTIC_ADMIN_PASSWORD,
# MAUTIC_ADMIN_USERNAME (opcional, "admin"), MAUTIC_MAILER_DSN (opcional, null://null).
set -euo pipefail
source /startup/logger.sh

APP=/var/www/html
DATA="${MAUTIC_DATA_DIR:-/data}"
export DOCKER_MAUTIC_ROLE=mautic_web
export MAUTIC_DB_PORT="${MAUTIC_DB_PORT:-3306}"

# ── 1. config/local.php en el volumen persistente ───────────────────────────
# La imagen oficial declara config/ y media/ como VOLUME (no se pueden reemplazar),
# así que se persiste el archivo crítico: local.php (BD, instalación y ajustes).
# Mautic escribe local.php con file_put_contents, que sigue el enlace simbólico.
mkdir -p "$DATA/config"
if [ ! -f "$DATA/config/local.php" ]; then
  log "[1heavy] primer arranque: creando local.php en el volumen"
  cp -p /templates/local.php "$DATA/config/local.php"
fi
ln -sfn "$DATA/config/local.php" "$APP/config/local.php"
chown -R www-data:www-data "$DATA" "$APP/config"

# ── 2. mismas verificaciones que la imagen oficial ──────────────────────────
# (mismas variables que define /entrypoint.sh de la imagen oficial)
export MAUTIC_VOLUME_CONFIG="$APP/config" MAUTIC_VOLUME_LOGS="$APP/var/logs" \
  MAUTIC_VOLUME_MEDIA="$APP/docroot/media" MAUTIC_VOLUME_FILES="$APP/docroot/media/files" \
  MAUTIC_VOLUME_IMAGES="$APP/docroot/media/images" MAUTIC_VAR="$APP/var" \
  MAUTIC_CONSOLE="$APP/bin/console" MAUTIC_WWW_USER=www-data MAUTIC_WWW_GROUP=www-data
mkdir -p "$MAUTIC_VOLUME_LOGS" "$MAUTIC_VOLUME_FILES" "$MAUTIC_VOLUME_IMAGES"
chown -R www-data:www-data "$MAUTIC_VAR"
/startup/check_database_connection.sh
/startup/check_local_php_exists.sh

console() { su -s /bin/bash www-data -c "php $MAUTIC_CONSOLE $*"; }
installed() {
  php -r "include('$APP/config/local.php'); exit(!empty(\$parameters['db_driver']) && !empty(\$parameters['site_url']) ? 0 : 1);"
}

# ── 3. instalación automática (sólo si no está instalado) ───────────────────
if ! installed; then
  : "${MAUTIC_SITE_URL:?Falta MAUTIC_SITE_URL}" "${MAUTIC_ADMIN_EMAIL:?Falta MAUTIC_ADMIN_EMAIL}" "${MAUTIC_ADMIN_PASSWORD:?Falta MAUTIC_ADMIN_PASSWORD}"
  log "[1heavy] instalando Mautic en ${MAUTIC_SITE_URL}"
  su -s /bin/bash www-data -c "php $MAUTIC_CONSOLE mautic:install '$MAUTIC_SITE_URL' --force \
    --db_driver=pdo_mysql --db_host='$MAUTIC_DB_HOST' --db_port='$MAUTIC_DB_PORT' \
    --db_name='$MAUTIC_DB_DATABASE' --db_user='$MAUTIC_DB_USER' --db_password='$MAUTIC_DB_PASSWORD' \
    --admin_firstname=Admin --admin_lastname=1heavy --admin_username='${MAUTIC_ADMIN_USERNAME:-admin}' \
    --admin_email='$MAUTIC_ADMIN_EMAIL' --admin_password='$MAUTIC_ADMIN_PASSWORD'"
fi

# ── 4. ajustes que 1heavy necesita (idempotente en cada arranque) ───────────
su -s /bin/bash www-data -c "php -r '
  \$f=\"$APP/config/local.php\"; include \$f;
  \$parameters[\"api_enabled\"]=true;
  \$parameters[\"api_enable_basic_auth\"]=true;
  \$parameters[\"trusted_proxies\"]=[\"0.0.0.0/0\",\"::/0\"];
  \$parameters[\"mailer_dsn\"]=getenv(\"MAUTIC_MAILER_DSN\") ?: (\$parameters[\"mailer_dsn\"] ?? \"null://null\");
  if (getenv(\"MAUTIC_SITE_URL\")) { \$parameters[\"site_url\"]=getenv(\"MAUTIC_SITE_URL\"); }
  file_put_contents(\$f, \"<?php\\n\\\$parameters = \".var_export(\$parameters,true).\";\\n\");
'"
console cache:clear >/dev/null 2>&1 || true

# ── 5. un solo MPM (prefork) por si el entorno activó otro ──────────────────
rm -f /etc/apache2/mods-enabled/mpm_event.* /etc/apache2/mods-enabled/mpm_worker.*
[ -e /etc/apache2/mods-enabled/mpm_prefork.load ] || a2enmod mpm_prefork >/dev/null

# ── 6. tareas programadas en segundo plano + web en primer plano ────────────
DOCKER_MAUTIC_ROLE=mautic_cron /entrypoint_mautic_cron.sh &
exec /entrypoint_mautic_web.sh "$@"
