<?php

namespace Vdhicts\Cyberfusion\ClusterApi\Endpoints;

use Vdhicts\Cyberfusion\ClusterApi\Exceptions\RequestException;
use Vdhicts\Cyberfusion\ClusterApi\Models\MailAccount;
use Vdhicts\Cyberfusion\ClusterApi\Models\MailAccountUsage;
use Vdhicts\Cyberfusion\ClusterApi\Request;
use Vdhicts\Cyberfusion\ClusterApi\Response;
use Vdhicts\Cyberfusion\ClusterApi\Support\ListFilter;

class MailAccounts extends Endpoint
{
    /**
     * @param ListFilter|null $filter
     * @return Response
     * @throws RequestException
     */
    public function list(ListFilter $filter = null): Response
    {
        if (is_null($filter)) {
            $filter = new ListFilter();
        }

        $request = (new Request())
            ->setMethod(Request::METHOD_GET)
            ->setUrl(sprintf('mail-accounts/?%s', http_build_query($filter->toArray())));

        $response = $this
            ->client
            ->request($request);
        if (! $response->isSuccess()) {
            return $response;
        }

        return $response->setData([
            'mailAccounts' => array_map(
                function (array $data) {
                    return (new MailAccount())->fromArray($data);
                },
                $response->getData()
            )
        ]);
    }

    /**
     * @param int $id
     * @return Response
     * @throws RequestException
     */
    public function get(int $id): Response
    {
        $request = (new Request())
            ->setMethod(Request::METHOD_GET)
            ->setUrl(sprintf('mail-accounts/%d', $id));

        $response = $this
            ->client
            ->request($request);
        if (! $response->isSuccess()) {
            return $response;
        }

        return $response->setData([
            'mailAccount' => (new MailAccount())->fromArray($response->getData()),
        ]);
    }

    /**
     * @param int $id
     * @return Response
     * @throws RequestException
     */
    public function usages(int $id): Response
    {
        $request = (new Request())
            ->setMethod(Request::METHOD_GET)
            ->setUrl(sprintf('mail-accounts/usages/%d', $id));

        $response = $this
            ->client
            ->request($request);
        if (! $response->isSuccess()) {
            return $response;
        }

        return $response->setData([
            'mailAccountUsage' => (new MailAccountUsage())->fromArray($response->getData()),
        ]);
    }

    /**
     * @param MailAccount $mailAccount
     * @return Response
     * @throws RequestException
     */
    public function create(MailAccount $mailAccount): Response
    {
        $requiredAttributes = [
            'localPart',
            'password',
            'forwardEmailAddresses',
            'mailDomainId',
        ];
        $this->validateRequired($mailAccount, 'create', $requiredAttributes);

        $request = (new Request())
            ->setMethod(Request::METHOD_POST)
            ->setUrl('mail-accounts/')
            ->setBody($this->filterFields($mailAccount->toArray(), [
                'local_part',
                'password',
                'forward_email_addresses',
                'quota',
                'mail_domain_id',
            ]));

        $response = $this
            ->client
            ->request($request);
        if (! $response->isSuccess()) {
            return $response;
        }

        return $response->setData([
            'mailAccount' => (new MailAccount())->fromArray($response->getData()),
        ]);
    }

    /**
     * @param MailAccount $mailAccount
     * @return Response
     * @throws RequestException
     */
    public function update(MailAccount $mailAccount): Response
    {
        $requiredAttributes = [
            'localPart',
            'password',
            'forwardEmailAddresses',
            'mailDomainId',
            'id',
            'clusterId'
        ];
        $this->validateRequired($mailAccount, 'update', $requiredAttributes);

        $request = (new Request())
            ->setMethod(Request::METHOD_PUT)
            ->setUrl(sprintf('mail-accounts/%d', $mailAccount->id))
            ->setBody($this->filterFields($mailAccount->toArray(), [
                'local_part',
                'password',
                'forward_email_addresses',
                'quota',
                'mail_domain_id',
                'id',
                'cluster_id',
            ]));

        $response = $this
            ->client
            ->request($request);
        if (! $response->isSuccess()) {
            return $response;
        }

        return $response->setData([
            'mailAccount' => (new MailAccount())->fromArray($response->getData()),
        ]);
    }

    /**
     * @param int $id
     * @return Response
     * @throws RequestException
     */
    public function delete(int $id): Response
    {
        $request = (new Request())
            ->setMethod(Request::METHOD_DELETE)
            ->setUrl(sprintf('mail-accounts/%d', $id));

        return $this
            ->client
            ->request($request);
    }
}
