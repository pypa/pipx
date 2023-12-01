<?php

namespace Cyberfusion\ClusterApi\Models;

use Cyberfusion\ClusterApi\Support\Arr;
use Cyberfusion\ClusterApi\Support\Validator;

class IpAddress extends ClusterModel
{
    private string $ipAddress;
    private ?string $dnsName = null;

    public function getIpAddress(): string
    {
        return $this->ipAddress;
    }

    public function setIpAddress(string $ipAddress): self
    {
        Validator::value($ipAddress)
            ->ip()
            ->validate();

        $this->ipAddress = $ipAddress;

        return $this;
    }

    public function getDnsName(): ?string
    {
        return $this->dnsName;
    }

    public function setDnsName(?string $dnsName): self
    {
        $this->dnsName = $dnsName;

        return $this;
    }

    public function fromArray(array $data): self
    {
        return $this
            ->setIpAddress(Arr::get($data, 'ip_address'))
            ->setDnsName(Arr::get($data, 'dns_name'));
    }

    public function toArray(): array
    {
        return [
            'ip_address' => $this->getIpAddress(),
            'dns_name' => $this->getDnsName()
        ];
    }
}
