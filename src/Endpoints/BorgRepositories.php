<?php

namespace Cyberfusion\ClusterApi\Endpoints;

use Cyberfusion\ClusterApi\Exceptions\RequestException;
use Cyberfusion\ClusterApi\Models\BorgArchiveMetadata;
use Cyberfusion\ClusterApi\Models\BorgRepository;
use Cyberfusion\ClusterApi\Models\TaskCollection;
use Cyberfusion\ClusterApi\Request;
use Cyberfusion\ClusterApi\Response;
use Cyberfusion\ClusterApi\Support\ListFilter;
use Cyberfusion\ClusterApi\Support\Str;

class BorgRepositories extends Endpoint
{
    /**
     * @throws RequestException
     */
    public function list(?ListFilter $filter = null): Response
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
        if (!$response->isSuccess()) {
            return $response;
        }

        return $response->setData([
            'borgRepositories' => array_map(
                fn(array $data) => (new BorgRepository())->fromArray($data),
                $response->getData()
            ),
        ]);
    }

    /**
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
        if (!$response->isSuccess()) {
            return $response;
        }

        return $response->setData([
            'borgRepository' => (new BorgRepository())->fromArray($response->getData()),
        ]);
    }

    /**
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
            ->setBody(
                $this->filterFields($borgRepository->toArray(), [
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
                ])
            );

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        $borgRepository = (new BorgRepository())->fromArray($response->getData());

        return $response->setData([
            'borgRepository' => $borgRepository,
        ]);
    }

    /**
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
            ->setBody(
                $this->filterFields($borgRepository->toArray(), [
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
                ])
            );

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        $borgRepository = (new BorgRepository())->fromArray($response->getData());

        return $response->setData([
            'borgRepository' => $borgRepository,
        ]);
    }

    /**
     * @throws RequestException
     */
    public function delete(int $id): Response
    {
        $request = (new Request())
            ->setMethod(Request::METHOD_DELETE)
            ->setUrl(sprintf('borg-repositories/%d', $id));

        return $this
            ->client
            ->request($request);
    }

    /**
     * @throws RequestException
     */
    public function prune(int $id, ?string $callbackUrl = null): Response
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
     * @throws RequestException
     */
    public function check(int $id, ?string $callbackUrl = null): Response
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
                fn(array $data) => (new BorgArchiveMetadata())->fromArray($data),
                $response->getData()
            ),
        ]);
    }
}
