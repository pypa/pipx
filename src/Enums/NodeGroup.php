<?php

namespace Cyberfusion\ClusterApi\Enums;

class NodeGroup
{
    public const ADMIN = 'Admin';
    public const APACHE = 'Apache';
    public const BORG = 'Borg';
    public const COMPOSER = 'Composer';
    public const DOCKER = 'Docker';
    public const DOVECOT = 'Dovecot';
    public const ELASTICSEARCH = 'Elasticsearch';
    public const FAST_REDIRECT = 'Fast Redirect';
    public const FFMPEG = 'FFmpeg';
    public const GHOST_SCRIPT = 'Ghostscript';
    public const GNU_MAILUTILS = 'GNU Mailutils';
    public const GRAFANA = 'Grafana';
    public const HA_PROXY = 'HAProxy';
    public const IMAGE_MAGICK = 'ImageMagick';
    public const KERNEL_CARE = 'KernelCare';
    public const LIBRE_OFFICE = 'LibreOffice';
    public const MALDET = 'maldet';
    public const MARIADB = 'MariaDB';
    public const METABASE = 'Metabase';
    public const NGINX = 'nginx';
    public const PASSENGER = 'Passenger';
    public const PHP = 'PHP';
    public const POSTGRESQL = 'PostgreSQL';
    public const PRO_FTPD = 'ProFTPD';
    public const PUPPETEER = 'Puppeteer';
    public const RABBITMQ = 'RabbitMQ';
    public const REDIS = 'Redis';
    public const SINGLE_STORE = 'SingleStore';
    public const WKHTMLTOPDF = 'wkhtmltopdf';
    public const WP_CLI = 'WP-CLI';
    public const MEILISEARCH = 'Meilisearch';
    public const NEW_RELIC = 'New Relic';

    public const AVAILABLE = [
        self::ADMIN,
        self::APACHE,
        self::BORG,
        self::COMPOSER,
        self::DOCKER,
        self::DOVECOT,
        self::ELASTICSEARCH,
        self::FAST_REDIRECT,
        self::FFMPEG,
        self::GHOST_SCRIPT,
        self::GNU_MAILUTILS,
        self::GRAFANA,
        self::HA_PROXY,
        self::IMAGE_MAGICK,
        self::KERNEL_CARE,
        self::LIBRE_OFFICE,
        self::MALDET,
        self::MARIADB,
        self::METABASE,
        self::NGINX,
        self::PASSENGER,
        self::PHP,
        self::POSTGRESQL,
        self::PRO_FTPD,
        self::PUPPETEER,
        self::RABBITMQ,
        self::REDIS,
        self::SINGLE_STORE,
        self::WKHTMLTOPDF,
        self::WP_CLI,
        self::MEILISEARCH,
        self::NEW_RELIC,
    ];
}
