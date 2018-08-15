import requests
import json
import urllib


class DataHolder:
    def __init__(self, api):
        self.api = api
        self.request = self.api.current_request
        self.page_no = 1
        self.pk = None

    @staticmethod
    def _parse_response(response):
        resp = json.loads(response)
        if 'error' in resp.keys():
            raise Exception(resp['error'])
        return resp

    def _build_request_params(self):
        url = self.api.domain + self.api.endpoint
        # get the pk if there is one
        if self.pk is not None:
            url += self.pk
        # get the page number
        if self.page_no > 1:
            self.api.params['page'] = self.page_no
        else:
            if self.api.params is not None:
                self.api.params.pop('page', None)
                # change lists to comma delimited strings
                for k, v in self.api.params.items():
                    if isinstance(v, list):
                        self.api.params[k] = ','.join(v)

        # get the get params
        if self.api.params:
            url += '?' + urllib.urlencode(self.api.params)
        return {'method': self.api.method, 'url': url, 'headers': self.api.headers}

    def _get_response(self, params):
        return self._parse_response(requests.request(**params).text)

    def all(self):
        """
        :return: all of the data (all pages)
        """
        result = []
        for p in self.iterall():
            if self.api.response_data_name is not None:
                result.append(p[self.api.response_data_name])
            else:
                result.append(p)
        if self.api.response_data_name is None:
            if len(result) == 1:
                return result[0]
            return result
        return {self.api.response_data_name: result}

    def iterall(self):
        """
        Generator function for all the pages
        :return: iterator for result pages
        """
        # reset page number
        self.page_no = 1
        last_page = False
        while not last_page:
            resp = self._get_response(self._build_request_params())
            if 'no_pages' in resp.keys():
                pages = resp['no_pages']
                if self.page_no == pages:
                    last_page = True
                    self.page_no = 1
                self.page_no += 1
            else:
                last_page = True
            yield resp

    def page(self, number):
        self.page_no = 1
        self.page_no = number
        return self._get_response(self._build_request_params())

    def find(self, pk):
        self.page_no = 1
        self.pk = pk
        return self


class BlackCurveAPI:
    """
    This is the holder for the subdomain and access_token for accessing the API
    """

    def __init__(self, subdomain, access_token=None):
        self.domain = 'https://%s.pricingsuccess.uk/api/' % subdomain
        self.access_token = access_token
        self.current_request = None
        self.data_attributes = ['all','iterall', 'page', 'find']
        self.response_data_name = 'data'
        self.endpoint = None
        self.params = {}
        self.method = None

    def __getattr__(self, name):
        dh = DataHolder(self)
        if name in self.data_attributes:
            return getattr(dh, name)
        else:
            raise Exception('method \'%s\' not allowed' % name)

    def _get_request(self, endpoint, method, params=None):
        self.endpoint = endpoint
        self.params = params
        self.method = method
        self.headers = {
            'Authorization': "Bearer %s" % self.access_token,
        }

    def get_access_token(self, client_key, client_secret):
        """
        Obtains a new access token, this will change your token for the API credentials
        The token is set on this object as access_token
        :param client_key: Your client key
        :param client_secret: Your client secret
        """
        url = self.domain + 'token'
        payload = "CLIENT_KEY=%s&CLIENT_SECRET=%s" % (client_key, client_secret)
        headers = {
            'Content-Type': "application/x-www-form-urlencoded",
        }

        response = requests.request("POST", url, data=payload, headers=headers)
        response = json.loads(response.text)
        if 'token' in response.keys():
            self.access_token = response['token']
        else:
            raise Exception('Bad Response getting Access Token %s' % response['error'])

    def prices(self, columns=None, geography=None, **kwargs):
        """
        :param columns: Optional: list of columns you want back
        :param geography: Optional: list of geographies you want back
        :param kwargs: Optional: filter columns eg brand=['nike', 'addidas']
        :return: Current Prices
        """
        self.data_attributes = ['all', 'iterall', 'page', 'find']
        self.response_data_name = 'prices'
        endpoint = 'prices/'

        params = {}
        if columns is not None:
            params['columns'] = columns
        if geography is not None:
            params['geography'] = geography
        if kwargs is not None:
            for k, v in kwargs:
                params[k] = v

        self._get_request(endpoint, 'GET', params)
        return self

    def data_sources_info(self):
        """
        Retrieves the column names and data types for all data sources
        :return: column names and types for each source
        """
        self.data_attributes = ['all', 'find']
        self.response_data_name = None
        endpoint = 'data_sources_info/'
        self._get_request(endpoint, 'GET')
        return self

    def data_sources(self, columns=None, **kwargs):
        """
        Gets a list of data from a given data source.
        :return: Data from a given / all data sources
        """
        self.data_attributes = ['all', 'iterall', 'page', 'find']
        self.response_data_name = 'data'
        endpoint = 'data_sources/'
        params = {}
        if columns is not None:
            params['columns'] = columns
        if kwargs is not None:
            for k, v in kwargs:
                params[k] = v

        self._get_request(endpoint, 'GET', params)
        return self



