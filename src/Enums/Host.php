<?php

namespace Vdhicts\Cyberfusion\ClusterApi\Enums;

class Host
{
    public const HOST_ALL = '%';
    public const HOST_LOCAL = '::1';

    public const AVAILABLE = [
        self::HOST_ALL,
        self::HOST_LOCAL,
    ];
}
