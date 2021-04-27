<?php

namespace Vdhicts\Cyberfusion\ClusterApi\Enums;

class ShellPath
{
    public const BASH = '/bin/bash';
    public const JAIL_SHELL = '/usr/local/bin/jailshell';

    public const DEFAULT = self::BASH;

    public const AVAILABLE = [
        self::BASH,
        self::JAIL_SHELL,
    ];
}
