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

connection_properties = None
identity = None

app_description = "automated user setup by Python SDK"

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



def init(*args):
  global connection_properties
  filename = "connection.properties"

  for arg in sys.argv[1:]:
    arg_elements = arg.split("=")
    if (arg_elements[0]=="config"):
      filename= arg_elements[1]
      break

  print ("config file >" + filename + "<")   

  connection_properties = from_file(file_location=filename)     
  oci.config.validate_config(connection_properties)

def find(name=None, query_type=USER):
  found_id = None
  query = query_dictionary[query_type][ALL]
  if (name != None):
    query = query_dictionary[query_type][NAMED]+"'" + name + "'"
    print (query)

  search_client = oci.resource_search.ResourceSearchClient(connection_properties)
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



def connect ():
  global connection_properties, identity
  identity = oci.identity.IdentityClient(connection_properties)



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

def link_user_group (user, group):
  print ("tbd")

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
    client = oci.core.ComputeClient(connection_properties)
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
    request.compartment_id = connection_properties["tenancy"]
    request.name = groupname
    request.description = app_description
    group = identity.create_group(request)
    print("Group Id:" + group.data.id)
  except oci.exceptions.ServiceError as se:
    print ("ERROR - Create Group: ")
    print (se)
  return group.data.id


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
  init(args)
  connect()
  username = username_to_oci_compatible_name(username)

  if (username == None):
    username = connection_properties["new-username"]
    username_to_oci_compatible_name(username)
    #ToDo: add logic that says if empty string or None then throw error

  groupname = username+"-grp"
  compartmentname = username+"-cmt"
  policyname = username+"-pol"

  search_only = False

  # find()
  print ("located " + username + " ocid=" + tostring(find(username, USER)))
  print ("located " + compartmentname + " ocid=" + tostring(find(compartmentname, COMPARTMENT)))
  print ("located " + groupname + " ocid=" + tostring(find(groupname, GROUP)))
  print ("located " + policyname + " ocid=" + tostring(find(policyname, POLICY)))

  

  if (search_only == False):

    parent_compartment_ocid = None
    if (teamname != None):
      parent_compartment_ocid = find (teamname, COMPARTMENT)
      if (parent_compartment_ocid == None):
        raise LookupError ("No compartment found")
    else:
      parent_compartment_ocid = connection_properties["tenancy"]

    compartment_ocid = find(compartmentname, COMPARTMENT)
    if (compartment_ocid == None):
      compartment_ocid = create_compartment (parent_compartment_ocid, compartmentname)

    group_ocid = find(groupname, GROUP)
    if (group_ocid == None):
      create_group(groupname)

    user_ocid = find(username, USER)
    if (user_ocid == None):
      create_user (username, connection_properties["tenancy"],email_address)

    policyname_ocid = find (policyname, POLICY)
    if (policyname_ocid== None):
      create_user_compartment_policies (groupname, policyname, compartment_ocid, compartmentname)

    # link user and group
    #set policies on compartment


if __name__ == "__main__":
  main(sys.argv[1:])