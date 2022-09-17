<?php

namespace Cyberfusion\ClusterApi\Enums;

class CmsConfigurationConstantName
{
    public const DB_NAME = 'DB_NAME';
    public const DB_USER = 'DB_USER';
    public const DB_PASSWORD = 'DB_PASSWORD';
    public const DB_HOST = 'DB_HOST';

    public const AVAILABLE = [
        self::DB_NAME,
        self::DB_USER,
        self::DB_PASSWORD,
        self::DB_HOST,
    ];
}
