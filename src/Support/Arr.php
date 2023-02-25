<?php

namespace Cyberfusion\ClusterApi\Support;

class Arr extends \Illuminate\Support\Arr
{
    /**
     * Removes the value from the array.
     */
    public static function exceptValue(array $array, mixed $value): array
    {
        if (!in_array($value, $array)) {
            return $array;
        }

        unset($array[$value]);

        return $array;
    }

    public static function keysExists(array $keys, array $source): bool
    {
        foreach ($keys as $key) {
            if (!array_key_exists($key, $source)) {
                return false;
            }
        }

        return true;
    }
}
