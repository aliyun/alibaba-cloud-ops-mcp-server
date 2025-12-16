# -------------------------------------------------------------------------------
# Copyright (c) 2019 Aliyun.com All right reserved. This software is the
# confidential and proprietary information of Aliyun.com ("Confidential
# Information"). You shall not disclose such Confidential Information and shall
# use it only in accordance with the terms of the license agreement you entered
# into with Aliyun.com .
# -------------------------------------------------------------------------------
import requests

API_META_KEYS = (VERSION, RESPONSES, SCHEMA, PROPERTIES, HTTP_SUCCESS_CODE, DEFAULT_VERSION, CODE, REF, APIS,
                 SERVICE_KEY, NAME, IN, PARAMETERS, STYLE, BODY) \
    = ('version', 'responses', 'schema', 'properties', '200', 'defaultVersion', 'code', '$ref', 'apis', 'service',
       'name', 'in', 'parameters', 'style', 'body')



class ApiMetaClient:
    PATH = 'path'
    METHODS = 'methods'
    BASE_URL = 'https://api.aliyun.com/meta/v1'
    POP_API_NAME = (GET_PRODUCT_LIST, GET_API_OVERVIEW, GET_API_INFO, GET_APIDOCS) = \
        ('GetProductList', 'GetApiOverview', 'GetApiInfo', 'GetAPIDocs')

    config = {
        'GetProductList': {'path': 'products.json'},
        'GetApiOverview': {'path': 'products/{service}/versions/{version}/overview.json'},
        'GetApiInfo': {'path': 'products/{service}/versions/{version}/apis/{api}/api.json'},
        'GetAPIDocs': {'path': 'products/{service}/versions/{version}/api-docs.json'},
    }

    @classmethod
    def get_response_from_pop_api(cls, pop_api_name, service=None, api=None, version=None):
        url = None  # 提前定义，防止 except 中引用未定义变量
        try:
            api_config = cls.config.get(pop_api_name)
            try:
                formatted_path = api_config[cls.PATH].format(service=service, api=api, version=version)
            except KeyError as e:
                raise Exception(f'Failed to format path, path: {api_config.get(cls.PATH)}, error: {e}')

            url = f'{cls.BASE_URL}/{formatted_path}'
            response = requests.get(url)
            return response.json()
        except Exception as e:
            raise Exception(f'Failed to get response from pop api, url: {url}, error: {e}')

    @classmethod
    def get_service_version(cls, service):
        data = cls.get_response_from_pop_api(cls.GET_PRODUCT_LIST)
        version = next((item.get(DEFAULT_VERSION) for item in data if item.get(CODE).lower() == service.lower()), None)
        return version

    @classmethod
    def get_all_service_info(cls):
        data = cls.get_response_from_pop_api(cls.GET_PRODUCT_LIST)
        filtered_data = [{"code": item["code"], "name": item["name"]} for item in data]

        return filtered_data

    @classmethod
    def get_service_style(cls, service):
        data = cls.get_response_from_pop_api(cls.GET_PRODUCT_LIST)
        style = next((item.get(STYLE) for item in data if item.get(CODE).lower() == service), 'RPC')
        return style

    @classmethod
    def get_standard_service_and_api(cls, service, api=None, version=None):
        data = cls.get_response_from_pop_api(cls.GET_PRODUCT_LIST)
        service_standard = (next((item.get(CODE) for item in data if item.get(CODE).lower() == service), None))
        api_standard = None
        if api:
            apis = cls.get_response_from_pop_api(cls.GET_API_OVERVIEW, service=service_standard,
                                                 version=version).get(APIS, {})
            for api_name in apis:
                if api_name.lower() == api.lower():
                    api_standard = api_name
        return service_standard, api_standard

    @classmethod
    def get_api_meta(cls, service, api):
        service = service.lower()
        # API_META不包含ROA类型的API，需要通过POP平台的API GetProductList获取Service对应的Version
        # 获取POP平台API META参考文档：https://api.aliyun.com/openmeta/guide
        version = cls.get_service_version(service)
        service_standard, api_standard = cls.get_standard_service_and_api(service, api, version)
        if service_standard is None:
            raise Exception(f'InvalidServiceName: Please check the Service ({service}) you provide.')
        if api_standard is None:
            raise Exception(f'InvalidAPIName: Please check the Service ({service}) and the API ({api}) you provide.')
        data = cls.get_response_from_pop_api(cls.GET_API_INFO, service_standard, api_standard, version)
        return data, version

    @classmethod
    def get_response_from_api_meta(cls, service, api):
        api_meta, version = cls.get_api_meta(service, api)
        property_values = api_meta.get(RESPONSES, {}).get(HTTP_SUCCESS_CODE, {}).get(SCHEMA, {}).get(PROPERTIES, {})
        return property_values, version

    @classmethod
    def get_ref_api_meta(cls, data, service, version):
        service_standard, _ = cls.get_standard_service_and_api(service=service, version=version)
        current_data = cls.get_response_from_pop_api(cls.GET_API_OVERVIEW, service=service_standard, version=version)
        ref_path = data.get(REF)
        path = ref_path.lstrip('#/').split('/')
        for _key in path:
            if _key in current_data:
                current_data = current_data[_key]
            else:
                raise KeyError(f"Path {_key} not found in the JSON data.")

        return current_data

    @classmethod
    def get_api_parameters(cls, service, api, params_in=''):
        """
        params_in: 过滤参数位置，取值：'host', 'query', 'body', 'header'，若为空，则返回所有参数
        """
        api_meta, _ = cls.get_api_meta(service, api)
        parameters = api_meta.get(PARAMETERS)
        param_names = []
        additional_props = []
        # 避免循环引用
        visited_refs = set()

        def get_ref(data, _):
            props = []
            if not isinstance(data, dict):
                return props
            if REF in data:
                ref_path = data.get(REF)
                if ref_path in visited_refs:
                    return props
                visited_refs.add(ref_path)
                referenced_schema = cls.get_ref_api_meta(data, service, _)
                props.extend(get_ref(referenced_schema, _))
                return props
            if PROPERTIES in data:
                for prop_name, prop_details in data.get(PROPERTIES, {}).items():
                    props.append(prop_name)
                    if isinstance(prop_details, dict) and REF in prop_details:
                        props.extend(get_ref(prop_details, _))
            return props

        for param in parameters:
            if params_in and param.get(IN) != params_in:
                continue
            param_name = param.get(NAME)
            if param_name:
                param_names.append(param_name)
            schema = param.get(SCHEMA, {})
            extracted_props = get_ref(schema, _)
            additional_props.extend(extracted_props)
        combined_params = param_names + additional_props
        return combined_params

    @classmethod
    def get_apis_in_service(cls, service):
        version = cls.get_service_version(service)
        data = cls.get_response_from_pop_api(cls.GET_API_OVERVIEW, service=service, version=version)
        apis = list(data[APIS].keys())
        return apis

    @classmethod
    def get_api_field(cls, field_type, service, api, default=None):
        try:
            data, _ = cls.get_api_meta(service, api)
            return data.get(field_type, default)
        except Exception as e:
            return default

    @classmethod
    def get_api_body_style(cls, service, api):
        parameters = cls.get_api_field(PARAMETERS, service, api)
        body_style = None
        if parameters:
            body_style = next((param.get(STYLE) for param in parameters if param.get(IN) == BODY), None)
        return body_style
