<?php

namespace Cyberfusion\ClusterApi\Models;

use Cyberfusion\ClusterApi\Support\Arr;

class BorgArchiveMetadata extends ClusterModel
{
    private string $contentsPath;
    private bool $existsOnServer;
    private int $borgArchiveId;

    public function getContentsPath(): string
    {
        return $this->contentsPath;
    }

    public function setContentsPath(string $contentsPath): self
    {
        $this->contentsPath = $contentsPath;

        return $this;
    }

    public function getExistsOnServer(): bool
    {
        return $this->existsOnServer;
    }

    public function setExistsOnServer(bool $existsOnServer): self
    {
        $this->existsOnServer = $existsOnServer;

        return $this;
    }

    public function getBorgArchiveId(): int
    {
        return $this->borgArchiveId;
    }

    public function setBorgArchiveId(int $borgArchiveId): self
    {
        $this->borgArchiveId = $borgArchiveId;

        return $this;
    }

    public function fromArray(array $data): self
    {
        return $this
            ->setContentsPath(Arr::get($data, 'contents_path'))
            ->setExistsOnServer(Arr::get($data, 'exists_on_server'))
            ->setBorgArchiveId(Arr::get($data, 'borg_archive_id'));
    }

    public function toArray(): array
    {
        return [
            'contents_path' => $this->getContentsPath(),
            'exists_on_server' => $this->getExistsOnServer(),
            'borg_archive_id' => $this->getBorgArchiveId(),
        ];
    }
}
