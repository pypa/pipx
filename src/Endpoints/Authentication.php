<?php

namespace Cyberfusion\ClusterApi\Endpoints;

use Cyberfusion\ClusterApi\Exceptions\RequestException;
use Cyberfusion\ClusterApi\Models\Login;
use Cyberfusion\ClusterApi\Models\Token;
use Cyberfusion\ClusterApi\Models\UserInfo;
use Cyberfusion\ClusterApi\Request;
use Cyberfusion\ClusterApi\Response;

class Authentication extends Endpoint
{
    /**
     * @param Login $login
     * @return Response
     * @throws RequestException
     */
    public function login(Login $login): Response
    {
        $request = (new Request())
            ->setMethod(Request::METHOD_POST)
            ->setUrl('login/access-token')
            ->setBody($login->toArray())
            ->setAuthenticationRequired(false)
            ->setBodySchema(Request::BODY_SCHEMA_FORM);

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        return $response->setData([
            'token' => (new Token())->fromArray($response->getData()),
        ]);
    }

    /**
     * @return Response
     * @throws RequestException
     */
    public function verify(): Response
    {
        $request = (new Request())
            ->setMethod(Request::METHOD_POST)
            ->setUrl('login/test-token');

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        return $response->setData([
            'userInfo' => (new UserInfo())->fromArray($response->getData()),
        ]);
    }
}
