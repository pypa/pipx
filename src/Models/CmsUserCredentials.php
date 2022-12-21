<?php

namespace Cyberfusion\ClusterApi\Models;

use Cyberfusion\ClusterApi\Contracts\Model;
use Cyberfusion\ClusterApi\Support\Arr;
use Cyberfusion\ClusterApi\Support\Validator;

class CmsUserCredentials extends ClusterModel implements Model
{
    private string $password;

    public function getPassword(): string
    {
        return $this->password;
    }

    public function setPassword(string $password): self
    {
        Validator::value($password)
            ->minLength(24)
            ->maxLength(255)
            ->pattern('^[ -~]+$')
            ->validate();

        $this->password = $password;

        return $this;
    }

    public function fromArray(array $data): self
    {
        return $this
            ->setPassword(Arr::get($data, 'password'));
    }

    public function toArray(): array
    {
        return [
            'password' => $this->getPassword(),
        ];
    }
}
