<?php

namespace Cyberfusion\ClusterApi\Enums;

class VirtualHostServerSoftwareName
{
    public const SERVER_SOFTWARE_APACHE = 'Apache';
    public const SERVER_SOFTWARE_NGINX = 'nginx';

    public const AVAILABLE = [
        self::SERVER_SOFTWARE_APACHE,
        self::SERVER_SOFTWARE_NGINX,
    ];
}
