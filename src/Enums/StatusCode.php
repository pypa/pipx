<?php

namespace Vdhicts\Cyberfusion\ClusterApi\Enums;

class StatusCode
{
    public const MOVED_PERMANENTLY = 301;
    public const MOVED_TEMPORARILY = 302;
    public const SEE_OTHER = 303;

    public const DEFAULT = self::MOVED_PERMANENTLY;

    public const AVAILABLE = [
        self::MOVED_PERMANENTLY,
        self::MOVED_TEMPORARILY,
        self::SEE_OTHER,
    ];
}
