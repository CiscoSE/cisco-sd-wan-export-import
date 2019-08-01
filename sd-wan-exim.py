#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Cisco SD-WAN EXIM (Export and Import) Console Script.

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

"""

from __future__ import print_function
from pprint import pprint
from collections import OrderedDict
from requests.packages.urllib3.exceptions import InsecureRequestWarning

import requests
import sys
import json
import argparse
import tarfile
import glob
import os
import shutil
import time
import urllib.parse

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

__author__ = "Octavian Preda"
__email__ = "opreda@cisco.com"
__version__ = "1.4.0"
__copyright__ = "Copyright (c) 2019 Cisco and/or its affiliates."
__license__ = "Cisco Sample Code License, Version 1.1"
__status__ = "Development"


""" GLOBAL VARIABLES """
DIR_PATH = os.path.dirname(os.path.abspath(__file__))
CONFIG_ARCH = "config_archive.tar.gz"
HEADER_VSESSION = ""
ITEM_DIC =  {
                "device_template" : ("template/device", "templateId"),
                "feature_template" : ("template/feature", "templateId"),
                "vedge_policy" : ("template/policy/vedge", "policyId"),
                "vsmart_policy" : ("template/policy/vsmart", "policyId"),
                "policy_definition" : ("template/policy/definition", "definitionId"),
                "policy_list" : ("template/policy/list", "listId"),
                "system_device" : ("system/device/vedges", "uuid")
            }


class CiscoException(Exception):
    pass

class rest_api_lib:
    def __init__(self, vmanage_ip, username, password):
        self.vmanage_ip = vmanage_ip
        self.session = {}
        self.login(self.vmanage_ip, username, password)

    def login(self, vmanage_ip, username, password):
        """Login to vmanage"""
        base_url_str = 'https://%s/'%vmanage_ip

        login_action = '/j_security_check'

        #Format data for loginForm
        login_data = {'j_username' : username, 'j_password' : password}

        #Url for posting login data
        login_url = base_url_str + login_action
        url = base_url_str + login_url

        sess = requests.session()
        #If the vmanage has a certificate signed by a trusted authority change verify to True
        login_response = sess.post(url=login_url, data=login_data, verify=False)


        if b'<html>' in login_response.content:
            print ("Login Failed")
            sys.exit(0)

        self.session[vmanage_ip] = sess

    def get_request(self, mount_point):
        """GET request"""
        url = "https://%s/dataservice/%s"%(self.vmanage_ip, mount_point)
        #print(url)
        if HEADER_VSESSION:
            headers={'VSessionId': str(HEADER_VSESSION)}
            response = self.session[self.vmanage_ip].get(url, headers=headers, verify=False)
        else:
            response = self.session[self.vmanage_ip].get(url, verify=False)

        data = response.content
        return data

    def post_request(self, mount_point, payload, headers={'Content-Type': 'application/json'}):
        """POST request"""
        url = "https://%s/dataservice/%s"%(self.vmanage_ip, mount_point)

        dup_template_msg = "Template with name"
        dup_list_msg = "Duplicate policy list entry"
        dup_policy_msg = "Duplicate policy detected with name"
        dup_vedge_msg = "vEdge policy with name"
        dup_vsmart_msg = "vSmart policy with name"
        dup_token = "Umbrella Token entry already exists"
        version_msg = "Failed to create definition"

        payload = json.dumps(payload)

        if HEADER_VSESSION:
            headers['VSessionId'] = str(HEADER_VSESSION)

        response = self.session[self.vmanage_ip].post(url=url, data=payload, headers=headers, verify=False)
        if response.status_code != 200:
            if (response.status_code == 400):
                response_details = str(response.json()['error']['details'])
                if  (response_details.startswith(dup_template_msg)) or \
                    (response_details.startswith(dup_list_msg)) or \
                    (response_details.startswith(dup_policy_msg)) or \
                    (response_details.startswith(dup_vedge_msg)) or \
                    (response_details.startswith(dup_vsmart_msg)) or \
                    (response_details.startswith(dup_token)) or \
                    (response_details.startswith(version_msg)):
                    return response_details
                else:
                    try:
                        print(response_details)
                    except:
                        print(response)
                    raise CiscoException("Fail - Post")
        try:
            data = response.json()
        except ValueError:
            data = "Successful"

        return data

    def put_request(self, mount_point, payload, headers={'Content-Type': 'application/json'}):
        """PUT request"""
        url = "https://%s/dataservice/%s"%(self.vmanage_ip, mount_point)

        payload = json.dumps(payload)

        if HEADER_VSESSION:
            headers['VSessionId'] = str(HEADER_VSESSION)

        response = self.session[self.vmanage_ip].put(url=url, data=payload, headers=headers, verify=False)
        if response.status_code != 200:
                print(response.json()['error']['details'])
                raise CiscoException("Fail - Put")
        try:
            data = response.json()
        except ValueError:
            data = "Successful"

        return data

    def delete_request(self, mount_point):
        """DELETE request"""
        url = "https://%s/dataservice/%s"%(self.vmanage_ip, mount_point)
        factory_template_msg = "Template is a factory default"
        policy_list_ro_msg = "This policy list is a read only list and it cannot be deleted"

        if HEADER_VSESSION:
            headers={'VSessionId': str(HEADER_VSESSION)}
            response = self.session[self.vmanage_ip].delete(url=url, headers=headers, verify=False)
        else:
            response = self.session[self.vmanage_ip].delete(url=url, verify=False)

        data = response.content

        #print(response.status_code)
        if response.status_code != 200:
            if (response.status_code == 400):
                if (response.json()['error']['details'] == factory_template_msg):
                    return(response.json()['error']['details'])
                elif(response.json()['error']['details'] == policy_list_ro_msg):
                    return(response.json()['error']['details'])
                else:
                    print(response.json()['error']['details'])
                    raise CiscoException("Fail - Delete")
            else:
                print(response)
                raise CiscoException("Fail - Delete")
        if data:
            return data
        else:
            return "Successful"


def get_ids(generic_item):
    mount_point, key_id = ITEM_DIC[generic_item]
    response = json.loads(sdwanp.get_request(mount_point))
    device_data = response['data']
    return [device[key_id] for device in device_data]

def get_policy_definition_ids(mount_point):
    new_mount_point = "template/policy/definition" + str(mount_point)
    response = json.loads(sdwanp.get_request(new_mount_point))
    device_data = response['data']
    return [device["definitionId"] for device in device_data]

def get_policy_list_ids(mount_point):
    new_mount_point = "template/policy/list" + str(mount_point)
    response = json.loads(sdwanp.get_request(new_mount_point))
    device_data = response['data']
    return [device["listId"] for device in device_data]


def load_json_from_file(fp):
    with open(fp) as f:
        return json.load(f, object_pairs_hook=OrderedDict)

def action_print(msg):
    print("Action:")
    print(msg)
    print("")

def wait(minutes):
    print("Waiting {} minutes".format(minutes))
    for i in range(minutes, 0, -1):
        time.sleep(60)
        if i > 1:
            print("Remaining time {} minute/minutes".format(i-1))
    print("")


def export_generic_item(file_path, generic_item, mount_point):
    """Export generic_item

        Data is exported as JSON in a separate folder called configuration.

    """
    print(generic_item)

    json_file = os.path.join(file_path, str(generic_item) + ".json")

    ids_list = get_ids(generic_item)

    export_data = OrderedDict({"configuration": []})

    for id in ids_list:
        print("Exporting ID: {}".format(id))
        new_mount_point = str(mount_point) + "/" + str(id)
        device_data = json.loads(sdwanp.get_request(new_mount_point))
        if device_data:
            export_data["configuration"].append(device_data)

    with open(json_file, 'w') as f:
        json.dump(export_data, f)

def export_generic_policy_ids(file_path, generic_item, mount_point):
    """Export generic_item IDs

        Data is exported as JSON in a separate folder called configuration.

    """
    print(generic_item)

    json_file = os.path.join(file_path, str(generic_item) + ".json")

    export_data = OrderedDict({"configuration": []})

    device_data = json.loads(sdwanp.get_request(mount_point))
    if device_data:
        export_data["configuration"] = device_data

    with open(json_file, 'w') as f:
        json.dump(export_data, f)

def export_policy_definitions(file_path):
    """Export policy definitions

        Data is exported as JSON in a separate folder called configuration.

    """
    print("policy_definition")

    policy_definition_json_file = os.path.join(file_path, "policy_definition.json")

    policy_definition_ids_list = OrderedDict({})

    definition_mount_points =    [
        "/cflowd",
        "/dnssecurity",
        "/advancedMalwareProtection",
        "/control",
        "/intrusionprevention",
        "/vedgeroute",
        "/hubandspoke",
        "/acl",
        "/vpnmembershipgroup",
        "/approute",
        "/approute",
        "/zonebasedfw",
        "/urlfiltering",
        "/qosmap",
        "/aclv6",
        "/mesh",
        "/data",
        "/rewriterule"
                                ]
    for mount_point in definition_mount_points:
        try:
            print("Exporting done for {0}".format(mount_point))
            policy_definition_ids_list[mount_point] = get_policy_definition_ids(mount_point)
        except:
            print("Exporting skipped for {0}, not present".format(mount_point))
    #pprint(policy_definition_ids_list)

    policy_definitions = OrderedDict({"configuration": OrderedDict()})

    for mount_point in definition_mount_points:
        device_data_list = []
        if mount_point in policy_definition_ids_list:
            for id in policy_definition_ids_list[mount_point]:
                print("Exporting ID: {}".format(id))
                new_mount_point = "template/policy/definition" + str(mount_point) + "/" + str(id)
                device_data = json.loads(sdwanp.get_request(new_mount_point))
                if device_data:
                    device_data_list.append(device_data)
            policy_definitions["configuration"][mount_point] = device_data_list

    with open(policy_definition_json_file, 'w') as f:
        json.dump(policy_definitions, f)

def export_policy_lists(file_path):
    """Export policy lists

        Data is exported as JSON in a separate folder called configuration.

    """
    print("policy_list")

    policy_list_json_file = os.path.join(file_path, "policy_list.json")

    policy_list_ids_list = OrderedDict({})


    list_mount_points =    [
      "/community",
      "/localdomain",
      "/dataipv6prefix",
      "/ipv6prefix",
      "/tloc",
      "/aspath",
      "/zone",
      "/color",
      "/sla",
      "/localapp",
      "/app",
      "/mirror",
      "/dataprefix",
      "/extcommunity",
      "/site",
      "/prefix",
      "/umbrelladata",
      "/class",
      "/ipssignature",
#      "/dataprefixall",
      "/urlblacklist",
      "/policer",
      "/urlwhitelist",
      "/vpn"
                            ]
    for mount_point in list_mount_points:
        try:
            print("Exporting done for {0}".format(mount_point))
            policy_list_ids_list[mount_point] = get_policy_list_ids(mount_point)
        except:
            print("Exporting skipped for {0}, not present".format(mount_point))
    #pprint(policy_definition_ids_list)

    policy_lists = OrderedDict({"configuration": OrderedDict()})

    for mount_point in list_mount_points:
        device_data_list = []
        if mount_point in policy_list_ids_list:
            for id in policy_list_ids_list[mount_point]:
                print("Exporting ID: {}".format(id))
                new_mount_point = "template/policy/list" + str(mount_point) + "/" + str(id)
                device_data = json.loads(sdwanp.get_request(new_mount_point))
                if device_data:
                    device_data_list.append(device_data)
            policy_lists["configuration"][mount_point] = device_data_list

    with open(policy_list_json_file, 'w') as f:
        json.dump(policy_lists, f)


def delete_generic_item(generic_item):
    print(generic_item)

    ids_list = get_ids(generic_item)
    mount_point, key_id = ITEM_DIC[generic_item]
    if (generic_item == "system_device"):
        mount_point = "system/device"
    for id in ids_list:
        print("Deleting ID: {} - ".format(id), end="")
        id = urllib.parse.quote(id, safe='')
        new_mount_point = str(mount_point) + "/" + str(id)

        response = sdwanp.delete_request(new_mount_point)
        print(response)
    print("")

def delete_policy_definitions():
    print("policy_definition")

    definition_mount_points =    [
        "/cflowd",
        "/dnssecurity",
        "/advancedMalwareProtection",
        "/control",
        "/intrusionprevention",
        "/vedgeroute",
        "/hubandspoke",
        "/acl",
        "/vpnmembershipgroup",
        "/approute",
        "/approute",
        "/zonebasedfw",
        "/urlfiltering",
        "/qosmap",
        "/aclv6",
        "/mesh",
        "/data",
        "/rewriterule"
                                ]
    for mount_point in definition_mount_points:
        policy_definition_ids_list = get_policy_definition_ids(mount_point)
        for id in policy_definition_ids_list:
            print("Deleting ID: {} - ".format(id), end="")
            new_mount_point = "template/policy/definition" + str(mount_point)+ "/" + str(id)
            response = sdwanp.delete_request(new_mount_point)
            print(response)
    print("")

def delete_policy_lists():
    print("policy_list")

    list_mount_points =    [
      "/community",
      "/localdomain",
      "/dataipv6prefix",
      "/ipv6prefix",
      "/tloc",
      "/aspath",
      "/zone",
      "/color",
      "/sla",
      "/localapp",
      "/app",
      "/mirror",
      "/dataprefix",
      "/extcommunity",
      "/site",
      "/prefix",
      "/umbrelladata",
      "/class",
      "/ipssignature",
#      "/dataprefixall",
      "/urlblacklist",
      "/policer",
      "/urlwhitelist",
      "/vpn"
                            ]
    for mount_point in list_mount_points:
        policy_list_ids_list = get_policy_list_ids(mount_point)
        for id in policy_list_ids_list:
            print("Deleting ID: {} - ".format(id), end="")
            new_mount_point = "template/policy/list" + str(mount_point)+ "/" + str(id)
            response = sdwanp.delete_request(new_mount_point)
            print(response)
    print("")


def device_certificates(validity):
    print("device_certificate")

    mount_point = "certificate/vedge/list"
    response = json.loads(sdwanp.get_request(mount_point))
    device_data = response["data"]
    chassis_serial_list_ids = [(device["chasisNumber"], device["serialNumber"]) for device in device_data]

    for chasisNumber, serialNumber in chassis_serial_list_ids:
        print("{}ating certificate chassis ID:{}... ".format(validity, chasisNumber)),
        mount_point = "certificate/save/vedge/list"
        item = [{"chasisNumber" : chasisNumber, "serialNumber" : serialNumber, "validity" : validity}]
        response = sdwanp.post_request(mount_point, item)
        print (response)
    print("")

def invalidate_certificates():
    """Invalidate device certificates.

        Example command:

             ./sd-wan-exim.py invalidate_certificates

    """

    print("invalidate_certificate")
    device_certificates("invalid")

def validate_certificates():
    """Validate device certificates.

        Example command:

             ./sd-wan-exim.py validate_certificates

    """

    print("validate_certificates")
    device_certificates("valid")

def push_to_controllers():
    """Push configuration to controllers.

        Example command:

             ./sd-wan-exim.py push_to_controllers

    """
    print("push_to_controllers")

    mount_point = "certificate/vedge/list?action=push"
    item = {}
    response = sdwanp.post_request(mount_point, item)
    print("Push to controllers: {}".format(response))
    wait(2)

def detach_devices():
    """Detach devices.

        Example command:

             ./sd-wan-exim.py detach_devices

    """

    print("detach_devices")

    mount_point = "template/device"
    mount_point_attach = "template/config/device/mode/cli"
    response = json.loads(sdwanp.get_request(mount_point))
    device_data = response["data"]
    template_list_ids = [device["templateId"] for device in device_data]

    need_to_wait = False

    for template_id in template_list_ids:
        mount_point = "template/device/config/attached/" + str(template_id)
        response = json.loads(sdwanp.get_request(mount_point))
        attach_data = response["data"]
        if attach_data:
            need_to_wait = True
            for attach in attach_data:
                item = {}
                item["devices"] = []
                if (attach["personality"] == 'vedge'):
                    print(attach["personality"], attach["uuid"], attach["deviceIP"])
                    item["deviceType"] = attach["personality"]
                    item["devices"].append({"deviceId":attach["uuid"],"deviceIP":attach["deviceIP"]})
                    response = sdwanp.post_request(mount_point_attach, item)

    if need_to_wait:
        print("Device vedge templates detached")
        wait(3)
    else:
        print("All device vedge templates are already detached")

    need_to_wait = False

    for template_id in template_list_ids:
        mount_point = "template/device/config/attached/" + str(template_id)
        response = json.loads(sdwanp.get_request(mount_point))
        attach_data = response["data"]
        if attach_data:
            need_to_wait = True
            for attach in attach_data:
                item = {}
                item["devices"] = []
                if (attach["personality"] == 'vsmart'):
                    print(attach["personality"], attach["uuid"], attach["deviceIP"])
                    item["deviceType"] = 'controller'
                    item["devices"].append({"deviceId":attach["uuid"],"deviceIP":attach["deviceIP"]})
                    response = sdwanp.post_request(mount_point_attach, item)

    if need_to_wait:
        print("Device vsmart templates detached")
        wait(2)
    else:
        print("All device vsmart templates are already detached")

def deactivate_generic_policy(mount_point):
    response = json.loads(sdwanp.get_request(mount_point))
    device_data = response['data']
    policy_active_ids = [device["policyId"] for device in device_data if device["isPolicyActivated"] == True]
    need_to_wait = False

    for policy_active_id in policy_active_ids:
        need_to_wait = True
        new_mount_point = mount_point + "/deactivate/" + str(policy_active_id)
        item = {}
        response = sdwanp.post_request(new_mount_point, item)
        print("Deactivated policy:{} - {}".format(policy_active_id, response))

    if need_to_wait:
        print("Policies deactivated")
        wait(2)
    else:
        print("All policies are already deactivated")

def deactivate_policies():
    """Deactivate policies.

        Example command:

             ./sd-wan-exim.py deactivate_policies

    """

    print("deactivate_policies")

    deactivate_generic_policy("template/policy/vsmart")
    #deactivate_generic_policy("template/policy/security")

def check_attached_devices():
    print("check_attached_devices")

    mount_point = "template/device"
    response = json.loads(sdwanp.get_request(mount_point))
    device_data = response["data"]
    template_list_ids = [device["templateId"] for device in device_data]

    for template_id in template_list_ids:
        mount_point = "template/device/config/attached/" + str(template_id)
        response = json.loads(sdwanp.get_request(mount_point))
        attach_data = response["data"]
        if attach_data:
            return True

    return False


def import_feature_templates(file_path):
    print("feature_template")

    feature_template_json_file = os.path.join(file_path, "feature_template.json")
    if not os.path.exists(feature_template_json_file):
        print ("No feature templates")
    feature_data = load_json_from_file(feature_template_json_file)
    feature_template_data = feature_data["configuration"]

    for item in feature_template_data:

        '''
        if "templateDefinition" in item:
            if "vrrp" in item["templateDefinition"]:
                print("ATTENTION: VRRP SKIPPED - Featute Template imported and VRRP set to Empty")
                item["templateDefinition"]["vrrp"] = {}
        '''

        mount_point = "template/feature/"
        print("Feature template: Importing {0} - ".format(item["templateName"]), end="")
        response = sdwanp.post_request(mount_point, item)
        print("Done, {0}".format(response))

    """ Update Feature IDs """
    feature_template_id_old = OrderedDict()
    for item in feature_template_data:
        feature_template_id_old[item['templateId']] = item['templateName']

    feature_template_id_new = OrderedDict()
    response = json.loads(sdwanp.get_request('template/feature'))
    feature_template_data = response['data']
    for feature_template_temp in feature_template_data:
        feature_template_id_new[feature_template_temp['templateName']] = feature_template_temp['templateId']

    print("")

    return (feature_template_id_old, feature_template_id_new)

def import_device_templates(file_path, all_template_ids, all_policy_ids = ([],[],[],[])):
    print("device_template")

    f_t_old, f_t_new = all_template_ids
    ve_t_old, ve_t_new, vs_t_old, vs_t_new = all_policy_ids
    device_template_json_file = os.path.join(file_path, "device_template.json")
    if not os.path.exists(device_template_json_file):
        print ("No device templates")
    device_template = load_json_from_file(device_template_json_file)
    device_template_data = device_template["configuration"]

    for item in device_template_data:
        if "configType" in item:
            if item["configType"] == "template":
                mount_point = "template/device/feature"

                item["featureTemplateUidRange"] = []
                try:
                    del item["templateId"]
                except:
                    pass

                """ Update policy IDs """
                if "policyId" in item:
                    if item["policyId"] in ve_t_old:
                        old_aux = ve_t_old[item["policyId"]]
                        new_aux = ve_t_new[old_aux]
                        item["policyId"] = new_aux
                    elif item["policyId"] in vs_t_old:
                        old_aux = vs_t_old[item["policyId"]]
                        new_aux = vs_t_new[old_aux]
                        item["policyId"] = new_aux
                    else:
                        item["policyId"] = ""
                else:
                    item["policyId"] = ""

                """ Update security policy IDs """
                if "securityPolicyId" in item:
                    if item["securityPolicyId"] in ve_t_old:
                        old_aux = ve_t_old[item["securityPolicyId"]]
                        new_aux = ve_t_new[old_aux]
                        item["securityPolicyId"] = new_aux
                    elif item["securityPolicyId"] in vs_t_old:
                        old_aux = vs_t_old[item["securityPolicyId"]]
                        new_aux = vs_t_new[old_aux]
                        item["securityPolicyId"] = new_aux
                    else:
                        item["securityPolicyId"] = ""
                else:
                    item["securityPolicyId"] = ""

                """ Update generalTemplates IDs """
                if "generalTemplates" in item:
                    for i in range(0, len(item["generalTemplates"])):
                        template_id = item["generalTemplates"][i]["templateId"]
                        old_aux = f_t_old[template_id]
                        new_aux = f_t_new[old_aux]
                        item["generalTemplates"][i]["templateId"] = new_aux

                        """ Update subtemplates generalTemplates IDs """
                        if "subTemplates" in item["generalTemplates"][i]:
                            for j in range(0, len(item["generalTemplates"][i]["subTemplates"])):
                                subtemplate_id = item["generalTemplates"][i]["subTemplates"][j]["templateId"]
                                old_aux = f_t_old[subtemplate_id]
                                new_aux = f_t_new[old_aux]
                                item["generalTemplates"][i]["subTemplates"][j]["templateId"] = new_aux

                                """ Update subsubtemplates generalTemplates IDs """
                                if "subTemplates" in item["generalTemplates"][i]["subTemplates"][j]:
                                    for k in range(0, len(item["generalTemplates"][i]["subTemplates"][j]["subTemplates"])):
                                        subsubtemple_id = item["generalTemplates"][i]["subTemplates"][j]["subTemplates"][k]["templateId"]
                                        old_aux = f_t_old[subsubtemple_id]
                                        new_aux = f_t_new[old_aux]
                                        item["generalTemplates"][i]["subTemplates"][j]["subTemplates"][k]["templateId"] = new_aux

                print("Device template: Importing {0} - ".format(item["templateName"]), end="")
                response = sdwanp.post_request(mount_point, item)
                print("Done, {0}".format(response))
            elif item["configType"] == "file":
                try:
                    del item["templateId"]
                    del item["feature"]
                    del item["lastUpdatedBy"]
                    del item["lastUpdatedOn"]
                    del item["createdOn"]
                    del item["createdBy"]
                    del item["@rid"]
                except:
                    pass
                mount_point = "template/device/cli"
                print("Device template: Importing {0} - ".format(item["templateName"]), end="")
                response = sdwanp.post_request(mount_point, item)
                print("Done, {0}".format(response))
            else:
                print("Device template: {0} is not a template, acutal configType is {1}".format(item["templateName"], item["configType"]))
    print("")

def import_policy_lists(file_path):
    print("policy_list")

    policy_list_json_file = os.path.join(file_path, "policy_list.json")
    if not os.path.exists(policy_list_json_file):
        print ("No policy list")
    policy_list = load_json_from_file(policy_list_json_file)
    policy_list_data = policy_list["configuration"]

    for list in policy_list_data:
        mount_point = "template/policy/list" + str(list)
        #print(mount_point)
        for item in policy_list_data[list]:
            print("Policy list: Importing {0} {1} - ".format(list, item["name"]), end="")
            response = sdwanp.post_request(mount_point, item)
            print("Done, {0}".format(response))
    print("")


    list_mount_points =    [
      "/community",
      "/localdomain",
      "/dataipv6prefix",
      "/ipv6prefix",
      "/tloc",
      "/aspath",
      "/zone",
      "/color",
      "/sla",
      "/localapp",
      "/app",
      "/mirror",
      "/dataprefix",
      "/extcommunity",
      "/site",
      "/prefix",
      "/umbrelladata",
      "/class",
      "/ipssignature",
#      "/dataprefixall",
      "/urlblacklist",
      "/policer",
      "/urlwhitelist",
      "/vpn"
                            ]


    """ Update List IDs """
    policy_list_id_old = OrderedDict()
    for list in policy_list_data:
        for item in policy_list_data[list]:
            composed_name = str(list) + "/" + str(item['name'])
            policy_list_id_old[item['listId']] = composed_name
    #pprint(policy_list_id_old)

    policy_list_id_new = OrderedDict()
    for mount_point in list_mount_points:
        response = json.loads(sdwanp.get_request('template/policy/list' + str(mount_point)))
        policy_list_data = response['data']
        for policy_list_temp in policy_list_data:
            policy_list_id_new[str(mount_point) + "/" + str(policy_list_temp['name'])] = policy_list_temp['listId']
    #pprint(policy_list_id_new)

    return (policy_list_id_old, policy_list_id_new)

def import_policy_definitions(file_path, all_list_ids):
    print("policy_definition")

    policy_list_id_old, policy_list_id_new = all_list_ids
    policy_definition_json_file = os.path.join(file_path, "policy_definition.json")
    if not os.path.exists(policy_definition_json_file):
        print ("No policy definition")
    policy_definition = load_json_from_file(policy_definition_json_file)
    policy_definition_data = policy_definition["configuration"]

    for definition in policy_definition_data:
        mount_point = "template/policy/definition" + str(definition)
        #print(mount_point)
        for item in policy_definition_data[definition]:
            if definition == "/cflowd":
                pass
                #"Cflowd ID - Standard"
                '''
                if "references" in item:
                    for i in range(0, len(item["references"])):
                        if "id" in item["references"][i]:
                            ref_id = item["references"][i]["id"]
                            old_aux_list = policy_list_id_old[ref_id]
                            new_aux_list = policy_list_id_new[old_aux_list]
                            item["references"][i]["id"] = new_aux_list
                '''

            elif definition == "/control":
                #"Control ID - Standard"
                if "sequences" in item:
                    for i in range(0, len(item["sequences"])):
                        if "match" in item["sequences"][i]:
                            if "entries" in item["sequences"][i]["match"]:
                                for j in range (0, len(item["sequences"][i]["match"]["entries"])):
                                    if "ref" in item["sequences"][i]["match"]["entries"][j]:
                                        ref_id = item["sequences"][i]["match"]["entries"][j]["ref"]
                                        old_aux_list = policy_list_id_old[ref_id]
                                        new_aux_list = policy_list_id_new[old_aux_list]
                                        item["sequences"][i]["match"]["entries"][j]["ref"] = new_aux_list
                        if "actions" in item["sequences"][i]:
                                for j in range (0, len(item["sequences"][i]["actions"])):
                                    if "parameter" in item["sequences"][i]["actions"][j]:
                                        if isinstance(item["sequences"][i]["actions"][j]["parameter"], list):
                                            for k in range (0, len(item["sequences"][i]["actions"][j]["parameter"])):
                                                if "ref" in item["sequences"][i]["actions"][j]["parameter"][k]:
                                                    ref_id = item["sequences"][i]["actions"][j]["parameter"][k]["ref"]
                                                    old_aux_list = policy_list_id_old[ref_id]
                                                    new_aux_list = policy_list_id_new[old_aux_list]
                                                    item["sequences"][i]["actions"][j]["parameter"][k]["ref"] = new_aux_list
                                        else:
                                            if "ref" in item["sequences"][i]["actions"][j]["parameter"]:
                                                ref_id = item["sequences"][i]["actions"][j]["parameter"]["ref"]
                                                old_aux_list = policy_list_id_old[ref_id]
                                                new_aux_list = policy_list_id_new[old_aux_list]
                                                item["sequences"][i]["actions"][j]["parameter"]["ref"] = new_aux_list
            elif definition == "/acl":
                #" Update ACL Id "
                if "sequences" in item:
                    for i in range(0, len(item["sequences"])):
                        if "actions" in item["sequences"][i]:
                            for j in range (0, len(item["sequences"][i]["actions"])):
                                if "parameter" in item["sequences"][i]["actions"][j]:
                                    if "ref" in item["sequences"][i]["actions"][j]["parameter"]:
                                        ref_id = item["sequences"][i]["actions"][j]["parameter"]["ref"]
                                        old_aux_list = policy_list_id_old[ref_id]
                                        new_aux_list = policy_list_id_new[old_aux_list]
                                        item["sequences"][i]["actions"][j]["parameter"]["ref"] = new_aux_list
            elif definition == "/zonebasedfw":
                #print("ATTENTION: DEFINITION SKIPPED - {0}".format(item))
                #continue

                if "definition" in item:
                    if "sequences" in item["definition"]:
                        for i in range(0, len(item["definition"]["sequences"])):
                            if "match" in item["definition"]["sequences"][i]:
                                if "entries" in item["definition"]["sequences"][i]["match"]:
                                    for j in range (0, len(item["definition"]["sequences"][i]["match"]["entries"])):
                                        if "ref" in item["definition"]["sequences"][i]["match"]["entries"][j]:
                                            ref_id = item["definition"]["sequences"][i]["match"]["entries"][j]["ref"]
                                            old_aux_list = policy_list_id_old[ref_id]
                                            new_aux_list = policy_list_id_new[old_aux_list]
                                            item["definition"]["sequences"][i]["match"]["entries"][j]["ref"] = new_aux_list
                            if "actions" in item["definition"]["sequences"][i]:
                                    for j in range (0, len(item["definition"]["sequences"][i]["actions"])):
                                        if "parameter" in item["definition"]["sequences"][i]["actions"][j]:
                                            if isinstance(item["definition"]["sequences"][i]["actions"][j]["parameter"], list):
                                                for k in range (0, len(item["definition"]["sequences"][i]["actions"][j]["parameter"])):
                                                    if "ref" in item["definition"]["sequences"][i]["actions"][j]["parameter"][k]:
                                                        ref_id = item["definition"]["sequences"][i]["actions"][j]["parameter"][k]["ref"]
                                                        old_aux_list = policy_list_id_old[ref_id]
                                                        new_aux_list = policy_list_id_new[old_aux_list]
                                                        item["definition"]["sequences"][i]["actions"][j]["parameter"][k]["ref"] = new_aux_list
                                            else:
                                                if "ref" in item["definition"]["sequences"][i]["actions"][j]["parameter"]:
                                                    ref_id = item["definition"]["sequences"][i]["actions"][j]["parameter"]["ref"]
                                                    old_aux_list = policy_list_id_old[ref_id]
                                                    new_aux_list = policy_list_id_new[old_aux_list]
                                                    item["definition"]["sequences"][i]["actions"][j]["parameter"]["ref"] = new_aux_list

                    if "entries" in item["definition"]:
                        for i in range(0, len(item["definition"]["entries"])):
                            if "sourceZone" in item["definition"]["entries"][i]:
                                aux_list_id = item["definition"]["entries"][i]["sourceZone"]
                                old_aux_list = policy_list_id_old[aux_list_id]
                                new_aux_list = policy_list_id_new[old_aux_list]
                                item["definition"]["entries"][i]["sourceZone"] = new_aux_list
                            if "destinationZone" in item["definition"]["entries"][i]:
                                aux_list_id = item["definition"]["entries"][i]["destinationZone"]
                                old_aux_list = policy_list_id_old[aux_list_id]
                                new_aux_list = policy_list_id_new[old_aux_list]
                                item["definition"]["entries"][i]["destinationZone"] = new_aux_list
            elif definition == "/qosmap":
                if "definition" in item:
                    if "qosSchedulers" in item["definition"]:
                        for i in range(0, len(item["definition"]["qosSchedulers"])):
                            if "classMapRef" in item["definition"]["qosSchedulers"][i]:
                                if item["definition"]["qosSchedulers"][i]["classMapRef"]:
                                    ref_id = item["definition"]["qosSchedulers"][i]["classMapRef"]
                                    old_aux_list = policy_list_id_old[ref_id]
                                    new_aux_list = policy_list_id_new[old_aux_list]
                                    item["definition"]["qosSchedulers"][i]["classMapRef"] = new_aux_list
            elif definition == "/aclv6":
                print("ATTENTION: DEFINITION ID UPDATE NOT IMPLEMENTED - {0} - {1}".format(definition, item))
            elif definition == "/data":
                #" Update Data Id "
                if "sequences" in item:
                    for i in range(0, len(item["sequences"])):
                        if "match" in item["sequences"][i]:
                            for j in range (0, len(item["sequences"][i]["match"]["entries"])):
                                if "ref" in item["sequences"][i]["match"]["entries"][j]:
                                    ref_id = item["sequences"][i]["match"]["entries"][j]["ref"]
                                    old_aux_list = policy_list_id_old[ref_id]
                                    new_aux_list = policy_list_id_new[old_aux_list]
                                    item["sequences"][i]["match"]["entries"][j]["ref"] = new_aux_list

                        if "actions" in item["sequences"][i]:
                            for j in range (0, len(item["sequences"][i]["actions"])):
                                if "parameter" in item["sequences"][i]["actions"][j]:
                                    if isinstance(item["sequences"][i]["actions"][j]["parameter"], list):
                                        for k in range (0, len(item["sequences"][i]["actions"][j]["parameter"])):
                                            if "ref" in item["sequences"][i]["actions"][j]["parameter"][k]:
                                                ref_id = item["sequences"][i]["actions"][j]["parameter"][k]["ref"]
                                                old_aux_list = policy_list_id_old[ref_id]
                                                new_aux_list = policy_list_id_new[old_aux_list]
                                                item["sequences"][i]["actions"][j]["parameter"][k]["ref"] = new_aux_list
                                            if "value" in item["sequences"][i]["actions"][j]["parameter"][k]:
                                                if "tlocList" in item["sequences"][i]["actions"][j]["parameter"][k]["value"]:
                                                    if "ref" in item["sequences"][i]["actions"][j]["parameter"][k]["value"]["tlocList"]:
                                                        ref_id = item["sequences"][i]["actions"][j]["parameter"][k]["value"]["tlocList"]["ref"]
                                                        old_aux_list = policy_list_id_old[ref_id]
                                                        new_aux_list = policy_list_id_new[old_aux_list]
                                                        item["sequences"][i]["actions"][j]["parameter"][k]["value"]["tlocList"]["ref"] = new_aux_list
                                    else:
                                        if "ref" in item["sequences"][i]["actions"][j]["parameter"]:
                                            ref_id = item["sequences"][i]["actions"][j]["parameter"]["ref"]
                                            old_aux_list = policy_list_id_old[ref_id]
                                            new_aux_list = policy_list_id_new[old_aux_list]
                                            item["sequences"][i]["actions"][j]["parameter"]["ref"] = new_aux_list
            elif definition == "/rewriterule":
                print("ATTENTION: DEFINITION ID UPDATE NOT IMPLEMENTED - {0} - {1}".format(definition, item))
            elif definition == "/vedgeroute":
                #" Update List Id "
                for i in range(0, len(item["sequences"])):
                    for j in range (0, len(item["sequences"][i]["match"]["entries"])):
                        #pprint(item["sequences"][i]["match"]["entries"][j]["ref"])
                        if "ref" in item["sequences"][i]["match"]["entries"][j]:
                            ref_id = item["sequences"][i]["match"]["entries"][j]["ref"]
                            old_aux_list = policy_list_id_old[ref_id]
                            new_aux_list = policy_list_id_new[old_aux_list]
                            item["sequences"][i]["match"]["entries"][j]["ref"] = new_aux_list
            elif definition == "/hubandspoke":
                #" Update Hub and Spoke Id - Standard"
                if "definition" in item:
                    if "vpnList" in item["definition"]:
                        vpn_list_id = item["definition"]['vpnList']
                        old_aux_list = policy_list_id_old[vpn_list_id]
                        new_aux_list = policy_list_id_new[old_aux_list]
                        item["definition"]["vpnList"] = new_aux_list

                    if "subDefinitions" in item["definition"]:
                        for i in range(0, len(item["definition"]["subDefinitions"])):
                            if "tlocList" in item["definition"]["subDefinitions"][i]:
                                aux_list_id = item["definition"]["subDefinitions"][i]["tlocList"]
                                old_aux_list = policy_list_id_old[aux_list_id]
                                new_aux_list = policy_list_id_new[old_aux_list]
                                item["definition"]["subDefinitions"][i]["tlocList"] = new_aux_list

                            if "spokes" in item["definition"]["subDefinitions"][i]:
                                for j in range(0, len(item["definition"]["subDefinitions"][i]["spokes"])):
                                    if "siteList" in item["definition"]["subDefinitions"][i]["spokes"][j]:
                                        site_list_id = item["definition"]["subDefinitions"][i]["spokes"][j]["siteList"]
                                        old_aux_list = policy_list_id_old[site_list_id]
                                        new_aux_list = policy_list_id_new[old_aux_list]
                                        item["definition"]["subDefinitions"][i]["spokes"][j]["siteList"] = new_aux_list

                                    if "hubs" in item["definition"]["subDefinitions"][i]["spokes"][j]:
                                        for k in range(0, len(item["definition"]["subDefinitions"][i]["spokes"][j]["hubs"])):
                                            if "siteList" in item["definition"]["subDefinitions"][i]["spokes"][j]["hubs"][k]:
                                                site_list_id = item["definition"]["subDefinitions"][i]["spokes"][j]["hubs"][k]["siteList"]
                                                old_aux_list = policy_list_id_old[site_list_id]
                                                new_aux_list = policy_list_id_new[old_aux_list]
                                                item["definition"]["subDefinitions"][i]["spokes"][j]["hubs"][k]["siteList"] = new_aux_list

                                            if "prefixLists" in item["definition"]["subDefinitions"][i]["spokes"][j]["hubs"][k]:
                                                for l in range(0, len(item["definition"]["subDefinitions"][i]["spokes"][j]["hubs"][k]["prefixLists"])):
                                                    aux_list_id = item["definition"]["subDefinitions"][i]["spokes"][j]["hubs"][k]["prefixLists"][l]
                                                    old_aux_list = policy_list_id_old[aux_list_id]
                                                    new_aux_list = policy_list_id_new[old_aux_list]
                                                    item["definition"]["subDefinitions"][i]["spokes"][j]["hubs"][k]["prefixLists"][l] = new_aux_list
            elif definition == "/vpnmembershipgroup":
                for i in range(0, len(item["definition"]["sites"])):
                    site_list_id = item["definition"]["sites"][i]["siteList"]
                    old_aux_list = policy_list_id_old[site_list_id]
                    new_aux_list = policy_list_id_new[old_aux_list]
                    item["definition"]["sites"][i]["siteList"] = new_aux_list
                    for j in range(0, len(item["definition"]["sites"][i]["vpnList"])):
                        vpn_list_id  = item["definition"]["sites"][i]["vpnList"][j]
                        old_aux_list = policy_list_id_old[vpn_list_id]
                        new_aux_list = policy_list_id_new[old_aux_list]
                        item["definition"]["sites"][i]["vpnList"][j] = new_aux_list
            elif definition == "/approute":
                #" Update ACL Id "
                if "defaultAction" in item:
                    if "ref" in item["defaultAction"]:
                        ref_id = item["defaultAction"]["ref"]
                        old_aux_list = policy_list_id_old[ref_id]
                        new_aux_list = policy_list_id_new[old_aux_list]
                        item["defaultAction"]["ref"] = new_aux_list

                if "sequences" in item:
                    for i in range(0, len(item["sequences"])):
                        if "match" in item["sequences"][i]:
                            for j in range (0, len(item["sequences"][i]["match"]["entries"])):
                                if "ref" in item["sequences"][i]["match"]["entries"][j]:
                                    ref_id = item["sequences"][i]["match"]["entries"][j]["ref"]
                                    old_aux_list = policy_list_id_old[ref_id]
                                    new_aux_list = policy_list_id_new[old_aux_list]
                                    item["sequences"][i]["match"]["entries"][j]["ref"] = new_aux_list

                        if "actions" in item["sequences"][i]:
                            for j in range (0, len(item["sequences"][i]["actions"])):
                                if "parameter" in item["sequences"][i]["actions"][j]:
                                    for k in range (0, len(item["sequences"][i]["actions"][j]["parameter"])):
                                        if "ref" in item["sequences"][i]["actions"][j]["parameter"][k]:
                                            ref_id = item["sequences"][i]["actions"][j]["parameter"][k]["ref"]
                                            old_aux_list = policy_list_id_old[ref_id]
                                            new_aux_list = policy_list_id_new[old_aux_list]
                                            item["sequences"][i]["actions"][j]["parameter"][k]["ref"] = new_aux_list

                '''
                for i in range(0, len(item["sequences"])):
                    for j in range(0, len(item["sequences"][i]["actions"])):
                        for k in range(0, len(item["sequences"][i]["actions"][j]["parameter"])):
                            if "ref" in item["sequences"][i]["actions"][j]["parameter"][k]:
                                ref_id = item["sequences"][i]["actions"][j]["parameter"][k]["ref"]
                                old_aux_list = policy_list_id_old[ref_id]
                                new_aux_list = policy_list_id_new[old_aux_list]
                                item["sequences"][i]["actions"][j]["parameter"][k]["ref"] = new_aux_list
                '''
            elif definition == "/mesh":
                vpn_list_id = item["definition"]['vpnList']
                old_aux_list = policy_list_id_old[vpn_list_id]
                new_aux_list = policy_list_id_new[old_aux_list]
                item["definition"]["vpnList"] = new_aux_list
                for i in range(0, len(item["definition"]["regions"])):
                    if "siteLists" in item["definition"]["regions"][i]:
                        for j in range(0, len(item["definition"]["regions"][i]["siteLists"])):
                            site_list_id = item["definition"]["regions"][i]["siteLists"][j]
                            old_aux_list = policy_list_id_old[site_list_id]
                            new_aux_list = policy_list_id_new[old_aux_list]
                            item["definition"]["regions"][i]["siteLists"][j] = new_aux_list
            else:
                print("ATTENTION: DEFINITION NOT IMPLEMENTED - {0} - {1}".format(definition, item))
                continue

            print("Policy definition: Importing {0} {1} - ".format(definition, item["name"]), end="")
            response = sdwanp.post_request(mount_point, item)
            print("Done, {0}".format(response))
    print("")


    definition_mount_points =   [
        "/cflowd",
        "/dnssecurity",
        "/advancedMalwareProtection",
        "/control",
        "/intrusionprevention",
        "/vedgeroute",
        "/hubandspoke",
        "/acl",
        "/vpnmembershipgroup",
        "/approute",
        "/approute",
        "/zonebasedfw",
        "/urlfiltering",
        "/qosmap",
        "/aclv6",
        "/mesh",
        "/data",
        "/rewriterule"
                                ]


    """ Update Definition IDs """
    policy_definition_id_old = OrderedDict()
    for definition in policy_definition_data:
        for item in policy_definition_data[definition]:
            composed_name = str(definition) + "/" + str(item['name'])
            policy_definition_id_old[item['definitionId']] = composed_name
    #pprint(policy_list_id_old)

    policy_definition_id_new = OrderedDict()
    for mount_point in definition_mount_points:
        response = json.loads(sdwanp.get_request('template/policy/definition' + str(mount_point)))
        policy_definition_data = response['data']
        for policy_definition_temp in policy_definition_data:
            policy_definition_id_new[str(mount_point) + "/" + str(policy_definition_temp['name'])] = policy_definition_temp['definitionId']
    #pprint(policy_list_id_new)
    return (policy_definition_id_old, policy_definition_id_new)

def import_vedge_policies(file_path, all_list_ids, all_definition_ids):
    print("vedge_policy")

    policy_list_id_old, policy_list_id_new = all_list_ids
    policy_definition_id_old, policy_definition_id_new = all_definition_ids
    vedge_policy_json_file = os.path.join(file_path, "vedge_policy.json")
    vedge_policy_id_json_file = os.path.join(file_path, "vedge_policy_id.json")
    if not os.path.exists(vedge_policy_json_file):
        print ("No vedge policy")
    vedge_policy = load_json_from_file(vedge_policy_json_file)
    vedge_policy_data = vedge_policy["configuration"]

    for item in vedge_policy_data:
        if "policyType" in item:
            if item["policyType"] == "feature":
                mount_point = "template/policy/vedge/"
                for i in range(0, len(item["policyDefinition"]["assembly"])):
                    def_id = item["policyDefinition"]["assembly"][i]["definitionId"]
                    old_aux_list = policy_definition_id_old[def_id]
                    new_aux_list = policy_definition_id_new[old_aux_list]
                    item["policyDefinition"]["assembly"][i]["definitionId"] = new_aux_list
                print("vEdge Policy: Importing {0} - ".format(item["policyName"]), end="")
                response = sdwanp.post_request(mount_point, item)
                print("Done, {0}".format(response))
            elif item["policyType"] == "cli":
                mount_point = "template/policy/vedge/"
                print("vEdge Policy: Importing {0} - ".format(item["policyName"]), end="")
                response = sdwanp.post_request(mount_point, item)
                print("Done, {0}".format(response))
            else:
                print("vEdge Policy: {0} is not a policy, acutal policyType is {1}".format(item["policyName"], item["policyType"]))
    print("")


    """ Update vEdge Policy IDs """
    vedge_policy_id_old = OrderedDict()
    vedge_policy_id = load_json_from_file(vedge_policy_id_json_file)
    vedge_policy_id_data = vedge_policy_id["configuration"]["data"]
    for item in vedge_policy_id_data:
        vedge_policy_id_old[item['policyId']] = item['policyName']
    #pprint(vedge_policy_id_old)

    vedge_policy_id_new = OrderedDict()
    response = json.loads(sdwanp.get_request('template/policy/vedge'))
    vedge_policy_id_data = response['data']
    for vedge_policy_id_temp in vedge_policy_id_data:
        vedge_policy_id_new[vedge_policy_id_temp['policyName']] = vedge_policy_id_temp['policyId']
    #pprint(vedge_policy_id_new)

    return (vedge_policy_id_old, vedge_policy_id_new)

def import_vsmart_policies(file_path, all_list_ids, all_definition_ids):
    print("vsmart_policy")

    policy_list_id_old, policy_list_id_new = all_list_ids
    policy_definition_id_old, policy_definition_id_new = all_definition_ids
    vsmart_policy_json_file = os.path.join(file_path, "vsmart_policy.json")
    vsmart_policy_id_json_file = os.path.join(file_path, "vsmart_policy_id.json")
    if not os.path.exists(vsmart_policy_json_file):
        print ("No vsmart policy")
    vedge_policy = load_json_from_file(vsmart_policy_json_file)
    vsmart_policy_data = vedge_policy["configuration"]

    for item in vsmart_policy_data:
        if "policyType" in item:
            if item["policyType"] == "feature":
                mount_point = "template/policy/vsmart/"
                for i in range(0, len(item["policyDefinition"]["assembly"])):
                    def_id = item["policyDefinition"]["assembly"][i]["definitionId"]
                    old_aux_list = policy_definition_id_old[def_id]
                    new_aux_list = policy_definition_id_new[old_aux_list]
                    item["policyDefinition"]["assembly"][i]["definitionId"] = new_aux_list
                    if "entries" in item["policyDefinition"]["assembly"][i]:
                        for j in range(0, len(item["policyDefinition"]["assembly"][i]["entries"])):
                            if "siteLists" in item["policyDefinition"]["assembly"][i]["entries"][j]:
                                for k in range (0, len(item["policyDefinition"]["assembly"][i]["entries"][j]["siteLists"])):
                                    site_list = item["policyDefinition"]["assembly"][i]["entries"][j]["siteLists"][k]
                                    old_aux_list = policy_list_id_old[site_list]
                                    new_aux_list = policy_list_id_new[old_aux_list]
                                    item["policyDefinition"]["assembly"][i]["entries"][j]["siteLists"][k] = new_aux_list
                            if "vpnLists" in item["policyDefinition"]["assembly"][i]["entries"][j]:
                                for k in range (0, len(item["policyDefinition"]["assembly"][i]["entries"][j]["vpnLists"])):
                                    vpn_list = item["policyDefinition"]["assembly"][i]["entries"][j]["vpnLists"][k]
                                    old_aux_list = policy_list_id_old[vpn_list]
                                    new_aux_list = policy_list_id_new[old_aux_list]
                                    item["policyDefinition"]["assembly"][i]["entries"][j]["vpnLists"][k] = new_aux_list
                print("vSmart Policy: Importing {0}  -  ".format(item["policyName"]),  end="")
                response = sdwanp.post_request(mount_point, item)
                print("Done, {0}".format(response))
            elif item["policyType"] == "cli":
                mount_point = "template/policy/vsmart/"
                print("vSmart Policy: Importing {0} - ".format(item["policyName"]), end="")
                response = sdwanp.post_request(mount_point, item)
                print("Done, {0}".format(response))
            else:
                print("vSmart Policy: {0} is not a policy, acutal policyType is {1}".format(item["policyName"], item["policyType"]))
    print("")


    """ =============Update vSmart Policy IDs============= """
    vsmart_policy_id_old = OrderedDict()
    vedge_policy_id = load_json_from_file(vsmart_policy_id_json_file)
    vsmart_policy_id_data = vedge_policy_id["configuration"]["data"]
    for item in vsmart_policy_id_data:
        vsmart_policy_id_old[item['policyId']] = item['policyName']
    #pprint(vsmart_policy_id_old)

    vsmart_policy_id_new = OrderedDict()
    response = json.loads(sdwanp.get_request('template/policy/vsmart'))
    vsmart_policy_id_data = response['data']
    for vsmart_policy_id_temp in vsmart_policy_id_data:
        vsmart_policy_id_new[vsmart_policy_id_temp['policyName']] = vsmart_policy_id_temp['policyId']
    #pprint(vsmart_policy_id_new)

    return (vsmart_policy_id_old, vsmart_policy_id_new)

def import_security_policies(file_path, all_list_ids, all_definition_ids):
    pass


def export(archive_path):
    """Export
            - device templates
            - feature templates
            - vEdge policies
            - vSmart policies
            - policy definitions
            - policy lists

        Data is exported as JSON in a separate folder called configuration.

        Example command:

            ./sd-wan-exim.py export

    """

    file_path = os.path.join(DIR_PATH, "configuration")
    if os.path.exists(file_path):
        shutil.rmtree(file_path)
    os.makedirs(file_path)

    export_generic_item(file_path, "device_template", "template/device/object")
    print("Successfully exported the device templates from %s"%(SDWAN_IP))
    print("")

    export_generic_item(file_path, "feature_template", "template/feature/object")
    print("Successfully exported the feature templates from %s"%(SDWAN_IP))
    print("")

    export_generic_item(file_path, "vedge_policy", "template/policy/vedge/definition")
    print("Successfully exported the vEdge policies from %s"%(SDWAN_IP))
    print("")

    export_generic_item(file_path, "vsmart_policy", "template/policy/vsmart/definition")
    print("Successfully exported the vSmart policies from %s"%(SDWAN_IP))
    print("")

    export_generic_policy_ids(file_path, "vedge_policy_id", "template/policy/vedge")
    print("Successfully exported the vEdge policy IDs from %s"%(SDWAN_IP))
    print("")

    export_generic_policy_ids(file_path, "vsmart_policy_id", "template/policy/vsmart")
    print("Successfully exported the vSmart policy IDs from %s"%(SDWAN_IP))
    print("")

    export_policy_definitions(file_path)
    print("Successfully exported the policy definitions from %s"%(SDWAN_IP))
    print("")

    export_policy_lists(file_path)
    print("Successfully exported the policy lists from %s"%(SDWAN_IP))
    print("")

    print("Successfully exported the configuration from %s"%(SDWAN_IP))

    tar = tarfile.open(archive_path, "w:gz")
    for file_name in glob.glob(os.path.join(file_path, "*")):
        tar.add(file_name, os.path.basename(file_name))
    tar.close()
    shutil.rmtree(file_path)


def clean_templates():
    """Delete device and feature templates.

        PREREQUISIT: DEVICE TEMPLATES MUST BE DETACHED.

        Example command:

            ./sd-wan-exim.py clean_templates

    """
    if check_attached_devices():
        ask = input("ATTENTION: There are device configurations attached. Are you sure you want to continue? (yes/no)\n")
        if (ask.lower() != "yes"):
            sys.exit("Action stopped - clean templates")

    delete_generic_item("device_template")
    delete_generic_item("feature_template")

def clean_policies():
    """Delete policies, definitions and lists.

        Example command:

            ./sd-wan-exim.py clean_policies

    """
    if check_attached_devices():
        ask = input("ATTENTION: There are device configurations attached. Are you sure you want to continue? (yes/no)\n")
        if (ask.lower() != "yes"):
            sys.exit("Action stopped - clean policies")

    delete_generic_item("vedge_policy")
    delete_generic_item("vsmart_policy")
    #delete_generic_item("security_policy")
    delete_policy_definitions()
    delete_policy_lists()

def clean_devices():
    """Invalidate certificates and delete system devices.

        Example command:

            ./sd-wan-exim.py clean_devices

    """
    if check_attached_devices():
        ask = input("ATTENTION: There are device configurations attached. Are you sure you want to continue? (yes/no)\n")
        if (ask.lower() != "yes"):
            sys.exit("Action stopped - clean devices")

    deactivate_policies()
    detach_devices()
    invalidate_certificates()
    push_to_controllers()
    delete_generic_item("system_device")

def clean():
    """Delete templates and policies configuration.

        PREREQUISIT: DEVICE TEMPLATES MUST BE DETACHED.

        Example command:

            ./sd-wan-exim.py clean

    """
    if check_attached_devices():
        ask = input("ATTENTION: There are device configurations attached. Are you sure you want to continue? (yes/no)\n")
        if (ask.lower() != "yes"):
            sys.exit("Action stopped - clean")

    delete_generic_item("device_template")
    delete_generic_item("feature_template")
    delete_generic_item("vedge_policy")
    delete_generic_item("vsmart_policy")
    delete_policy_definitions()
    delete_policy_lists()


def configure_templates(archive_path):
    """Import feature and device templates.

        Example command:

             ./sd-wan-exim.py configure_templates

    """

    #archive_path = os.path.join(DIR_PATH, CONFIG_ARCH)
    try:
        tar = tarfile.open(archive_path)
    except EnvironmentError: # parent of IOError, OSError
        raise CiscoException("File {} not found or with errors!".format(archive_path))

    file_path = os.path.join(os.getcwd(), "configuration")
    if os.path.exists(file_path):
        shutil.rmtree(file_path)
    os.makedirs(file_path)
    tar.extractall(path=file_path)
    tar.close()

    all_template_ids = import_feature_templates(file_path)
    import_device_templates(file_path, all_template_ids)

    shutil.rmtree(file_path)
    print("Successfully imported the templates to %s"%(SDWAN_IP))
    print("")

def configure_policies(archive_path):
    """Import vEdge/Vsmart policies, definitions and lists.

        TO DO: Update site ids in definitions and
               Add security policies

        Example command:

             ./sd-wan-exim.py configure_policies

    """

    #archive_path = os.path.join(DIR_PATH, CONFIG_ARCH)
    try:
        tar = tarfile.open(archive_path)
    except EnvironmentError: # parent of IOError, OSError
        raise CiscoException("File {} not found or with errors!".format(archive_path))


    file_path = os.path.join(os.getcwd(), "configuration")
    if os.path.exists(file_path):
        shutil.rmtree(file_path)
    os.makedirs(file_path)
    tar.extractall(path=file_path)
    tar.close()

    all_list_ids = import_policy_lists(file_path)
    all_definition_ids = import_policy_definitions(file_path, all_list_ids)
    all_vedge_ids = import_vedge_policies(file_path, all_list_ids, all_definition_ids)
    all_vsmart_ids = import_vsmart_policies(file_path, all_list_ids, all_definition_ids)
    #all_security_ids = import_security_policies(file_path, all_list_ids, all_definition_ids)

    vedge_policy_id_old, vedge_policy_id_new = all_vedge_ids
    vsmart_policy_id_old, vsmart_policy_id_new = all_vsmart_ids
    #security_policy_id_old, security_policy_id_new = all_security_ids
    all_policy_ids = (vedge_policy_id_old, vedge_policy_id_new, vsmart_policy_id_old, vsmart_policy_id_new)

    shutil.rmtree(file_path)
    print("Successfully imported the policies to %s"%(SDWAN_IP))
    print("")

    return all_policy_ids

def configure(archive_path):
    """Import configuration.

        TO DO: Update site ids in definitions and
               Add security policies

        Example command:

             ./sd-wan-exim.py configure

    """

    #archive_path = os.path.join(DIR_PATH, CONFIG_ARCH)
    try:
        tar = tarfile.open(archive_path)
    except EnvironmentError: # parent of IOError, OSError
        raise CiscoException("File {} not found or with errors!".format(archive_path))

    file_path = os.path.join(os.getcwd(), "configuration")
    if os.path.exists(file_path):
        shutil.rmtree(file_path)
    os.makedirs(file_path)
    tar.extractall(path=file_path)
    tar.close()

    all_list_ids = import_policy_lists(file_path)
    all_definition_ids = import_policy_definitions(file_path, all_list_ids)
    all_vedge_ids = import_vedge_policies(file_path, all_list_ids, all_definition_ids)
    all_vsmart_ids = import_vsmart_policies(file_path, all_list_ids, all_definition_ids)
    #all_security_ids = import_security_policies(file_path, all_definition_ids)

    vedge_policy_id_old, vedge_policy_id_new = all_vedge_ids
    vsmart_policy_id_old, vsmart_policy_id_new = all_vsmart_ids
    #security_policy_id_old, security_policy_id_new = all_security_ids
    all_policy_ids = (vedge_policy_id_old, vedge_policy_id_new, vsmart_policy_id_old, vsmart_policy_id_new)

    all_template_ids = import_feature_templates(file_path)
    import_device_templates(file_path, all_template_ids, all_policy_ids)

    shutil.rmtree(file_path)
    print("Successfully imported the policies and templates to %s"%(SDWAN_IP))
    print("")


def update_password():
    """Update user password.

        Example command:

            ./sd-wan-exim.py password

    """

    print("\nUpdate password for user")
    vusername = str(input("  vManage Username: "))
    new_pwd = input("  New vManage Password: ")
    confirm_pwd = input("  Confirm vManage Password: ")

    if new_pwd != confirm_pwd:
        raise CiscoException("Passwords do not match! Please try again")
    else:
        vpassword = str(new_pwd)
        mount_point = "admin/user/password/{}".format(vusername)
        item =  {   "userName" : vusername,
                    "password" : vpassword
                }
        response = sdwanp.put_request(mount_point, item)
        print("Password updated for user {}.".format(vusername))

def add_user():
    """Create user.

        Example command:

            ./sd-wan-exim.py add_user

    """

    print("\nCreate new user")
    vusergroup = str(input("  vManage Group: "))
    vuserdesc = str(input("  vManage Full Name: "))
    vusername = str(input("  vManage Username: "))
    new_pwd = input("  New vManage Password: ")
    confirm_pwd = input("  Confirm vManage Password: ")

    if new_pwd != confirm_pwd:
        raise CiscoException("Passwords do not match! Please try again")
    else:
        vpassword = str(new_pwd)
        mount_point = "admin/user"
        item = {"group":[vusergroup], "description":vuserdesc, "userName":vusername, "password":vpassword}
        response = sdwanp.post_request(mount_point, item)
        print("User {} created.".format(vusername))


def use_tenant(tenant):
    print("tenant")

    mount_point = "tenant"
    response = json.loads(sdwanp.get_request(mount_point))
    device_data = response["data"]
    tenant_id = ""
    for device in device_data:
        if device["name"] == tenant:
            tenant_id = device["tenantId"]
    if not tenant_id:
        raise CiscoException("Tenant {} not found! Please check tenant name and try again.".format(tenant))

    item = {}
    mount_point = "tenant/" + str(tenant_id) + "/switch"
    response = sdwanp.post_request(mount_point, item)

    return response["VSessionId"]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description = __doc__, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('vManage', help='vManage IP address or DNS name')
    parser.add_argument('username', help='Username to login the vManage')
    parser.add_argument('password', help='Password to login the vManage')
    parser.add_argument('action', help='Action to execute on the vManage')
    parser.add_argument('configfile', default=CONFIG_ARCH, nargs='?', help='Optional, specific export and import archive name')
    parser.add_argument('-tenant', '--tenant', required=False, help='Specify tenant in multi-tenant setup')
    args = parser.parse_args()

    SDWAN_IP = args.vManage
    SDWAN_USERNAME = args.username
    SDWAN_PASSWORD = args.password
    SDWAN_ACTION = args.action

    SDWAN_FILE = args.configfile
    SDWAN_TENANT = args.tenant

    if SDWAN_IP is None or SDWAN_USERNAME is None or SDWAN_PASSWORD is None or SDWAN_ACTION is None:
        print("CISCO SDWAN details must be provided before running.")
        print(__doc__)
        print("")
        exit("1")

    SDWAN_CONFIG = os.path.join(DIR_PATH, SDWAN_FILE)

    sdwanp = rest_api_lib(SDWAN_IP, SDWAN_USERNAME, SDWAN_PASSWORD)

    if SDWAN_TENANT:
        HEADER_VSESSION = use_tenant(SDWAN_TENANT)

    if SDWAN_ACTION == "clean":
        action_print("clean                     Delete templates and policies configuration.")
        clean()
    elif SDWAN_ACTION == "clean_devices":
        action_print("clean_devices             Delete certificates and system devices.")
        clean_devices()
    elif SDWAN_ACTION == "clean_policies":
        action_print("clean_policies            Delete policies, definitions and lists.")
        clean_policies()
    elif SDWAN_ACTION == "clean_templates":
        action_print("clean_templates           Delete device and feature templates.")
        clean_templates()

    elif SDWAN_ACTION == "configure":
        action_print("configure                 Import entire configuration.")
        configure(SDWAN_CONFIG)
    elif SDWAN_ACTION == "configure_policies":
        action_print("configure_policies        Import vEdge/Vsmart policies, definitions and lists.")
        configure_policies(SDWAN_CONFIG)
    elif SDWAN_ACTION == "configure_templates":
        action_print("configure_templates       Import feature templates and device templates.")
        configure_templates(SDWAN_CONFIG)

    elif SDWAN_ACTION == "export":
        action_print("export                    Export entire configuration.")
        export(SDWAN_CONFIG)

    elif SDWAN_ACTION == "password":
        action_print("password                  Update user password.")
        update_password()
    elif SDWAN_ACTION == "add_user":
        action_print("add_user                  Add user.")
        add_user()

    elif SDWAN_ACTION == "invalidate_certificates":
        action_print("invalidate_certificates   Invalidate device certificates.")
        invalidate_certificates()
    elif SDWAN_ACTION == "validate_certificates":
        action_print("validate_certificates     Validate device certificates.")
        validate_certificates()
    elif SDWAN_ACTION == "push_to_controllers":
        action_print("push_to_controllers       Push configuration to controllers.")
        push_to_controllers()
    elif SDWAN_ACTION == "detach_devices":
        action_print("detach_devices            Detach device templates.")
        detach_devices()
    elif SDWAN_ACTION == "deactivate_policies":
        action_print("deactivate_policies       Deactivate policies.")
        deactivate_policies()
    else:
        print(__doc__)
