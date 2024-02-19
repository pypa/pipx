<?php

namespace Cyberfusion\ClusterApi\Enums;

class DomainRouterCategory
{
    public const GRAFANA = 'Grafana';
    public const SINGLE_STORE_STUDIO = 'SingleStore Studio';
    public const SINGLE_STORE_API = 'SingleStore API';
    public const METABASE = 'Metabase';
    public const KIBANA = 'Kibana';
    public const RABBITMQ_MANAGEMENT = 'RabbitMQ Management';
    public const VIRTUAL_HOST = 'Virtual Host';
    public const URL_REDIRECT = 'URL Redirect';

    public const AVAILABLE = [
        self::GRAFANA,
        self::SINGLE_STORE_STUDIO,
        self::SINGLE_STORE_API,
        self::METABASE,
        self::KIBANA,
        self::RABBITMQ_MANAGEMENT,
        self::VIRTUAL_HOST,
        self::URL_REDIRECT,
    ];
}
