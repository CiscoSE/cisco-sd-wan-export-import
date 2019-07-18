# Cisco SD-WAN EXIM (Export and Import)

*Command line tool for Cisco SD-WAN vManage configuration management.*

---

**ToDo's:**

- [ ] Consider writing your README first.  Doing so helps you clarify your intent, focuses your project, and it is much more fun to write documentation at the beginning of a project than at the end of one, see:
    - [Readme Driven Development](http://tom.preston-werner.com/2010/08/23/readme-driven-development.html)
    - [GitHub Guides: Mastering Markdown](https://guides.github.com/features/mastering-markdown/)
- [ ] Ensure you put the [license and copyright header](./HEADER) at the top of all your source code files.
- [ ] Be mindful of the third-party materials you use and ensure you follow Cisco's policies for creating and sharing Cisco Sample Code.

---

## Motivation

Include a short description of the motivation behind the creation and maintenance of the project.  Explain **why** the project exists.

## Show Me!

What visual, if shown, clearly articulates the impact of what you have created?  In as concise a visualization as possible (code sample, CLI output, animated GIF, or screenshot) show what your project makes possible.

## Getting Started

These instructions will get you a copy of the tool up and running on your local machine.

See Install and Setup for further instructions.

## Features

Include a succinct summary of the features/capabilities of your project.

- Feature 1
- Feature 2
- Feature 3

Actions:
  - **clean**                Delete template(all) and policy(all) configuration.
      - **For an accurate deploy of a configuration a clean up is required**
  - **clean_devices**        Delete certificates and system devices.
  - **clean_policies**       Delete (only) policies, definitions and lists.
  - **clean_templates**      Delete (only) device and feature templates.
      - **Devices should be manually detached before cleanup**

  - **configure**            Import entire configuration.
      - **For Templates and Polices dependicies to be preserved use this option (configure)**
  - **configure_policies**   Import vEdge/Vsmart policies, definitions and lists.
  - **configure_templates**  Import feature templates and device templates.
      - **Templates will imported but dependicies to policies will not be imported**

  - **export**               Export entire configuration.

_______

Normal Workflow for Templates Only: export -> clean_templates -> configure_templates

Normal Workflow for Policies Only: export -> clean_policies -> configure_policies

Normal Workflow fro Templates With Policies: export -> clean -> configure

_______

**NOTE** The configuration archive will be exported to the same folder where the script is.

**NOTE** When importing/configuring please have the configuration archive named config_archive.tar.gz in the same folder

**TO DO**:
 - add option to specify archive name as parameter
 - add option to detach devices before cleanup
 - extend partial policy import capabilities

## Technologies & Frameworks Used

This is Cisco Sample Code!  What Cisco and third-party technologies are you working with?  Are you using a coding framework or software stack?  A simple list will set the context for your project.

**Cisco Products & Services:**

- Product
- Service

**Third-Party Products & Services:**

- Product
- Service

**Tools & Frameworks:**

- Framework 1
- Automation Tool 2

## Requirements

To use this application you will need:

* Python 3.6+ (DO NOT USE PYTHON 2)
* Cisco SD-WAN 18+
* A Cisco SD-WAN account with permissions to invalidate certificates

## Installation

Provide a step-by-step series of examples and explanations for how to install your project and its dependencies.
Clone the code to your local machine.

```
git clone https://wwwin-github.cisco.com/opreda/sd-wan-exim.git
cd sd-wan-exim
```

Setup Python Virtual Environment (requires Python 3)

```
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Get your Cisco SD-WAN
 - IP address of the vmanage or the dns name of the vmanage.
 - Credentials (Username and Password)

## Help

Investigate the built in help with:

```
python sd-wan-exim.py --help
```

OUTPUT:

```
usage: sd-wan-exim.py [-h] vManage username password action

Usage: python sd-wan-exim.py <vManage> <username> <password> <action>

  Command line tool for configuration management on CISCO SD-WAN vManage.

Actions:
  clean                Delete template(all) and policy(all) configuration.
    **For an accurate deploy of a configuration a clean up is required**
  clean_devices        Delete certificates and system devices.
  clean_policies       Delete (only) policies, definitions and lists.
  clean_templates      Delete (only) device and feature templates.

  configure            Import entire configuration.
    **For Templates and Polices dependicies to be preserved use this option (configure)**
  configure_policies   Import vEdge/Vsmart policies, definitions and lists.
  configure_templates  Import feature templates and device templates.
    **Templates will imported but dependicies to policies will not be imported***

  export               Export entire configuration.

!!!!!
Normal Workflow for Templates Only: export -> clean_templates -> configure_templates
Normal WOrkflow for Policies Only: export -> clean_policies -> configure_policies
Normal Workflow fro Templates With Policies: export -> clean -> configure
!!!!!

Parameters:
    vManage : Ip address of the vmanage or the dns name of the vmanage
    username : Username to login the vmanage
    password : Password to login the vmanage
    action : See above Actions

Note: All the arguments are mandatory

positional arguments:
  vManage     IP address of the vManage or the DNS name of the vManage
  username    Username to login the vManage
  password    Password to login the vManage
  action      Action to execute on the vManage

optional arguments:
  -h, --help  show this help message and exit
```

## Usage

If people like your project, they will want to use it.  Show them how.
```
python sd-wan-exim.py <vManage> <username> <password> <action>
```

## Authors & Maintainers

Smart people responsible for the creation and maintenance of this project:

- Octavian Preda <opreda@cisco.com> - for any questions or issues

## Credits

* Getting Started with Cisco SD-WAN REST APIs
- `git clone https://github.com/ai-devnet/Getting-started-with-Cisco-SD-WAN-REST-APIs.git`

Give proper credit.  Inspired by another project or article?  Was your work made easier by a tutorial?  Include links to the people, projects, and resources that were influential in the creation of this project.

## License

This project is licensed to you under the terms of the [Cisco Sample
Code License](./LICENSE).
