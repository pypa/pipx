<?php

namespace Vdhicts\Cyberfusion\ClusterApi\Endpoints;

use Vdhicts\Cyberfusion\ClusterApi\Exceptions\RequestException;
use Vdhicts\Cyberfusion\ClusterApi\Models\BorgArchive;
use Vdhicts\Cyberfusion\ClusterApi\Request;
use Vdhicts\Cyberfusion\ClusterApi\Response;
use Vdhicts\Cyberfusion\ClusterApi\Support\ListFilter;
use Vdhicts\Cyberfusion\ClusterApi\Support\Str;
use Vdhicts\Cyberfusion\ClusterApi\Models\BorgArchiveDatabaseCreation;
use Vdhicts\Cyberfusion\ClusterApi\Models\BorgArchiveUnixUserCreation;
use Vdhicts\Cyberfusion\ClusterApi\Models\BorgArchiveContent;
use Vdhicts\Cyberfusion\ClusterApi\Models\TaskCollection;

class BorgArchives extends Endpoint
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
            ->setUrl(sprintf('borg-archives?%s', $filter->toQuery()));

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        return $response->setData([
            'borgArchives' => array_map(
                function (array $data) {
                    return (new BorgArchive())->fromArray($data);
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
            ->setUrl(sprintf('borg-archives/%d', $id));

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        return $response->setData([
            'borgArchive' => (new BorgArchive())->fromArray($response->getData()),
        ]);
    }

    /**
     * @param BorgArchiveDatabaseCreation $borgArchiveDatabaseCreation
     * @param string|null $callbackUrl
     * @return Response
     * @throws RequestException
     */
    public function createDatabase(BorgArchiveDatabaseCreation $borgArchiveDatabaseCreation, string $callbackUrl = null): Response
    {
        $this->validateRequired($borgArchiveDatabaseCreation, 'create', [
            'name',
            'borg_repository_id',
            'database_id',
        ]);

        $url = Str::optionalQueryParameters(
            sprintf('borg-archives/database'),
            ['callback_url' => $callbackUrl]
        );

        $request = (new Request())
            ->setMethod(Request::METHOD_POST)
            ->setUrl($url)
            ->setBody($this->filterFields($borgArchiveDatabaseCreation->toArray(), [
                'name',
                'borg_repository_id',
                'database_id',
            ]));

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
     * @param BorgArchiveUnixUserCreation $borgArchiveUnixUserCreation
     * @param string|null $callbackUrl
     * @return Response
     * @throws RequestException
     */
    public function createUnixUser(BorgArchiveUnixUserCreation $borgArchiveUnixUserCreation, string $callbackUrl = null): Response
    {
        $this->validateRequired($borgArchiveUnixUserCreation, 'create', [
            'name',
            'borg_repository_id',
            'unix_user_id',
        ]);

        $url = Str::optionalQueryParameters(
            sprintf('borg-archives/unix-user'),
            ['callback_url' => $callbackUrl]
        );

        $request = (new Request())
            ->setMethod(Request::METHOD_POST)
            ->setUrl($url)
            ->setBody($this->filterFields($borgArchiveUnixUserCreation->toArray(), [
                'name',
                'borg_repository_id',
                'unix_user_id',
            ]));

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
    public function metadata(int $id): Response
    {
        $request = (new Request())
            ->setMethod(Request::METHOD_GET)
            ->setUrl(sprintf('borg-archives/%d/metadata', $id));

        $response = $this
            ->client
            ->request($request);
        if (! $response->isSuccess()) {
            return $response;
        }

        return $response->setData([
            'contents_path' => $response->getData('contents_path'),
            'exists_on_server' => $response->getData('exists_on_server'),
        ]);
    }

    /**
     * @param int $id
     * @param string|null $callbackUrl
     * @return Response
     * @throws RequestException
     */
    public function restore(int $id, string $path = null, string $callbackUrl = null): Response
    {
        $url = Str::optionalQueryParameters(
            sprintf('borg-archives/%d/restore', $id),
            ['path' => $path, 'callback_url' => $callbackUrl]
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
    public function download(int $id, string $path = null, string $callbackUrl = null): Response
    {
        $url = Str::optionalQueryParameters(
            sprintf('borg-archives/%d/download', $id),
            ['path' => $path, 'callback_url' => $callbackUrl]
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
    public function contents(int $id, string $path = null): Response
    {
        $url = Str::optionalQueryParameters(
            sprintf('borg-archives/%d/contents', $id),
            ['path' => $path]
        );

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
            'contents' => array_map(
                function (array $data) {
                    return (new BorgArchiveContent())->fromArray($data);
                },
                $response->getData()
            ),
        ]);
    }
}
