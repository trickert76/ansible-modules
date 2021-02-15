#!/usr/bin/python
''' Allow to store host specific configurations that can be read and stored from a JSON file. '''

import os
import shutil
import json

from pathlib import Path
from ansible.module_utils.basic import AnsibleModule

ANSIBLE_METADATA = {
        'metadata_version': '1.1',
        'status': ['preview'],
        'supported_by': 'acoby GmbH'
}

DOCUMENTATION = '''
---
module: define_configuration
short_description: Allow to store host specific configurations that can be read and stored
version_added: "2.9"
description:
        - This module allows defining host specific facts or configurations. You can define a dict
            with a list of key value pairs. When you register the result, then you have access to
            the configurations. See example
options:
        file:
                description:
                        - location of the file (JSON format) that holds the configuration
                type: str
        content:
                description:
                        - contains newly or already existing configuration values in key-value format.
                            Keys and Values should be of type str.
                type: dict
        override:
                description:
                        - if true, then the given value will override the already existing value.
                type: bool
        owner:
                description:
                        - the name of the user owner of the file
                type: str
        group:
                description:
                        - the name of the group owner of the file
                type: str
        mode:
                description:
                        - the mode of the file.
                type: int
        dir_mode:
                description:
                        - the mode of the directory, where the file is in (if it must be generated).
                type: int
'''

EXAMPLES = '''
- name: Define a configuration on the given host
    define_configuration:
        file: /etc/ansible_local.json
        content:
            service_secret: "{{ lookup('password', '/dev/null length=32 chars=ascii_letters,digits') }}"
            service_websocket_secret: "{{ lookup('password', '/dev/null length=128') | b64encode }}"
            backup_cron_hour: "{{ 6 | random }}"
            backup_cron_min: "{{ 59 | random(start=5) }}"
        owner: root
        group: root
        mode: 0600
    register: configuration
- name: "Output configuration value key backup_cron_hour"
    debug:
        msg: "{{ configuration.value.backup_cron_hour }}"
'''

RETURN = '''
msg:
    description: Message as to what action was taken
    returned: always
    type: str
    sample: Configuration created.
value:
    description: List of all known configurations
    returned: always
    type: dict
'''

def read_config(file):
    ''' load config from json file '''
    with open(file) as configfile:
        config = json.load(configfile)
    return config

def write_config(file, content, dir_mode, mode, owner, group):
    ''' write config from json file '''
    os.makedirs(name=str(file.parent),mode=dir_mode,exist_ok=True)

    with open(str(file), 'w') as configfile:
        json.dump(content, configfile)

    os.chmod(str(file) , mode)
    if (owner is not None and group is not None):
        shutil.chown(str(file),owner,group)

def main():
    ''' runs the module '''
    module = AnsibleModule(
        argument_spec = dict(
            file = dict(type='str', required=True),
            content = dict(type='dict', required=True),
            override = dict(type='bool', default=False),
            owner = dict(type='str'),
            group = dict(type='str'),
            dir_mode = dict(type='int', default=0o0700),
            mode = dict(type='int', default=0o0600)
        ),
        supports_check_mode=True
    )

    file = Path(module.params.get('file'))
    content = module.params.get('content')
    override = module.params.get('override')

    mode = module.params.get('mode')
    dir_mode = module.params.get('dir_mode')

    changeset = content

    result = dict(changed=False, msg='', diff={}, value=changeset, proposed=changeset.copy())

    if not file.exists():
        # create file with content
        if not module.check_mode:
            write_config(file=file,
                         content=changeset,
                         dir_mode=dir_mode,
                         mode=mode,
                         owner=module.params.get('owner'),
                         group=module.params.get('group')
                         )

        if module._diff:
            result['diff'] = dict(before='', after=changeset)

        result['changed'] = True
        result['value'] = changeset
        result['msg'] = 'Configuration created'

    else:
        # read content and merge
        before_data = read_config(file)

        if not override:
            # do not override existing data
            for name in before_data:
                if name in changeset:
                    changeset[name] = before_data[name]
            result['changed'] = False
            result['msg'] = 'Configuration read'
        else:
            result['changed'] = True
            result['msg'] = 'Configuration updated'

        updated_data = before_data.copy()
        updated_data.update(changeset)

        if not module.check_mode:
            write_config(file=file,
                         content=updated_data,
                         dir_mode=dir_mode,
                         mode=mode,
                         owner=module.params.get('owner'),
                         group=module.params.get('group')
                         )

        if module._diff:
            result['diff'] = dict(before=before_data, after=updated_data)

        result['value'] = updated_data

    module.exit_json(**result)

if __name__ == '__main__':
    main()
