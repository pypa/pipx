<?php

namespace Cyberfusion\ClusterApi\Enums;

class RedisInstanceEvictionPolicy
{
    public const VOLATILE_TTL = 'volatile-ttl';
    public const VOLATILE_RANDOM = 'volatile-random';
    public const ALLKEYS_RANDOM = 'allkeys-random';
    public const VOLATILE_LFU = 'volatile-lfu';
    public const VOLATILE_LRU = 'volatile-lru';
    public const ALLKEYS_LFU = 'allkeys-lfu';
    public const ALLKEYS_LRU = 'allkeys-lru';
    public const NOEVICTION = 'noeviction';

    public const AVAILABLE = [
        self::VOLATILE_TTL,
        self::VOLATILE_RANDOM,
        self::ALLKEYS_RANDOM,
        self::VOLATILE_LFU,
        self::VOLATILE_LRU,
        self::ALLKEYS_LFU,
        self::ALLKEYS_LRU,
        self::NOEVICTION,
    ];
}
