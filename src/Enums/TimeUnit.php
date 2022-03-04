<?php

namespace Vdhicts\Cyberfusion\ClusterApi\Enums;

class TimeUnit
{
    public const HOURLY = 'hourly';
    public const DAILY = 'daily';
    public const WEEKLY = 'weekly';
    public const MONTHLY = 'monthly';

    public const AVAILABLE = [
        self::HOURLY,
        self::DAILY,
        self::WEEKLY,
        self::MONTHLY,
    ];
}
