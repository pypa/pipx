<?php

namespace Vdhicts\Cyberfusion\ClusterApi\Enums;

class DatabaseEngine
{
    public const SERVER_SOFTWARE_MARIADB = 'MariaDB';
    public const SERVER_SOFTWARE_POSTGRES = 'PostgreSQL';

    public const AVAILABLE = [
        self::SERVER_SOFTWARE_MARIADB,
        self::SERVER_SOFTWARE_POSTGRES,
    ];
}
