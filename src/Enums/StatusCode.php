<?php

namespace Vdhicts\Cyberfusion\ClusterApi\Enums;

class StatusCode
{
    public const MULTIPLE_CHOICE = 300;
    public const MOVED_PERMANENTLY = 301;
    public const MOVED_TEMPORARILY = 302;

    public const DEFAULT = self::MOVED_PERMANENTLY;

    public const AVAILABLE = [
        self::MULTIPLE_CHOICE,
        self::MOVED_PERMANENTLY,
        self::MOVED_TEMPORARILY,
    ];
}
