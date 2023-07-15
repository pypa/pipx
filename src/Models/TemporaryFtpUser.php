<?php

namespace Cyberfusion\ClusterApi\Models;

use Cyberfusion\ClusterApi\Support\Arr;

class TemporaryFtpUser extends ClusterModel
{
    private string $username;
    private string $password;
    private string $fileManagerUrl;

    public function getUsername(): string
    {
        return $this->username;
    }

    public function setUsername(string $username): self
    {
        $this->username = $username;

        return $this;
    }

    public function getPassword(): string
    {
        return $this->password;
    }

    public function setPassword(string $password): self
    {
        $this->password = $password;

        return $this;
    }

    public function getFileManagerUrl(): string
    {
        return $this->fileManagerUrl;
    }

    public function setFileManagerUrl(string $fileManagerUrl): self
    {
        $this->fileManagerUrl = $fileManagerUrl;

        return $this;
    }

    public function fromArray(array $data): self
    {
        return $this
            ->setUsername(Arr::get($data, 'username'))
            ->setPassword(Arr::get($data, 'password'))
            ->setFileManagerUrl(Arr::get($data, 'file_manager_url'));
    }

    public function toArray(): array
    {
        return [
            'username' => $this->getUsername(),
            'password' => $this->getPassword(),
            'file_manager_url' => $this->getFileManagerUrl(),
        ];
    }
}
