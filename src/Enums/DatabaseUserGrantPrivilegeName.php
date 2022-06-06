<?php

namespace Vdhicts\Cyberfusion\ClusterApi\Enums;

class DatabaseUserGrantPrivilegeName
{
    public const ALL = 'ALL';
    public const SELECT = 'SELECT';

    public const DEFAULT = self::ALL;

    public const AVAILABLE = [
        self::ALL,
        self::SELECT,
    ];
}
