<?php

namespace Vdhicts\Cyberfusion\ClusterApi\Endpoints;

use Vdhicts\Cyberfusion\ClusterApi\Exceptions\RequestException;
use Vdhicts\Cyberfusion\ClusterApi\Models\MailDomain;
use Vdhicts\Cyberfusion\ClusterApi\Request;
use Vdhicts\Cyberfusion\ClusterApi\Response;
use Vdhicts\Cyberfusion\ClusterApi\Support\ListFilter;

class MailDomains extends Endpoint
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
            ->setUrl(sprintf('mail-domains?%s', http_build_query($filter->toArray())));

        $response = $this
            ->client
            ->request($request);
        if (! $response->isSuccess()) {
            return $response;
        }

        return $response->setData([
            'mailDomains' => array_map(
                function (array $data) {
                    return (new MailDomain())->fromArray($data);
                },
                $response->getData()
            ),
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
            ->setUrl(sprintf('mail-domains/%d', $id));

        $response = $this
            ->client
            ->request($request);
        if (! $response->isSuccess()) {
            return $response;
        }

        return $response->setData([
            'mailDomain' => (new MailDomain())->fromArray($response->getData()),
        ]);
    }

    /**
     * @param MailDomain $mailDomain
     * @return Response
     * @throws RequestException
     */
    public function create(MailDomain $mailDomain): Response
    {
        $requiredAttributes = [
            'domain',
            'catchAllForwardEmailAddresses',
            'isLocal',
            'unixUserId',
        ];
        $this->validateRequired($mailDomain, 'create', $requiredAttributes);

        $request = (new Request())
            ->setMethod(Request::METHOD_POST)
            ->setUrl('mail-domains')
            ->setBody($this->filterFields($mailDomain->toArray(), [
                'domain',
                'catch_all_forward_email_addresses',
                'is_local',
                'unix_user_id',
            ]));

        $response = $this
            ->client
            ->request($request);
        if (! $response->isSuccess()) {
            return $response;
        }

        return $response->setData([
            'mailDomain' => (new MailDomain())->fromArray($response->getData()),
        ]);
    }

    /**
     * @param MailDomain $mailDomain
     * @return Response
     * @throws RequestException
     */
    public function update(MailDomain $mailDomain): Response
    {
        $requiredAttributes = [
            'domain',
            'catchAllForwardEmailAddresses',
            'unixUserId',
            'id',
            'clusterId'
        ];
        $this->validateRequired($mailDomain, 'update', $requiredAttributes);

        $request = (new Request())
            ->setMethod(Request::METHOD_PUT)
            ->setUrl(sprintf('mail-domains/%d', $mailDomain->id))
            ->setBody($this->filterFields($mailDomain->toArray(), [
                'domain',
                'catch_all_forward_email_addresses',
                'is_local',
                'unix_user_id',
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
            'mailDomain' => (new MailDomain())->fromArray($response->getData()),
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
            ->setUrl(sprintf('mail-domains/%d', $id));

        return $this
            ->client
            ->request($request);
    }
}
