import requests


class MegaplanAuth:
    __slots__ = [
        'login', 'password', 'host',
        '__proto', 'accessid', 'secretkey', 'domain'
    ]

    def __init__(self, host: str, proto='http://'):
        self.host, self.__proto = host, proto
        self.domain = f"{self.__proto}{self.host}"


    def get_token(self, login: str, password: str):
        # encrupy_password = self.__password_crypt(password)
        response = requests.post(
            url=f'{self.domain}/api/v3/auth/access_token',
            headers={'content-type': 'application/x-www-form-urlencoded'},
            data={'username': login, 'password': password, 'grant_type': 'password'}, )
        resp_json = response.json()
        _AccessToken = resp_json["access_token"]
        # _SecretKey = resp_json["data"]["SecretKey"]
        return _AccessToken


class MegaplanApi:
    __slots__ = [
        '_today', 'AccessId', 'SecretKey', 'Token',
        'host', '__proto', 'domain', '_today'
    ]

    def __init__(self, host: str, AccessId="", SecretKey="", proto='http://', Token=""):
        self.host, self.__proto = host, proto
        self.domain = f"{self.__proto}{self.host}"
        self.AccessId, self.SecretKey = AccessId, SecretKey.encode()
        self.Token = Token



    def get_query_v3(self, uri_query: str, payload=None):
        # if payload:
        # payload_str = urlencode(payload, doseq=True)
        # print(f"payload_str = {payload}")
        response = requests.get(
            url=f"{self.domain}{uri_query}",
            headers={"AUTHORIZATION": f"Bearer {self.Token}", "Content-type": "application/json"},
            # params=urlencode(payload, doseq=True) if payload else None, timeout=60)
            params=payload if payload else None, timeout=60)
        # params=kwargs['params'] if 'params' in kwargs.keys() else {},)
        # print(response.url)
        resp_json = response.json()
        status = resp_json.get("status")
        if status and status.get("code") == "error":
            raise ValueError(status["message"])
        return resp_json.get("data")

    def get_task_v3(self, taskid: str, payload=None):
        self.get_query_v3(f"/api/v3/task/{taskid}", payload)

    # def post_query(self, uri_query: str, payload: dict):
    #     head = self.query_hasher('POST', uri_query, None)
    #     response = requests.post(
    #         url=f"{self.domain}{uri_query}",
    #         headers=head,
    #         data=payload)
    #     return response.json()

    def __repr__(self):
        return f"<API [{self.domain}]>"
