import requests
import json
import sys
import collections

# Python 2 & 3 compatible url-encoding
if sys.version_info >= (3, 0):
    from urllib.parse import urlencode
else:
    from urllib import urlencode


class APIException(Exception):
    """ Custom Exception """
    pass


def data_func_called_dec(evaluated=False):
    """
    A decorator for the data functions in the DataHolder class
    :param evaluated: if the function will be immediately evaluated or not (False)
    :return: method
    """
    def decorator(func):
        def wrapper(self, *args, **kwargs):
            """ Log the function call """
            self._data_function_called_dict[func.__name__] = True
            if evaluated:
                output = func(self, *args, **kwargs)
                output._data_function_evaluated_dict[func.__name__] = True
                self._data_function_evaluated_dict[func.__name__] = True
                for i in output._pages_queryset:
                    i._data_function_evaluated_dict[func.__name__] = True
                for i in self._pages_queryset:
                    i._data_function_evaluated_dict[func.__name__] = True
                return output
            return func(self, *args, **kwargs)
        return wrapper
    return decorator


class DataHolder(object):
    def __init__(self, api):
        """
        Object for holding & CRUD operations on BlackCurve data objects
        :param api: API Credentials object (BlackCurveAPI)
        """
        self._api = api
        self._request = self._api.current_request

        # has a data function been evaluated?
        self._data_function_evaluated_dict = dict(all=False, page=False, pages=False, find=False, delete=False,
                                                  save=False, create=False, batch_create=False)
        self._data_function_called_dict = dict(all=False, page=False, pages=False, find=False, delete=False, save=False,
                                               create=False, batch_create=False)

        # page info (multi & single page object)
        self._page_no = 1
        self._max_page = None
        self._no_pages = None

        # id / pk of the item (single item object)
        self._pk = None

        # object data storage
        self._pages_queryset = list()
        self._query = dict()

        # data attribute changes storage
        self._update_query = dict()
        self._attribute_map = dict()

        self._data_source = None
        self._object_name = self._api.object_name

    @staticmethod
    def _parse_response(response):
        """
        decode the response and check for errors
        :param response: http response
        :return: decoded response
        """
        resp = json.loads(response)
        if not isinstance(resp, list):
            if 'error' in resp.keys():
                raise APIException(resp['error'])
        return resp

    def _build_request_params(self, method=None, data=None):
        """
        Build the request params
        :param method: http method
        :param data: any post data
        :return: dict of the params to make the request
        """
        if method is None:
            method = self._api.method
        url = self._api.domain + self._api.endpoint
        # get the pk if there is one
        if self._pk is not None:
            url += '?id=' + str(self._pk)
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
            url += '?' + urlencode(self._api.params)
        if self._data_source is not None:
            url += self._data_source
        if data is not None:
            return {'method': method, 'url': url, 'headers': self._api.headers, 'data': data}
        return {'method': method, 'url': url, 'headers': self._api.headers}

    def _get_response(self, params):
        """
        Make the request
        :param params: http parameters
        :return: response
        """
        return self._parse_response(requests.request(**params).text)

    def _process_request(self, new_instance=False):
        """
        Update this object with the data
        :param new_instance: If we need a new instance or not
        :return: self
        """
        data = self._get_response(self._build_request_params())
        self._no_pages = data.pop('no_pages', None)
        inst = DataHolder(self._api)
        if self._api.response_data_name is not None:
            data = data[self._api.response_data_name]

        if isinstance(data, list):
            for i in data:
                d_obj = DataHolder(self._api)
                d_obj._api.data_attributes = self._api.data_item_attributes
                d_obj._request = self._api.current_request
                d_obj._object_name = self._api.object_name
                for key, val in i.items():
                    d_obj._query[key] = val
                    self._set_class_attribute(d_obj, key, val)
                if new_instance:
                    inst._pages_queryset.append(d_obj)
                else:
                    self._pages_queryset.append(d_obj)
        elif isinstance(data, dict):
            for k, v in data.items():
                d_obj = DataHolder(self._api)
                d_obj._request = self._api.current_request
                d_obj._api.data_attributes = self._api.data_item_attributes
                d_obj._object_name = k
                d_obj._data_source = k
                for key, val in v.items():
                    d_obj._query[key] = val
                    self._set_class_attribute(d_obj, key, val)
                if new_instance:
                    inst._pages_queryset.append(d_obj)
                else:
                    self._pages_queryset.append(d_obj)
        if new_instance:
            return inst
        if len(self._pages_queryset) == 1:
            return self._pages_queryset[0]
        return self

    @data_func_called_dec()
    def all(self):
        """
        Get all of the entries
        :return: all of the data (all pages)
        """
        return self

    @data_func_called_dec(True)
    def page(self, number):
        """
        Get a single page of data
        :param number: page number
        :return: data
        """
        self._page_no = 1
        self._max_page = None
        self._page_no = number
        if self._data_function_called_dict['all'] and not self._data_function_evaluated_dict['all']:
            return self._pages_queryset[0]
        return self._process_request()

    @data_func_called_dec()
    def pages(self, start, finish):
        """
        Get a range of pages of data
        :param start: page to start from
        :param finish: page to end on
        :return: concat data for given page range
        """
        if self._api.after_find_attributes is not None:
            self._api.data_attributes += self._api.after_find_attributes
        self._page_no = start
        self._max_page = finish
        return self

    @data_func_called_dec(True)
    def find(self, pk):
        """
        Find a single object
        :param pk: ID for the object
        :return: object
        """
        self._pages_queryset = []
        if self._api.after_find_attributes is not None:
            self._api.data_attributes += self._api.after_find_attributes
        self._page_no = 1
        self._pk = pk
        return self._process_request()

    @data_func_called_dec()
    def delete(self, attribute=None):
        """
        Deletes a Data Object
        :param attribute: Optional: for deleting a single value
        :return: self
        """
        if attribute:
            try:
                item = getattr(self, attribute)
            except AttributeError:
                item = getattr(self, attribute.replace(' ', '_').lower().strip())
            data = {attribute: item}
        else:
            data = self._get_deleted_attributes()
        params = self._build_request_params('DELETE', json.dumps(data))
        self._get_response(params)
        return self

    @data_func_called_dec()
    def create(self, *args, **kwargs):
        """
        Create a new data object
        :param args: Object data
        :param kwargs: Object data
        :return: self
        """
        if args:
            if isinstance(args, tuple) or isinstance(args, list):
                if len(args) > 1:
                    raise TypeError('Too many rows, use bulk_create() to add multiple rows at once')
                args = args[0]
            if not isinstance(args, dict):
                raise TypeError('arguments must be a dictionary')
            data = args
        else:
            if not kwargs:
                raise TypeError('create() takes at least one argument')
            data = kwargs
        if not data:
            raise TypeError('create() takes at least one argument')
        self._update_query = data
        return self.save(True)

    @data_func_called_dec()
    def batch_create(self, object_list):
        """
        Create multiple data objects at once
        :param object_list: list of objects to be created
        :return: self
        """
        for i in object_list:
            self.create(**i)
        return self

    @data_func_called_dec()
    def save(self, create=False):
        """
        Save data objects
        :param create: Whether or not to create a new entry or update an existing one
        :return: self
        """
        if not create:
            self._set_changed_attributes()
        if self._update_query:
            data = self._update_query
            try:
                data['Product ID'] = self._query['product id']
            except KeyError:
                try:
                    data['system id'] = self._query['system id']
                except KeyError:
                    data['id'] = self._query['id']
            params = self._build_request_params('POST', json.dumps(data))
            self._get_response(params)
        return self

    def _set_changed_attributes(self):
        """
        Find all of the objects attributes that have changes (for updates)
        """
        class_attrs = {x: getattr(self, x, None) for x in dir(self) if not x.startswith('_')}
        class_attrs = {k: v for k, v in class_attrs.items() if not callable(v)}
        class_attrs = {k: v for k, v in class_attrs.items() if v is not None}
        cased_class_attrs = {self._attribute_map[k] if k in self._attribute_map.keys() else k: v for k, v in
                             class_attrs.items()}
        for k, v in self._query.items():
            if k in cased_class_attrs.keys():
                if cased_class_attrs[k] == v:
                    del cased_class_attrs[k]
        self._update_query = cased_class_attrs

    def _get_deleted_attributes(self):
        """
        Get the attributes that have been deleted
        :return: deleted attributes (dict)
        """
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
        if k == 'system_id':
            setattr(cls, 'id', value)
            cls._attribute_map['id'] = 'id'
        cls._attribute_map[k] = key

    @property
    def _data_function_called(self):
        """
        Has a data function been called?
        :return: Boolean
        """
        if True in self._data_function_called_dict.values():
            return True
        return False

    @property
    def _data_function_evaluated(self):
        """
        Has a data function been evaluated?
        :return: Boolean
        """
        if True in self._data_function_evaluated_dict.values():
            return True
        return False

    @property
    def needs_evaluating(self):
        """
        Does the object need evaluating (API request)
        :return: Boolean
        """
        if not self._data_function_evaluated:
            return True
        if not self._query:
            if not self._pages_queryset:
                return True
        return False

    def _set_evaluated_function(self):
        """
        Log the evaluation of a data function
        :return: Nothing
        """
        for k, v in self._data_function_called_dict.items():
            if v:
                self._data_function_evaluated_dict[k] = True

    def _iter_pages(self):
        """
        Generator function for evaluating the requests and updating the object
        :return: iterator for results pages
        """
        if not self._data_function_evaluated_dict['all']:
            self._pages_queryset = []
        # reset page number
        if self._max_page is None:
            self._page_no = 1
        last_page = False
        while not last_page:
            try:
                obj = self._process_request(True)
            except Exception as e:
                raise StopIteration(*e.args)
            if self._data_function_called_dict['all'] or self._data_function_called_dict['pages']:
                self._pages_queryset += obj._pages_queryset
            if self._no_pages is not None:
                if self._max_page is not None:
                    self._no_pages = self._max_page
                if self._page_no == self._no_pages:
                    last_page = True
                    self._set_evaluated_function()
                    self._page_no = 1
                self._page_no += 1
            else:
                last_page = True
                self._set_evaluated_function()
            yield obj

    def __iter__(self):
        if self.needs_evaluating:
            for p in self._iter_pages():
                for i in p._pages_queryset:
                    yield i
        else:
            if len(self._pages_queryset) > 1:
                for i in self._pages_queryset:
                    yield i
            else:
                for k, v in self._query.items():
                    yield k, v

    def __getattribute__(self, item):
        if callable(object.__getattribute__(self, item)) and '_' not in item:
            if item not in self._api.data_attributes:
                raise AttributeError('%s method not allowed' % item)
            if item in self._api.data_attributes and True in self._data_function_called_dict.values():
                raise AttributeError('%s method not allowed' % item)
        return object.__getattribute__(self, item)

    def __getitem__(self, item):
        if isinstance(item, int):
            if self._pages_queryset:
                return self._pages_queryset[item]
            else:
                if self._data_function_evaluated_dict['all']:
                    return list(self)[0]
                raise ValueError
        else:
            object_names = [x._object_name for x in self._pages_queryset]
            try:
                idx = object_names.index(item)
            except ValueError:
                try:
                    return self._query[item]
                except ValueError:
                    return self._pages_queryset[item]
            return self._pages_queryset[idx]

    def __setitem__(self, key, value):
        if hasattr(self, key):
            setattr(self, key, value)
        elif hasattr(self, key.replace(' ', '_').lower().strip()):
            setattr(self, key.replace(' ', '_').lower().strip(), value)
        else:
            setattr(self, key, value)

    def __repr__(self):
        if len(self._pages_queryset) > 1:
            return '<%s Object: len %s>' % (self._api.object_name, len(self._pages_queryset))
        return '<%s Object>' % self._object_name

    def __len__(self):
        # evaluate the generator
        collections.deque(self.__iter__(), maxlen=0)
        if self._query:
            return len(self._query)
        return len(self._pages_queryset)

    def __str__(self):
        if self._query:
            return str(self._query)
        else:
            return self.__repr__()

    def __delattr__(self, item):
        return self.delete(item)

    def __delitem__(self, key):
        return self.delete(key)

    def __dict__(self):
        return self._query

    @property
    def __class__(self):
        for _ in self:
            pass
        if self._query:
            return dict
        else:
            return list

    def keys(self):
        return self._query.keys()

    def values(self):
        return self._query.values()

    def items(self):
        return self._query.items()


class BlackCurveAPI(object):
    def __init__(self, subdomain, access_token=None):
        """
        This is the base class for accessing the API either by obtaining an access token by providing a key and secret
        or by just providing a pre-existing token
        :param subdomain: Your BlackCurve subdomain (name of company usually)
        :param access_token: Optional: API access token obtained
        """
        self.domain = 'https://%s.blackcurve.io/api/' % subdomain
        self.object_name = 'BlackCurve API'
        self.access_token = access_token
        self.current_request = None
        self.all_data_attributes = ['all', 'page', 'find', 'pages']
        self.data_attributes = self.all_data_attributes
        self.data_item_attributes = ['save', 'delete']
        self.response_data_name = 'data'
        self.endpoint = None
        self.params = {}
        self.method = None
        self.after_find_attributes = None
        self._data_holder = DataHolder(self)
        self._can_only_change_attributes = False
        self._is_updatable = True
        self._endpoint_called = False

    def __getattr__(self, name):
        if name in self.data_attributes:
            if not self._endpoint_called:
                raise AttributeError('You need to call an endpoint before a data function, e.g. inst.prices().all()')
            return getattr(self._data_holder, name)
        elif name == '__deepcopy__':
            return None
        else:
            raise AttributeError('method \'%s\' not allowed' % name)

    def _set_request_attributes(self, endpoint, method, params=None):
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
            raise APIException('Bad Response getting Access Token %s' % response['error'])

    def prices(self, columns=None, geography=None, changes_only=True, **kwargs):
        """
        :param columns: Optional: list of columns you want back
        :param geography: Optional: list of geographies you want back
        :param changes_only: Optional: whether or not to only receive prices that have changed
        :param kwargs: Optional: filter columns eg. brand=['nike', 'addidas']
        :return: Current Prices
        """
        self._data_holder = DataHolder(self)
        self.object_name = 'Price'
        self.data_attributes = ['all', 'page', 'find', 'pages']
        self.after_find_attributes = ['all']
        self.response_data_name = 'prices'
        self._is_updatable = False
        self._endpoint_called = True
        endpoint = 'prices/'

        params = {}
        if columns is not None:
            params['columns'] = columns
        if geography is not None:
            params['geography'] = geography
        if not changes_only:
            params['changes_only'] = changes_only
        if kwargs is not None:
            for k, v in kwargs:
                params[k] = v

        self._set_request_attributes(endpoint, 'GET', params)
        return self

    def data_sources_info(self):
        """
        Retrieves the column names and data types for all data sources
        :return: column names and types for each source
        """
        self._data_holder = DataHolder(self)
        self.object_name = 'Data Sources Info'
        self.data_attributes = ['all', 'find', 'delete', 'save']
        self.data_item_attributes = []
        self.response_data_name = None
        endpoint = 'data_sources_info/'
        self._set_request_attributes(endpoint, 'GET')
        self._can_only_change_attributes = True
        self._is_updatable = False
        self._endpoint_called = True
        return self

    def data_sources(self, source_name, columns=None, **kwargs):
        """
        Gets a list of data from a given data source.
        :param source_name: DataSource name, e.g. 'SalesHistory'
        :param columns: Optional: The required columns from the DataSource
        :return: Data from a given / all data sources
        """
        self._data_holder = DataHolder(self)
        self.object_name = 'Data Sources'
        self.data_attributes = ['all', 'page', 'create', 'batch_create', 'pages', 'find']
        self.response_data_name = 'data'
        endpoint = 'data_sources/%s' % source_name
        params = {}
        if columns is not None:
            params['columns'] = columns
        if kwargs is not None:
            for k, v in kwargs.items():
                params[k] = v

        self._set_request_attributes(endpoint, 'GET', params)
        self._endpoint_called = True
        return self

    def geographies(self, geography_name=None):
        """
        Gets a list of Geographies (or a single geography if name is specified) and associated data
        :param geography_name: Name of the geography (Optional)
        :return: Geography Data
        """
        self._data_holder = DataHolder(self)
        self.object_name = 'Geographies'
        self.data_attributes = ['all']
        self.response_data_name = 'data'
        endpoint = 'geographies/'
        if geography_name is not None:
            endpoint += geography_name

        self._set_request_attributes(endpoint, 'GET')
        self._endpoint_called = True
        return self

    def currencies(self):
        """
        Gets a list of Currencies and associated data
        :return: Currency Data
        """
        self._data_holder = DataHolder(self)
        self.object_name = 'Currencies'
        self.data_attributes = ['all']
        self.response_data_name = 'data'
        endpoint = 'currencies/'

        self._set_request_attributes(endpoint, 'GET')
        self._endpoint_called = True
        return self
