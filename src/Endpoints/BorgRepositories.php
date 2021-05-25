<?php

namespace Vdhicts\Cyberfusion\ClusterApi\Endpoints;

use DateTimeInterface;
use Vdhicts\Cyberfusion\ClusterApi\Exceptions\RequestException;
use Vdhicts\Cyberfusion\ClusterApi\Models\BorgRepository;
use Vdhicts\Cyberfusion\ClusterApi\Models\BorgRepositoryUsage;
use Vdhicts\Cyberfusion\ClusterApi\Request;
use Vdhicts\Cyberfusion\ClusterApi\Response;
use Vdhicts\Cyberfusion\ClusterApi\Support\ListFilter;

class BorgRepositories extends Endpoint
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
            ->setUrl(sprintf('borg-repositories?%s', http_build_query($filter->toArray())));

        $response = $this
            ->client
            ->request($request);
        if (! $response->isSuccess()) {
            return $response;
        }

        return $response->setData([
            'borgRepositories' => array_map(
                function (array $data) {
                    return (new BorgRepository())->fromArray($data);
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
            ->setUrl(sprintf('borg-repositories/%d', $id));

        $response = $this
            ->client
            ->request($request);
        if (! $response->isSuccess()) {
            return $response;
        }

        return $response->setData([
            'borgRepository' => (new BorgRepository())->fromArray($response->getData()),
        ]);
    }

    /**
     * @param int $id
     * @param DateTimeInterface|null $from
     * @return Response
     * @throws RequestException
     */
    public function usages(int $id, DateTimeInterface $from = null): Response
    {
        $url = $this->applyOptionalQueryParameters(
            sprintf('borg-repositories/usages/%d', $id),
            ['from_timestamp_date' => $from]
        );

        $request = (new Request())
            ->setMethod(Request::METHOD_GET)
            ->setUrl($url);

        $response = $this
            ->client
            ->request($request);
        if (! $response->isSuccess()) {
            return $response;
        }

        return $response->setData([
            'borgRepositoryUsage' => count($response->getData()) !== 0
                ? array_map(
                    function (array $data) {
                        return (new BorgRepositoryUsage())->fromArray($data);
                    },
                    $response->getData()
                )
                : null,
        ]);
    }

    /**
     * @param BorgRepository $borgRepository
     * @return Response
     * @throws RequestException
     */
    public function create(BorgRepository $borgRepository): Response
    {
        $this->validateRequired($borgRepository, 'create', [
            'name',
            'passphrase',
            'remote_url',
            'ssh_key_id',
            'unix_user_id',
        ]);

        $request = (new Request())
            ->setMethod(Request::METHOD_POST)
            ->setUrl('borg-repositories')
            ->setBody($this->filterFields($borgRepository->toArray(), [
                'name',
                'passphrase',
                'keep_hourly',
                'keep_daily',
                'keep_weekly',
                'keep_monthly',
                'keep_yearly',
                'remote_url',
                'ssh_key_id',
                'unix_user_id',
            ]));

        $response = $this
            ->client
            ->request($request);
        if (! $response->isSuccess()) {
            return $response;
        }

        $borgRepository = (new BorgRepository())->fromArray($response->getData());

        // Log which cluster is affected by this change
        $this
            ->client
            ->addAffectedCluster($borgRepository->getClusterId());

        return $response->setData([
            'borgRepository' => $borgRepository,
        ]);
    }

    /**
     * @param BorgRepository $borgRepository
     * @return Response
     * @throws RequestException
     */
    public function update(BorgRepository $borgRepository): Response
    {
        $this->validateRequired($borgRepository, 'update', [
            'name',
            'passphrase',
            'remote_url',
            'ssh_key_id',
            'unix_user_id',
            'id',
            'cluster_id',
        ]);

        $request = (new Request())
            ->setMethod(Request::METHOD_PUT)
            ->setUrl(sprintf('borg-repositories/%d', $borgRepository->getId()))
            ->setBody($this->filterFields($borgRepository->toArray(), [
                'name',
                'passphrase',
                'keep_hourly',
                'keep_daily',
                'keep_weekly',
                'keep_monthly',
                'keep_yearly',
                'remote_url',
                'ssh_key_id',
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

        $borgRepository = (new BorgRepository())->fromArray($response->getData());

        // Log which cluster is affected by this change
        $this
            ->client
            ->addAffectedCluster($borgRepository->getClusterId());

        return $response->setData([
            'borgRepository' => $borgRepository,
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
                ->getData('borgRepository')
                ->getClusterId();

            $this
                ->client
                ->addAffectedCluster($clusterId);
        }

        $request = (new Request())
            ->setMethod(Request::METHOD_DELETE)
            ->setUrl(sprintf('borg-repositories/%d', $id));

        return $this
            ->client
            ->request($request);
    }
}
