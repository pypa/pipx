<?php

namespace Cyberfusion\ClusterApi\Endpoints;

use Cyberfusion\ClusterApi\Exceptions\RequestException;
use Cyberfusion\ClusterApi\Models\Cms;
use Cyberfusion\ClusterApi\Models\CmsConfigurationConstant;
use Cyberfusion\ClusterApi\Models\CmsInstallation;
use Cyberfusion\ClusterApi\Models\CmsOption;
use Cyberfusion\ClusterApi\Models\CmsUserCredentials;
use Cyberfusion\ClusterApi\Models\TaskCollection;
use Cyberfusion\ClusterApi\Request;
use Cyberfusion\ClusterApi\Response;
use Cyberfusion\ClusterApi\Support\ListFilter;
use Cyberfusion\ClusterApi\Support\Str;

class Cmses extends Endpoint
{
    /**
     * @throws RequestException
     */
    public function list(?ListFilter $filter = null): Response
    {
        if (!$filter instanceof ListFilter) {
            $filter = new ListFilter();
        }

        $request = (new Request())
            ->setMethod(Request::METHOD_GET)
            ->setUrl(sprintf('cmses?%s', $filter->toQuery()));

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        return $response->setData([
            'cmses' => array_map(
                fn (array $data) => (new Cms())->fromArray($data),
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
            ->setUrl(sprintf('cmses/%d', $id));

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        return $response->setData([
            'cms' => (new Cms())->fromArray($response->getData()),
        ]);
    }

    /**
     * @throws RequestException
     */
    public function create(Cms $cms): Response
    {
        $this->validateRequired($cms, 'create', [
            'software_name',
            'virtual_host_id',
        ]);

        $request = (new Request())
            ->setMethod(Request::METHOD_POST)
            ->setUrl('cmses')
            ->setBody(
                $this->filterFields($cms->toArray(), [
                    'software_name',
                    'is_manually_created',
                    'virtual_host_id',
                ])
            );

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        $cms = (new Cms())->fromArray($response->getData());

        return $response->setData([
            'cms' => $cms,
        ]);
    }

    /**
     * @throws RequestException
     */
    public function delete(int $id): Response
    {
        $request = (new Request())
            ->setMethod(Request::METHOD_DELETE)
            ->setUrl(sprintf('cmses/%d', $id));

        return $this
            ->client
            ->request($request);
    }

    public function installNextcloud(int $id, CmsInstallation $cmsInstallation, ?string $callbackUrl = null): Response
    {
        $this->validateRequired($cmsInstallation, 'create', [
            'database_name',
            'database_user_name',
            'database_user_password',
            'database_host',
            'admin_username',
            'admin_password',
        ]);

        $url = Str::optionalQueryParameters(
            sprintf('cmses/%d/install/nextcloud', $id),
            ['callback_url' => $callbackUrl]
        );

        $request = (new Request())
            ->setMethod(Request::METHOD_POST)
            ->setUrl($url)
            ->setBody(
                $this->filterFields($cmsInstallation->toArray(), [
                    'database_name',
                    'database_user_name',
                    'database_user_password',
                    'database_host',
                    'admin_username',
                    'admin_password',
                ])
            );

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
    public function installWordpress(int $id, CmsInstallation $cmsInstallation, ?string $callbackUrl = null): Response
    {
        $this->validateRequired($cmsInstallation, 'create', [
            'database_name',
            'database_user_name',
            'database_user_password',
            'database_host',
            'site_title',
            'site_url',
            'locale',
            'version',
            'admin_username',
            'admin_password',
            'admin_email_address',
        ]);

        $url = Str::optionalQueryParameters(
            sprintf('cmses/%d/install/wordpress', $id),
            ['callback_url' => $callbackUrl]
        );

        $request = (new Request())
            ->setMethod(Request::METHOD_POST)
            ->setUrl($url)
            ->setBody(
                $this->filterFields($cmsInstallation->toArray(), [
                    'database_name',
                    'database_user_name',
                    'database_user_password',
                    'database_host',
                    'site_title',
                    'site_url',
                    'locale',
                    'version',
                    'admin_username',
                    'admin_password',
                    'admin_email_address',
                ])
            );

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
    public function oneTimeLogin(int $id): Response
    {
        $request = (new Request())
            ->setMethod(Request::METHOD_GET)
            ->setUrl(sprintf('cmses/%d/one-time-login', $id));

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        return $response->setData([
            'url' => $response->getData('url'),
        ]);
    }

    /**
     * @throws RequestException
     */
    public function updateOption(int $id, CmsOption $cmsOption): Response
    {
        $this->validateRequired($cmsOption, 'update', [
            'name',
            'value',
        ]);

        $request = (new Request())
            ->setMethod(Request::METHOD_PUT)
            ->setUrl(sprintf('cmses/%d/options/%d', $id, $cmsOption->getName()))
            ->setBody(
                $this->filterFields($cmsOption->toArray(), [
                    'name',
                    'value',
                ])
            );

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        $cmsOption = (new CmsOption())->fromArray($response->getData());

        return $response->setData([
            'cmsOption' => $cmsOption,
        ]);
    }

    /**
     * @throws RequestException
     */
    public function updateConfigurationConstant(int $id, CmsConfigurationConstant $cmsConfigurationConstant): Response
    {
        $this->validateRequired($cmsConfigurationConstant, 'update', [
            'name',
            'value',
        ]);

        $request = (new Request())
            ->setMethod(Request::METHOD_PUT)
            ->setUrl(sprintf('cmses/%d/configuration-constants/%d', $id, $cmsConfigurationConstant->getName()))
            ->setBody(
                $this->filterFields($cmsConfigurationConstant->toArray(), [
                    'name',
                    'value',
                ])
            );

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        $cmsConfigurationConstant = (new CmsConfigurationConstant())->fromArray($response->getData());

        return $response->setData([
            'cmsConfigurationConstant' => $cmsConfigurationConstant,
        ]);
    }

    /**
     * @throws RequestException
     */
    public function searchReplace(
        int $id,
        string $searchString,
        string $replaceString,
        ?string $callbackUrl = null
    ): Response {
        $url = Str::optionalQueryParameters(
            sprintf(
                'cmses/%d/search-replace?search_string=%d&replace_string=%d',
                $id,
                $searchString,
                $replaceString
            ),
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
    public function regenerateSalts(int $id): ?Response
    {
        $request = (new Request())
            ->setMethod(Request::METHOD_POST)
            ->setUrl(sprintf('cmses/%d/regenerate-salts', $id));

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        return null;
    }

    /**
     * @throws RequestException
     */
    public function installThemeFromRepository(int $id, string $name, ?string $version = null): ?Response
    {
        $request = (new Request())
            ->setMethod(Request::METHOD_POST)
            ->setUrl(sprintf('cmses/%d/themes', $id))
            ->setBody([
                'name' => $name,
                'version' => $version,
            ]);

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        return null;
    }

    /**
     * @throws RequestException
     */
    public function installThemeFromUrl(int $id, string $url): ?Response
    {
        $request = (new Request())
            ->setMethod(Request::METHOD_POST)
            ->setUrl(sprintf('cmses/%d/themes', $id))
            ->setBody([
                'url' => $url,
            ]);

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        return null;
    }

    /**
     * @throws RequestException
     */
    public function updateUserCredentials(int $id, int $userId, CmsUserCredentials $cmsUserCredentials): ?Response
    {
        $this->validateRequired($cmsUserCredentials, 'update', [
            'password',
        ]);

        $request = (new Request())
            ->setMethod(Request::METHOD_PATCH)
            ->setUrl(sprintf('cmses/%d/users/%d/credentials', $id, $userId))
            ->setBody(
                $this->filterFields($cmsUserCredentials->toArray(), [
                    'password',
                ])
            );

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        return null;
    }
}
