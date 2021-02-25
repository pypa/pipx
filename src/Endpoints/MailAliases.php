<?php

namespace Vdhicts\Cyberfusion\ClusterApi\Endpoints;

use Vdhicts\Cyberfusion\ClusterApi\Exceptions\RequestException;
use Vdhicts\Cyberfusion\ClusterApi\Models\MailAlias;
use Vdhicts\Cyberfusion\ClusterApi\Request;
use Vdhicts\Cyberfusion\ClusterApi\Response;
use Vdhicts\Cyberfusion\ClusterApi\Support\ListFilter;

class MailAliases extends Endpoint
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
            ->setUrl(sprintf('mail-aliases?%s', http_build_query($filter->toArray())));

        $response = $this
            ->client
            ->request($request);
        if (! $response->isSuccess()) {
            return $response;
        }

        return $response->setData([
            'mailAliases' => array_map(
                function (array $data) {
                    return (new MailAlias())->fromArray($data);
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
            ->setUrl(sprintf('mail-aliases/%d', $id));

        $response = $this
            ->client
            ->request($request);
        if (! $response->isSuccess()) {
            return $response;
        }

        return $response->setData([
            'mailAlias' => (new MailAlias())->fromArray($response->getData()),
        ]);
    }

    /**
     * @param MailAlias $mailAlias
     * @return Response
     * @throws RequestException
     */
    public function create(MailAlias $mailAlias): Response
    {
        $requiredAttributes = [
            'localPart',
            'forwardEmailAddresses',
            'mailDomainId',
        ];
        $this->validateRequired($mailAlias, 'create', $requiredAttributes);

        $request = (new Request())
            ->setMethod(Request::METHOD_POST)
            ->setUrl('mail-aliases')
            ->setBody($this->filterFields($mailAlias->toArray(), [
                'local_part',
                'forward_email_addresses',
                'mail_domain_id',
            ]));

        $response = $this
            ->client
            ->request($request);
        if (! $response->isSuccess()) {
            return $response;
        }

        return $response->setData([
            'mailAlias' => (new MailAlias())->fromArray($response->getData()),
        ]);
    }

    /**
     * @param MailAlias $mailAlias
     * @return Response
     * @throws RequestException
     */
    public function update(MailAlias $mailAlias): Response
    {
        $requiredAttributes = [
            'localPart',
            'forwardEmailAddresses',
            'mailDomainId',
            'id',
            'clusterId'
        ];
        $this->validateRequired($mailAlias, 'update', $requiredAttributes);

        $request = (new Request())
            ->setMethod(Request::METHOD_PUT)
            ->setUrl(sprintf('mail-aliases/%d', $mailAlias->id))
            ->setBody($this->filterFields($mailAlias->toArray(), [
                'local_part',
                'forward_email_addresses',
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
            'mailAlias' => (new MailAlias())->fromArray($response->getData()),
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
            ->setUrl(sprintf('mail-aliases/%d', $id));

        return $this
            ->client
            ->request($request);
    }
}
