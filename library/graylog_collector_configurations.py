#!/usr/bin/python
# (c) 2019, Whitney Champion <whitney.ellis.champion@gmail.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

ANSIBLE_METADATA = {'metadata_version': '1.1',
                    'status': ['preview'],
                    'supported_by': 'community'}

DOCUMENTATION = '''
module: graylog_collector_configurations
short_description: Communicate with the Graylog API to manage collector configurations
description:
    - The Graylog collector_configurations module manages Graylog collector configurations
version_added: "2.9"
author: "Whitney Champion (@shortstack)"
options:
  endpoint:
    description:
      - Graylog endoint. (i.e. graylog.mydomain.com).
    required: false
  graylog_user:
    description:
      - Graylog privileged user username.
    required: false
  graylog_password:
    description:
      - Graylog privileged user password.
    required: false
  action:
    description:
      - Action to take against collector configuration API.
    required: false
    default: list_configurations
    choices: [ list_configurations, query_collector_configurations ]
  configuration_id:
    description:
      - Configuration id.
    required: false
  configuration_name:
    description:
      - Configuration name.
    required: false
  configuration_tags:
    description:
      - Configuration tags.
    required: false
  snippet_name:
    description:
      - Snippet name.
    required: false
  snippet_source:
    description:
      - Snippet source code.
    required: false
  backend:
    description:
      - Snippet backend, ex: winlogbeat, filebeat, nxlog
    required: false
'''

EXAMPLES = '''
# List collector configurations
- graylog_collector_configurations:
    endpoint: "graylog.mydomain.com"
    graylog_user: "username"
    graylog_password: "password"

# Get collector configuration from configuration name query_collector_configurations
- graylog_collector_configurations:
    action: query_collector_configurations
    endpoint: "graylog.mydomain.com"
    graylog_user: "username"
    graylog_password: "password"
    configuration_name: "windows-collector-confiuration"
  register: configuration

 # Update snippet for a configuration
 - graylog_collector_configurations:
     action: update_snippet
     endpoint: "graylog.mydomain.com"
     graylog_user: "username"
     graylog_password: "password"
     configuration_name: "windows-collector-configuration"
     snippet_name: "client-x"
     snippet_source: |
        # filebeat or winlog beat source here
   register: configuration
'''

RETURN = '''
json:
  description: The JSON response from the Graylog API
  returned: always
  type: str
msg:
  description: The HTTP message from the request
  returned: always
  type: str
  sample: OK (unknown bytes)
status:
  description: The HTTP status code from the request
  returned: always
  type: int
  sample: 200
url:
  description: The actual URL used for the request
  returned: always
  type: str
  sample: https://www.ansible.com/
'''


# import module snippets
import json
import base64
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.urls import fetch_url, to_text


def list_configurations(module, configuration_url, headers, configuration_id, query):

    if configuration_id is not None and configuration_id != "":
        url = configuration_url + "/%s" % (configuration_id)
    elif query == "yes" and configuration_id == "":
        url = configuration_url + "/0"
    else:
        url = configuration_url

    response, info = fetch_url(module=module, url=url, headers=json.loads(headers), method='GET')

    if info['status'] != 200:
        module.fail_json(msg="Fail: %s" % ("Status: " + str(info['msg']) + ", Message: " + str(info['body'])))

    try:
        content = response.read()
    except AttributeError:
        content = info.pop('body', '')

    return info['status'], info['msg'], content, url


def query_collector_configurations(module, configuration_url, headers, configuration_name):

    url = configuration_url

    response, info = fetch_url(module=module, url=url, headers=json.loads(headers), method='GET')

    if info['status'] != 200:
        module.fail_json(msg="Fail: %s" % ("Status: " + str(info['msg']) + ", Message: " + str(info['body'])))

    try:
        content = response.read()
        collector_configurations = json.loads(content)
    except AttributeError:
        content = info.pop('body', '')

    configuration_id = ""
    if collector_configurations is not None:

        i = 0
        while i < len(collector_configurations['configurations']):
            configuration = collector_configurations['configurations'][i]
            if configuration_name == configuration['name']:
                configuration_id = configuration['id']
                break
            i += 1

    return configuration_id


def query_snippets(module, configuration_url, headers, configuration_id, snippet_name):

    url = configuration_url + "/%s" % (configuration_id)

    response, info = fetch_url(module=module, url=url, headers=json.loads(headers), method='GET')

    if info['status'] != 200:
        module.fail_json(msg="Fail: %s" % ("Status: " + str(info['msg']) + ", Message: " + str(info['body'])))

    try:
        content = response.read()
        configuration = json.loads(content)
        snippets = configuration['snippets']
    except AttributeError:
        content = info.pop('body', '')

    snippet_id = ""
    if snippets is not None:

        i = 0
        while i < len(snippets):
            snippet = snippets[i]
            if snippet_name == snippet['name']:
                snippet_id = snippet['snippet_id']
                break
            i += 1

    return snippet_id


def update_snippet(module, configuration_url, headers, configuration_id, snippet_id, snippet_name, snippet_source, backend):

    url = configuration_url + "/%s/snippets/%s" % (configuration_id, snippet_id)

    payload = {}

    if backend is not None:
        payload['backend'] = backend
    if snippet_name is not None:
        payload['name'] = snippet_name
    if snippet_source is not None:
        payload['snippet'] = snippet_source

    response, info = fetch_url(module=module, url=url, headers=json.loads(headers), method='PUT', data=module.jsonify(payload))

    if info['status'] != 202:
        module.fail_json(msg="Fail: %s" % ("Status: " + str(info['msg']) + ", Message: " + str(info['body'])))

    try:
        content = response.read()
    except AttributeError:
        content = info.pop('body', '')

    return info['status'], info['msg'], content, url


def get_token(module, endpoint, username, password):

    headers = '{ "Content-Type": "application/json", "X-Requested-By": "Graylog API", "Accept": "application/json" }'

    url = "https://%s/api/system/sessions" % (endpoint)

    payload = {}
    payload['username'] = username
    payload['password'] = password
    payload['host'] = endpoint

    response, info = fetch_url(module=module, url=url, headers=json.loads(headers), method='POST', data=module.jsonify(payload))

    if info['status'] != 200:
        module.fail_json(msg="Fail: %s" % ("Status: " + str(info['msg']) + ", Message: " + str(info['body'])))

    try:
        content = response.read()
        session = json.loads(content)
    except AttributeError:
        content = info.pop('body', '')

    session_string = session['session_id'] + ":session"
    session_bytes = session_string.encode('utf-8')
    session_token = base64.b64encode(session_bytes)

    return session_token


def main():
    module = AnsibleModule(
        argument_spec=dict(
            endpoint=dict(type='str'),
            graylog_user=dict(type='str'),
            graylog_password=dict(type='str', no_log=True),
            action=dict(type='str', required=False, default='list_configurations',
                        choices=['list_configurations', 'query_collector_configurations', 'update_snippet']),
            configuration_id=dict(type='str'),
            configuration_name=dict(type='str'),
            configuration_tags=dict(type='list'),
            snippet_name=dict(type='str'),
            snippet_source=dict(type='str'),
            backend=dict(type='str')
        )
    )

    endpoint = module.params['endpoint']
    graylog_user = module.params['graylog_user']
    graylog_password = module.params['graylog_password']
    action = module.params['action']
    configuration_id = module.params['configuration_id']
    configuration_name = module.params['configuration_name']
    configuration_tags = module.params['configuration_tags']
    snippet_name = module.params['snippet_name']
    snippet_source = module.params['snippet_source']
    backend = module.params['backend']

    configuration_url = "https://%s/api/plugins/org.graylog.plugins.collector/configurations" % (endpoint)

    api_token = get_token(module, endpoint, graylog_user, graylog_password)
    headers = '{ "Content-Type": "application/json", "X-Requested-By": "Graylog API", "Accept": "application/json", \
                "Authorization": "Basic ' + api_token.decode() + '" }'

    if action == "list_configurations":
        query = "no"
        status, message, content, url = list_configurations(module, configuration_url, headers, configuration_id, query)
    elif action == "update_snippet":
        configuration_id = query_collector_configurations(module, configuration_url, headers, configuration_name)
        snippet_id = query_snippets(module, configuration_url, headers, configuration_id, snippet_name)
        status, message, content, url = update_snippet(module, configuration_url, headers, configuration_id, snippet_id,
                                                        snippet_name, snippet_source, backend)
    elif action == "query_collector_configurations":
        configuration_id = query_collector_configurations(module, configuration_url, headers, configuration_name)
        query = "yes"
        status, message, content, url = list_configurations(module, configuration_url, headers, configuration_id, query)

    uresp = {}
    content = to_text(content, encoding='UTF-8')

    try:
        js = json.loads(content)
    except ValueError:
        js = ""

    uresp['json'] = js
    uresp['status'] = status
    uresp['msg'] = message
    uresp['url'] = url

    module.exit_json(**uresp)


if __name__ == '__main__':
    main()