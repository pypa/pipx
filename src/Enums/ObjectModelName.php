<?php

namespace Cyberfusion\ClusterApi\Enums;

class ObjectModelName
{
    public const BORG_ARCHIVE = 'BorgArchive';
    public const BORG_REPOSITORY = 'BorgRepository';
    public const CLUSTER = 'Cluster';
    public const CMS = 'CMS';
    public const FPM_POOL = 'FPMPool';
    public const VIRTUAL_HOST = 'VirtualHost';
    public const PASSENGER_APP = 'PassengerApp';
    public const DATABASE = 'Database';
    public const CERTIFICATE_MANAGER = 'CertificateManager';
    public const BASIC_AUTHENTICATION_REALM = 'BasicAuthenticationRealm';
    public const CRON = 'Cron';
    public const DATABASE_USER = 'DatabaseUser';
    public const DATABASE_USER_GRANT = 'DatabaseUserGrant';
    public const HTPASSWD_FILE = 'HtpasswdFile';
    public const HTPASSWD_USER = 'HtpasswdUser';
    public const MAIL_ACCOUNT = 'MailAccount';
    public const MAIL_ALIAS = 'MailAlias';
    public const MAIL_DOMAIN = 'MailDomain';
    public const NODE = 'Node';
    public const REDIS_INSTANCE = 'RedisInstance';
    public const DOMAIN_ROUTER = 'DomainRouter';
    public const MAIL_HOSTNAME = 'MailHostname';
    public const CERTIFICATE = 'Certificate';
    public const ROOT_SSH_KEY = 'RootSSHKey';
    public const SSH_KEY = 'SSHKey';
    public const UNIX_USER = 'UNIXUser';
    public const UNIX_USER_RABBIT_MQ_CREDENTIALS = 'UNIXUserRabbitMQCredentials';
    public const HA_PROXY_LISTEN = 'HAProxyListen';
    public const HA_PROXY_LISTEN_TO_NODE = 'HAProxyListenToNode';
    public const URL_REDIRECT = 'URLRedirect';
    public const DAEMON = 'Daemon';

    public const AVAILABLE = [
        self::BORG_ARCHIVE,
        self::BORG_REPOSITORY,
        self::CLUSTER,
        self::CMS,
        self::FPM_POOL,
        self::VIRTUAL_HOST,
        self::PASSENGER_APP,
        self::DATABASE,
        self::CERTIFICATE_MANAGER,
        self::BASIC_AUTHENTICATION_REALM,
        self::CRON,
        self::DATABASE_USER,
        self::DATABASE_USER_GRANT,
        self::HTPASSWD_FILE,
        self::HTPASSWD_USER,
        self::MAIL_ACCOUNT,
        self::MAIL_ALIAS,
        self::MAIL_DOMAIN,
        self::NODE,
        self::REDIS_INSTANCE,
        self::DOMAIN_ROUTER,
        self::MAIL_HOSTNAME,
        self::CERTIFICATE,
        self::ROOT_SSH_KEY,
        self::SSH_KEY,
        self::UNIX_USER,
        self::UNIX_USER_RABBIT_MQ_CREDENTIALS,
        self::HA_PROXY_LISTEN,
        self::HA_PROXY_LISTEN_TO_NODE,
        self::URL_REDIRECT,
        self::DAEMON
    ];
}
