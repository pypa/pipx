<?php

namespace Cyberfusion\ClusterApi\Models;

use Cyberfusion\ClusterApi\Support\Arr;

class DatabaseComparison extends ClusterModel
{
    private array $identicalTablesNames = [];
    private array $notIdenticalTablesNames = [];
    private array $onlyLeftTablesNames = [];
    private array $onlyRightTablesNames = [];

    /**
     * These tables exist in the left and right databases, and their structure and contents are identical.
     */
    public function getIdenticalTablesNames(): array
    {
        return $this->identicalTablesNames;
    }

    public function setIdenticalTablesNames(array $identicalTablesNames): self
    {
        $this->identicalTablesNames = $identicalTablesNames;

        return $this;
    }

    /**
     * These tables exist in the left and right databases, but their structure and/or contents are not identical.
     */
    public function getNotIdenticalTablesNames(): array
    {
        return $this->notIdenticalTablesNames;
    }

    public function setNotIdenticalTablesNames(array $notIdenticalTablesNames): self
    {
        $this->notIdenticalTablesNames = $notIdenticalTablesNames;

        return $this;
    }

    /**
     * These tables only exist in the left database.
     */
    public function getOnlyLeftTablesNames(): array
    {
        return $this->onlyLeftTablesNames;
    }

    public function setOnlyLeftTablesNames(array $onlyLeftTablesNames): self
    {
        $this->onlyLeftTablesNames = $onlyLeftTablesNames;

        return $this;
    }

    /**
     * These tables only exist in the right database.
     */
    public function getOnlyRightTablesNames(): array
    {
        return $this->onlyRightTablesNames;
    }

    public function setOnlyRightTablesNames(array $onlyRightTablesNames): self
    {
        $this->onlyRightTablesNames = $onlyRightTablesNames;

        return $this;
    }

    public function fromArray(array $data): self
    {
        return $this
            ->setIdenticalTablesNames(Arr::get($data, 'identical_tables_names', []))
            ->setNotIdenticalTablesNames(Arr::get($data, 'not_identical_tables_names', []))
            ->setOnlyLeftTablesNames(Arr::get($data, 'only_left_tables_names', []))
            ->setOnlyRightTablesNames(Arr::get($data, 'only_right_tables_names', []));
    }

    public function toArray(): array
    {
        return [
            'identical_tables_names' => $this->getIdenticalTablesNames(),
            'not_identical_tables_names' => $this->getNotIdenticalTablesNames(),
            'only_left_tables_names' => $this->getOnlyLeftTablesNames(),
            'only_right_tables_names' => $this->getOnlyRightTablesNames(),
        ];
    }
}
