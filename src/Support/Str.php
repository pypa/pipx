<?php

namespace Cyberfusion\ClusterApi\Support;

class Str extends \Illuminate\Support\Str
{
    /**
     * Determines if the pattern matches on the string.
     */
    public static function doesMatch(string $string, string $pattern): bool
    {
        return preg_match($pattern, $string) != false;
    }

    /**
     * Determines the full url based on the available optional query parameters. Filters out null values of the
     * parameters.
     */
    public static function optionalQueryParameters(string $url, array $parameters): string
    {
        $parameters = array_filter($parameters);
        if (count($parameters) === 0) {
            return $url;
        }

        return $url . '?' . http_build_query($parameters);
    }
}
