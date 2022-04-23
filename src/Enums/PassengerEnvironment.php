<?php

namespace Vdhicts\Cyberfusion\ClusterApi\Enums;

class PassengerEnvironment
{
    public const PRODUCTION = 'production';
    public const DEVELOPMENT = 'development';

    public const AVAILABLE = [
        self::PRODUCTION,
        self::DEVELOPMENT,
    ];
}