<?php

namespace Cyberfusion\ClusterApi\Models;

use Cyberfusion\ClusterApi\Support\Arr;
use Cyberfusion\ClusterApi\Support\Validator;

class IpAddressCreate extends ClusterModel
{
    private ?string $serviceAccountName = null;
    private ?string $dnsName = null;
    private ?string $addressFamily = null;

    public function getServiceAccountName(): ?string
    {
        return $this->serviceAccountName;
    }

    public function setServiceAccountName(?string $serviceAccountName): self
    {
        $this->serviceAccountName = $serviceAccountName;
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

    public function getAddressFamily(): ?string
    {
        return $this->addressFamily;
    }

    public function setAddressFamily(?string $addressFamily): self
    {
        Validator::value($addressFamily)
            ->valuesIn(['IPv4', 'IPv6'])
            ->nullable()
            ->validate();

        $this->addressFamily = $addressFamily;
        return $this;
    }

    public function fromArray(array $data): self
    {
        return $this
            ->setServiceAccountName(Arr::get($data, 'service_account_name'))
            ->setDnsName(Arr::get($data, 'dns_name'))
            ->setAddressFamily(Arr::get($data, 'address_family'));
    }

    public function toArray(): array
    {
        return [
            'service_account_name' => $this->serviceAccountName,
            'dns_name' => $this->dnsName,
            'address_family' => $this->addressFamily,
        ];
    }
}
