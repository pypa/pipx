<?php

namespace Cyberfusion\ClusterApi\Models;

use Cyberfusion\ClusterApi\Support\Arr;
use Cyberfusion\ClusterApi\Support\Validator;

class ClusterCommonProperties extends ClusterModel
{
    private string $imapHostname;
    private int $imapPort;
    private string $imapEncryption;
    private string $smtpHostname;
    private int $smtpPort;
    private string $smtpEncryption;
    private string $pop3Hostname;
    private int $pop3Port;
    private string $pop3Encryption;
    private string $phpmyadminUrl;

    public function getImapHostname(): string
    {
        return $this->imapHostname;
    }

    public function setImapHostname(string $imapHostname): self
    {
        $this->imapHostname = $imapHostname;
        return $this;
    }

    public function getImapPort(): int
    {
        return $this->imapPort;
    }

    public function setImapPort(int $imapPort): self
    {
        Validator::value($imapPort)
            ->minAmount(0)
            ->maxAmount(65535)
            ->validate();

        $this->imapPort = $imapPort;
        return $this;
    }

    public function getImapEncryption(): string
    {
        return $this->imapEncryption;
    }

    public function setImapEncryption(string $imapEncryption): self
    {
        $this->imapEncryption = $imapEncryption;
        return $this;
    }

    public function getSmtpHostname(): string
    {
        return $this->smtpHostname;
    }

    public function setSmtpHostname(string $smtpHostname): self
    {
        $this->smtpHostname = $smtpHostname;
        return $this;
    }

    public function getSmtpPort(): int
    {
        return $this->smtpPort;
    }

    public function setSmtpPort(int $smtpPort): self
    {
        Validator::value($smtpPort)
            ->minAmount(0)
            ->maxAmount(65535)
            ->validate();

        $this->smtpPort = $smtpPort;
        return $this;
    }

    public function getSmtpEncryption(): string
    {
        return $this->smtpEncryption;
    }

    public function setSmtpEncryption(string $smtpEncryption): self
    {
        $this->smtpEncryption = $smtpEncryption;
        return $this;
    }

    public function getPop3Hostname(): string
    {
        return $this->pop3Hostname;
    }

    public function setPop3Hostname(string $pop3Hostname): self
    {
        $this->pop3Hostname = $pop3Hostname;
        return $this;
    }

    public function getPop3Port(): int
    {
        return $this->pop3Port;
    }

    public function setPop3Port(int $pop3Port): self
    {
        Validator::value($pop3Port)
            ->minAmount(0)
            ->maxAmount(65535)
            ->validate();

        $this->pop3Port = $pop3Port;
        return $this;
    }

    public function getPop3Encryption(): string
    {
        return $this->pop3Encryption;
    }

    public function setPop3Encryption(string $pop3Encryption): self
    {
        $this->pop3Encryption = $pop3Encryption;
        return $this;
    }

    public function getPhpmyadminUrl(): string
    {
        return $this->phpmyadminUrl;
    }

    public function setPhpmyadminUrl(string $phpmyadminUrl): self
    {
        $this->phpmyadminUrl = $phpmyadminUrl;
        return $this;
    }

    public function fromArray(array $data): self
    {
        return $this
            ->setImapHostname(Arr::get($data, 'imap_hostname'))
            ->setImapPort(Arr::get($data, 'imap_port'))
            ->setImapEncryption(Arr::get($data, 'imap_encryption'))
            ->setSmtpHostname(Arr::get($data, 'smtp_hostname'))
            ->setSmtpPort(Arr::get($data, 'smtp_port'))
            ->setSmtpEncryption(Arr::get($data, 'smtp_encryption'))
            ->setPop3Hostname(Arr::get($data, 'pop3_hostname'))
            ->setPop3Port(Arr::get($data, 'pop3_port'))
            ->setPop3Encryption(Arr::get($data, 'pop3_encryption'))
            ->setPhpmyadminUrl(Arr::get($data, 'phpmyadmin_url'));
    }

    public function toArray(): array
    {
        return [
            'imap_hostname' => $this->imapHostname,
            'imap_port' => $this->imapPort,
            'imap_encryption' => $this->imapEncryption,
            'smtp_hostname' => $this->smtpHostname,
            'smtp_port' => $this->smtpPort,
            'smtp_encryption' => $this->smtpEncryption,
            'pop3_hostname' => $this->pop3Hostname,
            'pop3_port' => $this->pop3Port,
            'pop3_encryption' => $this->pop3Encryption,
            'phpmyadmin_url' => $this->phpmyadminUrl,
        ];
    }
}
