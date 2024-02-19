<?php

namespace Cyberfusion\ClusterApi\Enums;

class FirewallRuleExternalProviderName
{
    public const ATLASSIAN = 'Atlassian';
    public const BUDDY = 'Buddy';
    public const GOOGLE_CLOUD = 'Google Cloud';

    public const AVAILABLE = [
        self::ATLASSIAN,
        self::BUDDY,
        self::GOOGLE_CLOUD,
    ];
}
