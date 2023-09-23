<?php

namespace Cyberfusion\ClusterApi\Endpoints;

use Cyberfusion\ClusterApi\Contracts\Client as ClientContract;
use Cyberfusion\ClusterApi\Contracts\Model;
use Cyberfusion\ClusterApi\Exceptions\RequestException;
use Cyberfusion\ClusterApi\Support\Arr;

abstract class Endpoint
{
    public function __construct(protected ClientContract $client)
    {
    }

    /**
     * @throws RequestException
     */
    protected function validateRequired(Model $model, string $action, array $requiredAttributes = []): void
    {
        $modelFields = $model->toArray();

        $missing = [];
        foreach ($requiredAttributes as $requiredAttribute) {
            if (!array_key_exists($requiredAttribute, $modelFields)) {
                $missing[] = $requiredAttribute;
                continue;
            }

            $value = $modelFields[$requiredAttribute] ?? null;
            if (is_string($value) && trim($value) === '') {
                $missing[] = $requiredAttribute;
            }
        }

        if (count($missing) === 0) {
            return;
        }

        throw RequestException::invalidRequest($model::class, $action, $missing);
    }

    protected function filterFields(array $array, array $fields = []): array
    {
        return Arr::only($array, $fields);
    }
}
