#!/usr/bin/python
import subprocess
import hashlib
import os

from pathlib import Path
from ansible.module_utils.basic import AnsibleModule

ANSIBLE_METADATA = {
    'metadata_version': '1.1',
    'status': ['preview'],
    'supported_by': 'acoby GmbH'
}

DOCUMENTATION = '''
---
module: move
short_description: Allow to move files idempotent from source to destination
version_added: "2.9"
description:
        - This module allows moving files from one place to another place. The module always
            checks, if the source is still present. If you enable validation, then this module
            also checks, if the source and destination is different and always moves or removes
            source.
options:
        src:
                description:
                        - absolute path to the source file
                type: str
        dest:
                description:
                        - absolute path to the destination file
                type: str
        validate:
                description:
                        - if true (default is false) then it also calculates the checksum of
                            source and destination if both files exists. If they differ, then the
                            destination is replaced by source. And in all cases the source file
                            will be removed, if it is still present
                type: bool
'''

EXAMPLES = '''
- name: Move a file to a new location
    move:
        src: /originalfile
        dest: /newfile
        validate: true
'''

RETURN = '''
msg:
    description: Message as to what action was taken
    returned: always
    type: str
    sample: File already moved.
'''

def checksum(file):
    with open(file, "rb") as file_handle:
        file_hash = hashlib.blake2b()
        while True:
            chunk = file_handle.read(8192)
            if not chunk:
                break
            file_hash.update(chunk)
    return file_hash.hexdigest()

def main():
    module = AnsibleModule(
        argument_spec = dict(
            src = dict(type='str', required=True),
            dest = dict(type='str', required=True),
            validate = dict(type='bool', default=False)
        ),
        supports_check_mode=True
    )

    validate = module.params.get('validate')
    src_file = Path(module.params.get('src'))
    dest_file = Path(module.params.get('dest'))
    msg = 'File already moved'

    if (src_file.exists() and dest_file.exists() and validate):
        src_checksum = checksum(src_file)
        dest_checksum = checksum(dest_file)
        changed = (src_checksum != dest_checksum)
        if changed:
            msg = 'File exists, but is different, moving src to dest'
        else:
            msg = 'File exists and src and dest are the same, removing source'
    else:
        changed = (src_file.exists() and not dest_file.exists())
        if changed:
            msg = 'Destination file doesnt exists, moving src to dest'

    if module.check_mode:
        module.exit_json(changed=changed)

    if changed:
        try:
            os.makedirs(name=str(dest_file.parent),exist_ok=True)
            os.replace(src_file, dest_file)
        except Exception as e:
            module.fail_json(
              msg='Could not move file %s to %s: %s' % (src_file,
                                                        dest_file,
                                                        str(e)))
    else:
        if (validate and src_file.exists()):
            try:
                os.remove(src_file)
            except Exception as e:
                module.fail_json(
                  msg='Could not remove src file %s: %s' % (src_file,
                                                            dest_file,
                                                            str(e)))

    module.exit_json(changed=changed, msg=msg)

if __name__ == '__main__':
    main()
