#!/usr/bin/python

import sys
import oci
from oci.config import from_file

# Useful resources for getting setup:
# https://github.com/pyenv-win/pyenv-win#installation
# https://realpython.com/effective-python-environment/#virtual-environments
# https://docs.pipenv.org/en/latest/
# https://oracle-cloud-infrastructure-python-sdk.readthedocs.io/en/latest/installation.html
# https://mytechretreat.com/how-to-use-the-oci-python-sdk-to-make-api-calls/
# https://github.com/oracle/oci-python-sdk/blob/master/examples/quotas_example.py -- quotas example update
# https://docs.oracle.com/en-us/iaas/Content/Search/Concepts/querysyntax.htm - search query syntax

config_props = None
quota_props = None
config_filename = None
quota_config_filename = None

identity = None

app_description = "automated user setup by Python SDK"
    
TENANCY = "tenancy"

USER = "users"
COMPARTMENT="compartments"
GROUP="group"
ALL = "all"
NAMED="named"
POLICY="policy"

query_dictionary = {
  USER: {ALL : "query user resources where inactiveStatus = 0", NAMED : "query user resources where displayname = "},
  COMPARTMENT: {ALL : "query compartment resources where inactiveStatus = 0", NAMED : "query compartment resources where displayname = "},
  GROUP: {ALL : "query group resources where inactiveStatus = 0", NAMED : "query group resources where displayname = "},
  POLICY: {ALL : "query policy resources where inactiveStatus = 0", NAMED : "query policy resources where displayname = "}
}

QUOTA_PREFIX = "quota_"
QUOTA_PRE_LEN = len(QUOTA_PREFIX)

def init_config_filename (*args):
  global config_filename, quota_config_filename
  config_filename = "connection.properties"
  quota_config_filename = "connection.properties"

  for arg in sys.argv[1:]:
    arg_elements = arg.split("=")
    if (arg_elements[0]=="config"):
      config_filename= arg_elements[1]
      print ("config file >" + config_filename + "<") 
    elif (arg_elements[0]=="quotaconfig"):
      quota_config_filename= arg_elements[1]
      print ("quota config file >" + config_filename + "<") 


def init_connection():
  global config_props, identity
  config_props = from_file(file_location=config_filename)     
  oci.config.validate_config(config_props)
  identity = oci.identity.IdentityClient(config_props)

def get_quota_statements (compartmentname):
  global quota_props, config_props
  quota_statements = []

  for config in config_props:
    if (config.startswith(QUOTA_PREFIX)):
      quota_name = config[QUOTA_PRE_LEN:]
      stmt = "Set " + quota_name + " to " + config_props[config] + " in compartment " + compartmentname
      print (stmt)
      quota_statements.append(stmt)
    else:
      print ("ignoring " + config)
  return quota_statements




def find(name=None, query_type=USER):
  found_id = None
  query = query_dictionary[query_type][ALL]
  if (name != None):
    query = query_dictionary[query_type][NAMED]+"'" + name + "'"
    print (query)

  search_client = oci.resource_search.ResourceSearchClient(config_props)
  structured_search = oci.resource_search.models.StructuredSearchDetails(query=query,
                                                                           type='Structured',
                                                                           matching_context_type=oci.resource_search.models.SearchDetails.MATCHING_CONTEXT_TYPE_NONE)
  found_resources = search_client.search_resources(structured_search)

  # print (found_resources.data)
  result_size = len(found_resources.data.items)
  if ((result_size == 1) and (name!=None)):
    found_id = found_resources.data.items[0].identifier
  elif ((result_size == 0) and (name!=None)):
    found_id = None
  else:
    print()
    print(" Performing Query:"+query)
    print("=========================================================")
    print (found_resources.data.items)
    print("=========================================================")

  return found_id


def create_user (username, compartment_id, email):
  user_id = None
  try:
    request = oci.identity.models.CreateUserDetails()
    request.compartment_id = compartment_id
    request.name = username
    request.description = app_description
    if ((email != None) and (len(email) > 3)):
      request.email = email
    user = identity.create_user(request)
    user_id = user.data.id

    print("User Name :"+ username + ";User Id:" + user.data.id)
  except oci.exceptions.ServiceError as se:
    print ("ERROR - Create User: ")
    print (se)

  return user_id




def create_compartment (parentcompartment, compartmentname):
  compartment_id = None
  try:
    request = oci.identity.models.CreateCompartmentDetails()
    request.description = app_description
    request.name = compartmentname
    request.compartment_id = parentcompartment
    compartment = identity.create_compartment(request)
    print ("Compartment Id:" + compartment.data.id)
    compartment_id = compartment.data.id

    print ("waiting on compartment state")
    client = oci.core.ComputeClient(config_props)
    oci.wait_until(client, client.get_instance(compartment_id), 'lifecycle_state', 'ACTIVE')    
  except oci.exceptions.ServiceError as se:
    print ("ERROR - Create Compartment: ")
    print (se)

  return compartment_id


def create_user_compartment_policies (groupname, policyname, compartment_id, compartmentname):
  policy_id = None
  try:
    manage_policy = "Allow group " + groupname +" to manage all-resources in compartment "+compartmentname
    print ("add policy: " + manage_policy)
    request = oci.identity.models.CreatePolicyDetails()
    request.description = app_description
    request.name = policyname
    request.compartment_id = compartment_id
    request.statements = [manage_policy]

    policy_id = identity.create_policy(request)
  except oci.exceptions.ServiceError as se:
    print ("ERROR - Create Policies: ")
    print (se)
  return policy_id



def create_group (groupname):
  try:
    request = oci.identity.CreateGroupDetails()
    request.compartment_id = config_props["tenancy"]
    request.name = groupname
    request.description = app_description
    group = identity.create_group(request)
    print("Group Id:" + group.data.id)
  except oci.exceptions.ServiceError as se:
    print ("ERROR - Create Group: ")
    print (se)
  return group.data.id


def create_compartment_quota (quota_statements, compartment_id, quotaname):
  try:
    request = oci.limits.models.CreateQuotaDetails()
    request.compartment_id = compartment_id
    request.statements = quota_statements
    request.description = app_description
    request.name = quotaname
    client = oci.limits.QuotasClient(config_props)

    quota = oci.limits.QuotasClient.create_quota(client,request)
  except oci.exceptions.ServiceError as se:
    print ("ERROR - Create Quota: ")
    print (se)
  return quota.data.id

def username_to_oci_compatible_name(username):
  username = username.replace(".com", "")
  username = username.replace(".org", "")
  username = username.replace("@", "-")
  username = username.replace(".", "-")
  username = username.replace(" ", "")
  return username


def tostring (object):
  result = "--- not Found ---"

  if (object != None):
    result = object
  
  return result

def get_username(username):
  username = username_to_oci_compatible_name(username)

  if (username == None):
    username = config_props["new-username"]
    username_to_oci_compatible_name(username)
    #ToDo: add logic that says if empty string or None then throw error
  return username

def het_parent_compartment_ocid(teamname):
  parent_compartment_ocid = None
  if (teamname != None):
    parent_compartment_ocid = find (teamname, COMPARTMENT)
    if (parent_compartment_ocid == None):
      raise LookupError ("No compartment found")
  else:
    parent_compartment_ocid = config_props[TENANCY]
  return parent_compartment_ocid

def main(*args):
  print (args)
  username = None
  teamname = None
  compartmentname = None
  email_address = None

  for arg in sys.argv[1:]:
    arg_elements = arg.split("=")

    if (arg_elements[0]=="user"):
      username = arg_elements[1]
      print ("create user>" + username+"<")
    elif (arg_elements[0]=="team"):
      teamname= arg_elements[1]
      print ("Team attribution >" + teamname + "<")
    elif (arg_elements[0]=="email"):
      email_address= arg_elements[1]
      print ("Email  >" + email_address + "<")


  init_config_filename(args)
  init_connection()

  username = get_username(username)
    #ToDo: add logic that says if empty string or None then throw error

  groupname = username+"-grp"
  compartmentname = username+"-cmt"
  policyname = username+"-pol"
  quotaname = username+"-qta"

  search_only = False

  # find()
  LOCATEDMSG = "located "
  OCIDMSG = " ocid="
  print (LOCATEDMSG + username + OCIDMSG + tostring(find(username, USER)))
  print (LOCATEDMSG + compartmentname + OCIDMSG + tostring(find(compartmentname, COMPARTMENT)))
  print (LOCATEDMSG + groupname + OCIDMSG + tostring(find(groupname, GROUP)))
  print (LOCATEDMSG + policyname + OCIDMSG + tostring(find(policyname, POLICY)))

  get_quota_statements(compartmentname)


  if (search_only == False):

    parent_compartment_ocid = het_parent_compartment_ocid(teamname)

    compartment_ocid = find(compartmentname, COMPARTMENT)
    if (compartment_ocid == None):
      compartment_ocid = create_compartment (parent_compartment_ocid, compartmentname)

    group_ocid = find(groupname, GROUP)
    if (group_ocid == None):
      create_group(groupname)

    user_ocid = find(username, USER)
    if (user_ocid == None):
      create_user (username, config_props[TENANCY],email_address)

    policyname_ocid = find (policyname, POLICY)
    if (policyname_ocid== None):
      create_user_compartment_policies (groupname, policyname, compartment_ocid, compartmentname)

    create_compartment_quota (get_quota_statements(compartmentname),config_props[TENANCY],quotaname)





if __name__ == "__main__":
  main(sys.argv[1:])