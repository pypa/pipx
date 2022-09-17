<?php

namespace Cyberfusion\ClusterApi\Models;

use Cyberfusion\ClusterApi\Contracts\Model;
use Cyberfusion\ClusterApi\Support\Arr;

class UnixUserComparison extends ClusterModel implements Model
{
    private array $notIdenticalPaths = [];
    private array $onlyLeftFilesPaths = [];
    private array $onlyRightFilesPaths = [];
    private array $onlyLeftDirectoriesPaths = [];
    private array $onlyRightDirectoriesPaths = [];

    /**
     * These files or directories exist in the left and right UNIX users, and their attributes are identical.
     */
    public function getNotIdenticalPaths(): array
    {
        return $this->notIdenticalPaths;
    }

    public function setNotIdenticalPaths(array $notIdenticalPaths): UnixUserComparison
    {
        $this->notIdenticalPaths = $notIdenticalPaths;

        return $this;
    }

    /**
     * These files only exist in the left UNIX user.
     */
    public function getOnlyLeftFilesPaths(): array
    {
        return $this->onlyLeftFilesPaths;
    }

    public function setOnlyLeftFilesPaths(array $onlyLeftFilesPaths): UnixUserComparison
    {
        $this->onlyLeftFilesPaths = $onlyLeftFilesPaths;

        return $this;
    }

    /**
     * These files only exist in the right UNIX user.
     */
    public function getOnlyRightFilesPaths(): array
    {
        return $this->onlyRightFilesPaths;
    }

    public function setOnlyRightFilesPaths(array $onlyRightFilesPaths): UnixUserComparison
    {
        $this->onlyRightFilesPaths = $onlyRightFilesPaths;

        return $this;
    }

    /**
     * These directories only exist in the left UNIX user.
     */
    public function getOnlyLeftDirectoriesPaths(): array
    {
        return $this->onlyLeftDirectoriesPaths;
    }

    public function setOnlyLeftDirectoriesPaths(array $onlyLeftDirectoriesPaths): UnixUserComparison
    {
        $this->onlyLeftDirectoriesPaths = $onlyLeftDirectoriesPaths;

        return $this;
    }

    /**
     * These directories only exist in the right UNIX user.
     */
    public function getOnlyRightDirectoriesPaths(): array
    {
        return $this->onlyRightDirectoriesPaths;
    }

    public function setOnlyRightDirectoriesPaths(array $onlyRightDirectoriesPaths): UnixUserComparison
    {
        $this->onlyRightDirectoriesPaths = $onlyRightDirectoriesPaths;

        return $this;
    }

    public function fromArray(array $data): UnixUserComparison
    {
        return $this
            ->setNotIdenticalPaths(Arr::get($data, 'not_identical_paths', []))
            ->setOnlyLeftFilesPaths(Arr::get($data, 'only_left_files_paths', []))
            ->setOnlyRightFilesPaths(Arr::get($data, 'only_right_files_paths', []))
            ->setOnlyLeftDirectoriesPaths(Arr::get($data, 'only_left_directories_paths', []))
            ->setOnlyRightDirectoriesPaths(Arr::get($data, 'only_right_directories_paths', []));
    }

    public function toArray(): array
    {
        return [
            'not_identical_paths' => $this->getNotIdenticalPaths(),
            'only_left_files_paths' => $this->getOnlyLeftFilesPaths(),
            'only_right_files_paths' => $this->getOnlyRightFilesPaths(),
            'only_left_directories_paths' => $this->getOnlyLeftDirectoriesPaths(),
            'only_right_directories_paths' => $this->getOnlyRightDirectoriesPaths(),
        ];
    }
}
