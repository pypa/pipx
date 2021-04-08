<?php

namespace Vdhicts\Cyberfusion\ClusterApi\Enums;

class AllowOverrideDirectives
{
    public const ALL = 'All';
    public const AUTH_CONFIG = 'AuthConfig';
    public const FILE_INFO = 'FileInfo';
    public const INDEXES = 'Indexes';
    public const LIMIT = 'Limit';
    public const NONE = 'None';

    public const DEFAULTS = [
        self::AUTH_CONFIG,
        self::FILE_INFO,
        self::INDEXES,
        self::LIMIT,
    ];

    public const AVAILABLE = [
        self::ALL,
        self::AUTH_CONFIG,
        self::FILE_INFO,
        self::INDEXES,
        self::LIMIT,
        self::NONE,
    ];
}
