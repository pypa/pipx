<?php

namespace Vdhicts\Cyberfusion\ClusterApi\Endpoints;

use DateTimeInterface;
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
            ->setUrl(sprintf('mail-accounts?%s', $filter->toQuery()));

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        return $response->setData([
            'mailAccounts' => array_map(
                function (array $data) {
                    return (new MailAccount())->fromArray($data);
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
            ->setUrl(sprintf('mail-accounts/%d', $id));

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        return $response->setData([
            'mailAccount' => (new MailAccount())->fromArray($response->getData()),
        ]);
    }

    /**
     * @param int $id
     * @param DateTimeInterface $from
     * @return Response
     * @throws RequestException
     */
    public function usages(int $id, DateTimeInterface $from): Response
    {
        $url = sprintf('mail-accounts/usages/%d?from_timestamp_date=%s', $id, $from->format('c'));

        $request = (new Request())
            ->setMethod(Request::METHOD_GET)
            ->setUrl($url);

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
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
        $this->validateRequired($mailAccount, 'create', [
            'local_part',
            'password',
            'mail_domain_id',
        ]);

        $request = (new Request())
            ->setMethod(Request::METHOD_POST)
            ->setUrl('mail-accounts')
            ->setBody($this->filterFields($mailAccount->toArray(), [
                'local_part',
                'password',
                'quota',
                'mail_domain_id',
            ]));

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        $mailAccount = (new MailAccount())->fromArray($response->getData());

        // Log which cluster is affected by this change
        $this
            ->client
            ->addAffectedCluster($mailAccount->getClusterId());

        return $response->setData([
            'mailAccount' => $mailAccount,
        ]);
    }

    /**
     * @param MailAccount $mailAccount
     * @return Response
     * @throws RequestException
     */
    public function update(MailAccount $mailAccount): Response
    {
        $this->validateRequired($mailAccount, 'update', [
            'local_part',
            'password',
            'mail_domain_id',
            'id',
            'cluster_id',
        ]);

        $request = (new Request())
            ->setMethod(Request::METHOD_PUT)
            ->setUrl(sprintf('mail-accounts/%d', $mailAccount->getId()))
            ->setBody($this->filterFields($mailAccount->toArray(), [
                'local_part',
                'password',
                'quota',
                'mail_domain_id',
                'id',
                'cluster_id',
            ]));

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        $mailAccount = (new MailAccount())->fromArray($response->getData());

        // Log which cluster is affected by this change
        $this
            ->client
            ->addAffectedCluster($mailAccount->getClusterId());

        return $response->setData([
            'mailAccount' => $mailAccount,
        ]);
    }

    /**
     * @param int $id
     * @return Response
     * @throws RequestException
     */
    public function delete(int $id): Response
    {
        // Log the affected cluster by retrieving the model first
        $result = $this->get($id);
        if ($result->isSuccess()) {
            $clusterId = $result
                ->getData('mailAccount')
                ->getClusterId();

            $this
                ->client
                ->addAffectedCluster($clusterId);
        }

        $request = (new Request())
            ->setMethod(Request::METHOD_DELETE)
            ->setUrl(sprintf('mail-accounts/%d', $id));

        return $this
            ->client
            ->request($request);
    }
}
