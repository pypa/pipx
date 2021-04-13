<?php

namespace Vdhicts\Cyberfusion\ClusterApi\Enums;

class ShellPath
{
    public const BASH = '/bin/bash';
    public const NO_LOGIN = '/usr/sbin/nologin';
    public const JAIL_SHELL = '/usr/local/bin/jailshell';

    public const DEFAULT = self::BASH;

    public const AVAILABLE = [
        self::BASH,
        self::NO_LOGIN,
        self::JAIL_SHELL,
    ];
}
