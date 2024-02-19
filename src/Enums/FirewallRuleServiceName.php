<?php

namespace Cyberfusion\ClusterApi\Enums;

class FirewallRuleServiceName
{
    public const SSH = 'SSH';
    public const PRO_FTPD = 'ProFTPD';
    public const NGINX = 'nginx';
    public const APACHE = 'Apache';

    public const AVAILABLE = [
        self::SSH,
        self::PRO_FTPD,
        self::NGINX,
        self::APACHE,
    ];
}
