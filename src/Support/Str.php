<?php

namespace Vdhicts\Cyberfusion\ClusterApi\Support;

class Str extends \Illuminate\Support\Str
{
    /**
     * Determines if the pattern matches on the string.
     *
     * @param string $string
     * @param string $pattern
     * @return bool
     */
    public static function match(string $string, string $pattern): bool
    {
        return preg_match($pattern, $string) != false;
    }
}
