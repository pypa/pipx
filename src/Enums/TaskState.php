<?php

namespace Cyberfusion\ClusterApi\Enums;

class TaskState
{
    public const STATE_PENDING = 'pending';
    public const STATE_STARTED = 'started';
    public const STATE_SUCCESS = 'success';
    public const STATE_FAILURE = 'failure';
    public const STATE_RETRY = 'retry';
    public const STATE_REVOKED = 'revoked';

    public const AVAILABLE = [
        self::STATE_PENDING,
        self::STATE_STARTED,
        self::STATE_SUCCESS,
        self::STATE_FAILURE,
        self::STATE_RETRY,
        self::STATE_REVOKED,
    ];
}
