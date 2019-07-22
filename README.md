# Cisco SD-WAN EXIM (Export and Import)

*Command line tool for Cisco SD-WAN vManage configuration management.*

---

## Why

Cisco SD-WAN powered by Viptela is a cloud-delivered overlay WAN architecture for enterprises. This project provides a Command line tool interface on top of the REST API programmatic interface offered by the SD-WAN controller, vManage. The final desired outcome is a baseline automation framework for
Cisco SD-WAN. A simple example of the plus value is the time saved migrating templates and policies from lab to production (from one controller to another), while preserving the exact same configurations without any manual misconfigurations.



## Getting Started

These instructions will get you a copy of the project up and running on your local machine.

See Installation and Usage for further instructions.



## Features

Summary of the features/capabilities/actions:
  - **export**             Export entire configuration.
  - **configure**            Import entire configuration.
      - *For Templates and Polices dependencies to be preserved use this option (configure)*
  - **configure_policies**   Import policies, definitions and lists.
  - **configure_templates**  Import feature templates and device templates.
      - *Templates will be imported but dependencies to policies will not be imported*
  - **clean**                Delete template(all) and policy(all) configuration.
      - *For an accurate deploy of a configuration a clean up is required, in case of items named the same*
  - **clean_devices**        Delete certificates and system devices.
  - **clean_policies**       Delete (only) policies, definitions and lists.
  - **clean_templates**      Delete (only) device and feature templates.
      - *Devices should be manually detached before cleanup*
  - **password**                  Update user password
  - **add_user**                  Add user
  - **invalidate_certificates**   Invalidate device certificates
  - **validate_certificates**     Validate device certificates
  - **push_to_controllers**       Push configuration to controllers
  - **detach_devices**            Detach device templates
  - **deactivate_policies**       Deactivate policies



## Technologies & Frameworks Used

This is Cisco Sample Code!

**Cisco Products & Services:**

- Cisco SD-WAN (Viptela)
  - Example: https://www.cisco.com/c/en/us/solutions/enterprise-networks/sd-wan/index.html
  - API Documentation: https://sdwan-docs.cisco.com/Product_Documentation/Command_Reference/vManage_REST_APIs


## Requirements

To use this application, you will need:

* **Python 3.6+** (DO NOT USE PYTHON 2)
* **Cisco SD-WAN 18+**
* A **vManage Cisco SD-WAN account** with read or read/write depending on the action



## Installation

Step-by-step series for how to install the project and its dependencies:
1. Clone the code to your local machine.

```
git clone https://github.com/CiscoSE/cisco-sd-wan-export-import.git
cd cisco-sd-wan-export-import
```

2. Setup Python Virtual Environment (requires Python 3 and Requests)

```
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

3. Get your Cisco SD-WAN
 - IP address of the vManage or the DNS name of the vManage.
 - Credentials (Username and Password)

4. GO to next sections (Help and Usage)



## Help

Investigate the built in help with:

```
python sd-wan-exim.py --help
```
or
```
python sd-wan-exim.py -h
```

OUTPUT:

```
usage: sd-wan-exim.py [-h] [-tenant TENANT]
                      vManage username password action [configfile]

Cisco SD-WAN EXIM (Export and Import) Console Script.

Copyright (c) 2019 Cisco and/or its affiliates.

This software is licensed to you under the terms of the Cisco Sample
Code License, Version 1.1 (the "License"). You may obtain a copy of the
License at

               https://developer.cisco.com/docs/licenses

All use of the material herein must be in accordance with the terms of
the License. All rights not expressly granted by the License are
reserved. Unless required by applicable law or agreed to separately in
writing, software distributed under the License is distributed on an "AS
IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
or implied.

Command line tool for Cisco SD-WAN vManage configuration management.

Example: python sd-wan-exim.py <vManage> <username> <password> <action>

Actions:
  export                      Export entire configuration.

  configure                   Import entire configuration.
  configure_policies          Import policies, definitions and lists.
  configure_templates         Import feature templates and device templates.

  clean                       Delete template(all) and policy(all) configuration.
  clean_policies              Delete (only) policies, definitions and lists.
  clean_templates             Delete (only) device and feature templates.

  clean_devices               Delete certificates and system devices.

  password                    Update user password
  add_user                    Add user

  invalidate_certificates     Invalidate device certificates
  validate_certificates       Validate device certificates
  push_to_controllers         Push configuration to controllers
  detach_devices              Detach device templates
  deactivate_policies         Deactivate policies

positional arguments:
  vManage               vManage IP address or DNS name
  username              Username to login the vManage
  password              Password to login the vManage
  action                Action to execute on the vManage
  configfile            Optional, specific export and import archive name

optional arguments:
  -h, --help            show this help message and exit
  -tenant TENANT, --tenant TENANT
                        Specify tenant in multi-tenant setup
```



## Usage

Basic example how to use the Cisco SD-WAN EXIM (Export and Import):

```
python sd-wan-exim.py myvmanage.cisco.com myusername mypassword export
```

Multi-tenant example how to use the Cisco SD-WAN EXIM (Export and Import):

```
python sd-wan-exim.py myvmanage.cisco.com myusername mypassword export -tenant mytenantname
```

Specific archive export example how to use the Cisco SD-WAN EXIM (Export and Import):

```
python sd-wan-exim.py myvmanage.cisco.com myusername mypassword export mysdwanarchive.tar.gz
```

Specific archive import multi-tenant example how to use the Cisco SD-WAN EXIM (Export and Import):

```
python sd-wan-exim.py myvmanage.cisco.com myusername mypassword configure mysdwanarchive.tar.gz -tenant mytenantname
```

---

Normal Workflow for Templates Only: export -> clean_templates -> configure_templates

NOTE: The clean action can be skipped if you want to keep existing configurations and it's not overlapping.  
```
python sd-wan-exim.py <vManage> <username> <password> export
python sd-wan-exim.py <vManage> <username> <password> clean_templates
python sd-wan-exim.py <vManage> <username> <password> configure_templates
```

Normal Workflow for Policies Only: export -> clean_policies -> configure_policies

NOTE: The clean action can be skipped if you want to keep existing configurations and it's not overlapping.  
```
python sd-wan-exim.py <vManage> <username> <password> export
python sd-wan-exim.py <vManage> <username> <password> clean_policies
python sd-wan-exim.py <vManage> <username> <password> configure_policies
```

Normal Workflow for Templates with Policies: export -> clean -> configure

NOTE: The clean action can be skipped if you want to keep existing configurations and it's not overlapping.  
```
python sd-wan-exim.py <vManage> <username> <password> export
python sd-wan-exim.py <vManage> <username> <password> clean
python sd-wan-exim.py <vManage> <username> <password> configure
```

---

**NOTE:** The configuration archive will be exported to the same folder where the script is.

**NOTE:** When importing/configuring please have the configuration archive named config_archive.tar.gz(or the one used as parameter) in the same folder

**NOTE:** The configure option will not overwrite items(templates/policies) that have the same name, they will be skipped and the process will continue.

## ToDo's:

- [x] Add option to specify archive name as parameter
- [x] Add option to detach devices before cleanup
- [ ] Add support for Python 2
- [ ] Extend partial policy import capabilities



## Authors & Maintainers

People responsible for the creation and maintenance of this project:

- Octavian Preda <opreda@cisco.com> - for any questions or issues



## Credits

* Getting Started with Cisco SD-WAN REST APIs
- `git clone https://github.com/ai-devnet/Getting-started-with-Cisco-SD-WAN-REST-APIs.git`



## License

This project is licensed to you under the terms of the [Cisco Sample
Code License](./LICENSE).
