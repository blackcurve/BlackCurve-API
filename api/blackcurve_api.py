import requests
import json
import urllib


class DataHolder(object):
    def __init__(self, api):
        self._api = api
        self._request = self._api.current_request
        self._page_no = 1
        self._max_page = None
        self._pk = None
        self._queryset = []
        self._query = {}
        self._update_query = {}
        self._attribute_map = {}
        self._no_pages = None
        self._data_source = None
        self._object_name = self._api.object_name

    @staticmethod
    def _parse_response(response):
        resp = json.loads(response)
        if 'error' in resp.keys():
            raise Exception(resp['error'])
        return resp

    def _build_request_params(self, method=None, data=None):
        if method is None:
            method = self._api.method
        url = self._api.domain + self._api.endpoint
        # get the pk if there is one
        if self._pk is not None:
            url += self._pk
        # get the page number
        if self._page_no > 1:
            self._api.params['page'] = self._page_no
        else:
            if self._api.params is not None:
                self._api.params.pop('page', None)
                # change lists to comma delimited strings
                for k, v in self._api.params.items():
                    if isinstance(v, list):
                        self._api.params[k] = ','.join(v)

        # get the get params
        if self._api.params:
            url += '?' + urllib.urlencode(self._api.params)
        if self._data_source is not None:
            url += self._data_source
        if data is not None:
            return {'method': method, 'url': url, 'headers': self._api.headers, 'data': data}
        return {'method': method, 'url': url, 'headers': self._api.headers}

    def _get_response(self, params):
        return self._parse_response(requests.request(**params).text)

    def _process_request(self):
        data = self._get_response(self._build_request_params())
        self._no_pages = data.pop('no_pages', None)
        if self._api.response_data_name is not None:
            data = data[self._api.response_data_name]
        if isinstance(data, list):
            for i in data:
                d_obj = DataHolder(self._api)
                d_obj._request = self._api.current_request
                d_obj._object_name = self._api.object_name
                for key, val in i.items():
                    d_obj._query[key] = val
                    self._set_class_attribute(d_obj, key, val)
                self._queryset.append(d_obj)
        elif isinstance(data, dict):
            for k, v in data.items():
                d_obj = DataHolder(self._api)
                d_obj._request = self._api.current_request
                d_obj._object_name = k
                d_obj._data_source = k
                for key, val in v.items():
                    d_obj._query[key] = val
                    self._set_class_attribute(d_obj, key, val)
                self._queryset.append(d_obj)

        if len(self._queryset) == 1:
            return self._queryset[0]
        return self

    def all(self):
        """
        :return: all of the data (all pages)
        """
        result = []
        for p in self._iter_pages():
            if self._api.response_data_name is not None:
                result += p[self._api.response_data_name]
            else:
                result += p
        if self._api.response_data_name is None:
            if len(result) == 1:
                return result[0]
            return result
        return {self._api.response_data_name: result}

    def page(self, number):
        self._page_no = 1
        self._max_page = None
        self._page_no = number
        return self._process_request()

    def pages(self, start, finish):
        """
        :param start: page to start from
        :param finish: page to end on
        :return: concat data for given page range
        """
        if self._api.after_find_attributes is not None:
            self._api.data_attributes += self._api.after_find_attributes
        self._page_no = start
        self._max_page = finish
        return self.all()

    def find(self, pk):
        self._queryset = []
        if self._api.after_find_attributes is not None:
            self._api.data_attributes += self._api.after_find_attributes
        self._page_no = 1
        self._pk = pk
        return self._process_request()

    def delete(self, attribute=None):
        if attribute:
            try:
                item = getattr(self, attribute)
            except AttributeError:
                item = getattr(self, attribute.replace(' ', '_').lower().strip())
            data = {attribute: item}
        else:
            data = self._get_deleted_attributes()
        params = self._build_request_params('DELETE', json.dumps(data))
        resp = self._get_response(params)
        return self

    def create(self, **kwargs):
        data = kwargs
        self._update_query = data
        self.save(True)

    def batch_create(self, object_list):
        for i in object_list:
            self.create(**i)

    def save(self, create=False):
        self._set_changed_attributes()
        if self._update_query:
            params = self._build_request_params('POST', json.dumps(self._update_query))
            resp = self._get_response(params)
            return self

    def _set_changed_attributes(self):
        class_attrs = {x: getattr(self, x, None) for x in dir(self) if not x.startswith('_')}
        class_attrs = {k: v for k, v in class_attrs.items() if not callable(v)}
        cased_class_attrs = {self._attribute_map[k] if k in self._attribute_map.keys() else k: v for k, v in class_attrs.items()}
        for k, v in self._query.items():
            if k in cased_class_attrs.keys():
                if cased_class_attrs[k] == v:
                    del cased_class_attrs[k]
        self._update_query = cased_class_attrs

    def _get_deleted_attributes(self):
        class_attrs = {x: getattr(self, x, None) for x in dir(self) if not x.startswith('_')}
        class_attrs = {k: v for k, v in class_attrs.items() if not callable(v)}
        return {k: v for k, v in self._query.items() if k not in class_attrs.keys()}

    @staticmethod
    def _set_class_attribute(cls, key, value):
        """
        Formats the attribute name to remove whitespace with _
        :param key: attribute name
        :param value: attribute value
        """
        k = key.replace(' ', '_').lower().strip()
        setattr(cls, k, value)
        cls._attribute_map[k] = key

    def _iter_pages(self):
        """
        Generator function for all the pages
        :return: iterator for result pages
        """
        self._queryset = []
        # reset page number
        if self._max_page is None:
            self._page_no = 1
        last_page = False
        while not last_page:
            obj = self._process_request()
            if self._no_pages is not None:
                if self._max_page is not None:
                    self._no_pages = self._max_page
                if self._page_no == self._no_pages:
                    last_page = True
                    self._page_no = 1
                self._page_no += 1
            else:
                last_page = True
            yield obj

    def __iter__(self):
        if len(self._queryset) > 1:
            for i in self._queryset:
                yield i
        else:
            for k, v in self._query.items():
                yield k, v

    def __getattr__(self, item):
        if callable(self.__getattribute__(item)):
            if item not in self._api.data_attributes:
                raise AttributeError('%s method not allowed' % item)
        return self.__getattribute__(item)

    def __getitem__(self, item):
        object_names = [x._object_name for x in self._queryset]
        idx = object_names.index(item)
        return self._queryset[idx]

    def __setitem__(self, key, value):
        if hasattr(self, key):
            setattr(self, key, value)
        elif hasattr(self, key.replace(' ', '_').lower().strip()):
            setattr(self, key.replace(' ', '_').lower().strip(), value)
        else:
            setattr(self, key, value)

    def __repr__(self):
        if len(self._queryset) > 1:
            return '<%s Object: len %s' % (self._api.object_name, len(self._queryset))
        return '<%s Object>' % self._object_name

    def __len__(self):
        return len(self._queryset)

    def __str__(self):
        if len(self._queryset):
            return self.__repr__()
        else:
            return str(self._query)

    def __delattr__(self, item):
        return self.delete(item)

    def __delitem__(self, key):
        return self.delete(key)


class BlackCurveAPI(object):
    """
    This is the holder for the subdomain and access_token for accessing the API
    """

    def __init__(self, subdomain, access_token=None):
        # self.domain = 'https://%s.blackcurve.io/api/' % subdomain
        self.domain = 'http://127.0.0.1:8000/api/'
        self.object_name = 'BlackCurve API Object'
        self.access_token = access_token
        self.current_request = None
        self.data_attributes = ['all', 'iterall', 'page', 'find']
        self.response_data_name = 'data'
        self.endpoint = None
        self.params = {}
        self.method = None
        self.after_find_attributes = None
        self._data_holder = DataHolder(self)
        self._can_only_change_attributes = False
        self._is_updatable = True

    def __getattr__(self, name):
        if name in self.data_attributes:
            return getattr(self._data_holder, name)
        elif name == '__deepcopy__':
            return None
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
            return self.access_token
        else:
            raise Exception('Bad Response getting Access Token %s' % response['error'])

    def prices(self, columns=None, geography=None, **kwargs):
        """
        :param columns: Optional: list of columns you want back
        :param geography: Optional: list of geographies you want back
        :param kwargs: Optional: filter columns eg brand=['nike', 'addidas']
        :return: Current Prices
        """
        self.object_name = 'Price'
        self.data_attributes = ['all', 'iterall', 'page', 'find']
        self.after_find_attributes = ['all', 'iterall', 'page']
        self.response_data_name = 'prices'
        self._is_updatable = False
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
        self.object_name = 'Data Sources Info'
        self.data_attributes = ['all', 'find', 'delete', 'save']
        self.response_data_name = None
        endpoint = 'data_sources_info/'
        self._get_request(endpoint, 'GET')
        self._can_only_change_attributes = True
        self._is_updatable = False
        return self

    def data_sources(self, columns=None, **kwargs):
        """
        Gets a list of data from a given data source.
        :return: Data from a given / all data sources
        """
        self.object_name = 'Data Sources'
        self.data_attributes = ['find']
        self.after_find_attributes = ['all', 'iterall', 'page', 'create', 'batch_create']
        self.response_data_name = 'data'
        endpoint = 'data_sources/'
        params = {}
        if columns is not None:
            params['columns'] = columns
        if kwargs is not None:
            for k, v in kwargs.items():
                params[k] = v

        self._get_request(endpoint, 'GET', params)
        return self



