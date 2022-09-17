<?php

namespace Cyberfusion\ClusterApi\Enums;

class BorgArchiveObjectType
{
    public const REGULAR_FILE = 'regular_file';
    public const DIRECTORY = 'directory';
    public const SYMBOLIC_LINK = 'symbolic_link';

    public const AVAILABLE = [
        self::REGULAR_FILE,
        self::DIRECTORY,
        self::SYMBOLIC_LINK,
    ];
}
