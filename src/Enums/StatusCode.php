<?php

namespace Cyberfusion\ClusterApi\Enums;

class StatusCode
{
    public const MOVED_PERMANENTLY = 301;
    public const MOVED_TEMPORARILY = 302;
    public const SEE_OTHER = 303;
    public const TEMPORARY_REDIRECT = 307;
    public const PERMANENT_REDIRECT = 308;

    public const DEFAULT = self::MOVED_PERMANENTLY;

    public const AVAILABLE = [
        self::MOVED_PERMANENTLY,
        self::MOVED_TEMPORARILY,
        self::SEE_OTHER,
        self::TEMPORARY_REDIRECT,
        self::PERMANENT_REDIRECT,
    ];
}
