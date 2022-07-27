<?php

namespace Vdhicts\Cyberfusion\ClusterApi\Endpoints;

use Vdhicts\Cyberfusion\ClusterApi\Exceptions\RequestException;
use Vdhicts\Cyberfusion\ClusterApi\Models\BorgRepository;
use Vdhicts\Cyberfusion\ClusterApi\Models\BorgArchiveMetadata;
use Vdhicts\Cyberfusion\ClusterApi\Models\TaskCollection;
use Vdhicts\Cyberfusion\ClusterApi\Request;
use Vdhicts\Cyberfusion\ClusterApi\Response;
use Vdhicts\Cyberfusion\ClusterApi\Support\ListFilter;
use Vdhicts\Cyberfusion\ClusterApi\Support\Str;

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
            ->setUrl(sprintf('borg-repositories?%s', $filter->toQuery()));

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
     * @param BorgRepository $borgRepository
     * @return Response
     * @throws RequestException
     */
    public function create(BorgRepository $borgRepository): Response
    {
        $this->validateRequired($borgRepository, 'create', [
            'name',
            'passphrase',
            'remote_host',
            'remote_path',
            'remote_username',
            'identity_file_path',
            'unix_user_id',
            'cluster_id',
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
                'remote_host',
                'remote_path',
                'remote_username',
                'identity_file_path',
                'unix_user_id',
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
     * @param BorgRepository $borgRepository
     * @return Response
     * @throws RequestException
     */
    public function update(BorgRepository $borgRepository): Response
    {
        $this->validateRequired($borgRepository, 'update', [
            'name',
            'passphrase',
            'remote_host',
            'remote_path',
            'remote_username',
            'identity_file_path',
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
                'remote_host',
                'remote_path',
                'remote_username',
                'identity_file_path',
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

    /**
     * @param int $id
     * @param string|null $callbackUrl
     * @return Response
     * @throws RequestException
     */
    public function prune(int $id, string $callbackUrl = null): Response
    {
        $url = Str::optionalQueryParameters(
            sprintf('borg-repositories/%d/prune', $id),
            ['callback_url' => $callbackUrl]
        );

        $request = (new Request())
            ->setMethod(Request::METHOD_POST)
            ->setUrl($url);

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        $taskCollection = (new TaskCollection())->fromArray($response->getData());

        return $response->setData([
            'taskCollection' => $taskCollection,
        ]);
    }

    /**
     * @param int $id
     * @param string|null $callbackUrl
     * @return Response
     * @throws RequestException
     */
    public function check(int $id, string $callbackUrl = null): Response
    {
        $url = Str::optionalQueryParameters(
            sprintf('borg-repositories/%d/check', $id),
            ['callback_url' => $callbackUrl]
        );

        $request = (new Request())
            ->setMethod(Request::METHOD_POST)
            ->setUrl($url);

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        $taskCollection = (new TaskCollection())->fromArray($response->getData());

        return $response->setData([
            'taskCollection' => $taskCollection,
        ]);
    }

    /**
     * @param int $id
     * @return Response
     * @throws RequestException
     */
    public function archivesMetadata(int $id): Response
    {
        $request = (new Request())
            ->setMethod(Request::METHOD_GET)
            ->setUrl(sprintf('borg-repositories/%d/archives-metadata', $id));

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        return $response->setData([
            'metadata' => array_map(
                function (array $data) {
                    return (new BorgArchiveMetadata())->fromArray($data);
                },
                $response->getData()
            ),
        ]);
    }
}
