<?php

namespace Vdhicts\Cyberfusion\ClusterApi\Enums;

class AllowOverrideOptionDirectives
{
    public const ALL = 'All';
    public const FOLLOW_SYM_LINKS = 'FollowSymLinks';
    public const INDEXES = 'Indexes';
    public const MULTI_VIEWS = 'MultiViews';
    public const SYM_LINKS_IF_OWNER_MATCH = 'SymLinksIfOwnerMatch';
    public const NONE = 'None';

    public const DEFAULTS = [
        self::INDEXES,
        self::MULTI_VIEWS,
        self::SYM_LINKS_IF_OWNER_MATCH,
        self::NONE,
    ];

    public const AVAILABLE = [
        self::ALL,
        self::FOLLOW_SYM_LINKS,
        self::INDEXES,
        self::MULTI_VIEWS,
        self::SYM_LINKS_IF_OWNER_MATCH,
        self::NONE,
    ];
}
