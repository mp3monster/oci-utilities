#!/usr/bin/python

import sys
import oci
from oci.config import from_file
from oci.identity.models import CreateGroupDetails

# Useful resources for getting setup:
# https://github.com/pyenv-win/pyenv-win#installation
# https://realpython.com/effective-python-environment/#virtual-environments
# https://docs.pipenv.org/en/latest/
# https://oracle-cloud-infrastructure-python-sdk.readthedocs.io/en/latest/installation.html
# https://mytechretreat.com/how-to-use-the-oci-python-sdk-to-make-api-calls/

connection_properties = None
identity = None

app_description = "automated user setup by Python SDK"

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



def connect ():
  global connection_properties, identity
  identity = oci.identity.IdentityClient(connection_properties)



def create_user (username, compartment_id, email):
  print ("create - user")
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
    print("User Id:" + user.data.id)
  except oci.exceptions.ServiceError as se:
    print ("Create user: ")
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
  except oci.exceptions.ServiceError as se:
    print ("Create Compartment: ")
    print (se)

  return compartment_id


def create_user_compartment_policies (group, compartment_id, compartmentname):
  try:
    manage_policy = "Allow group " + group +" to manage all-resources in compartment "+compartmentname
    print ("add policy: " + manage_policy)
    request = oci.identity.models.CreatePolicyDetails()
    request.description = app_description
    request.name = compartmentname
    request.compartment_id = compartment_id
    request.statements = [manage_policy]

    policy_id = identity.create_policy(request)
  except oci.exceptions.ServiceError as se:
    print ("Create Policies: ")
    print (se)
  return policy_id



def scan_page_for (name, page):
  entity_id = None
  for entity in page:
    if (entity.name == name):
      entity_id = entity.id
      print ("Found " + name)
      break
  return entity_id



def get_compartment_by_name(compartmentname, compartment_id):
  print ("looking for compartment " + compartmentname)
  located_id = None

  try:
    response = identity.list_compartments(compartment_id)
    located_id = scan_page_for (compartmentname, response.data)
    while response.has_next_page and located_id == None:
      response = identity.list_users(compartment_id, page=response.next_page)
      located_id = scan_page_for (compartmentname, response.data)
  except oci.exceptions.ServiceError as se:
    print ("Get Compartment by Name: ")
    print (se)
  return located_id


def create_group (groupname):
  try:
    request = CreateGroupDetails()
    request.compartment_id = connection_properties["tenancy"]
    request.name = groupname
    request.description = app_description
    group = identity.create_group(request)
    print("Group Id:" + group.data.id)
  except oci.exceptions.ServiceError as se:
    print ("Create Group: ")
    print (se)
  return group.data.id


def username_to_oci_compatible_name(username):
  username = username.replace(".com", "")
  username = username.replace(".org", "")
  username = username.replace("@", "-")
  username = username.replace(".", "-")
  username = username.replace(" ", "")
  return username

def main(*args):
  print (args)
  username = None
  teamname = None
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
  #ToDo: add logic that says if empty string or None then throw error
  groupname = username+"-grp"
  compartmentname = username+"-cmt"

  if (teamname != None):
    parent_compartment = get_compartment_by_name (teamname, connection_properties["tenancy"])
    if (parent_compartment == None):
      raise LookupError ("No compartment found")
  else:
    parent_compartment = connection_properties["tenancy"]

  compartment_ocid = create_compartment (parent_compartment, compartmentname)

  group_ocid = create_group(groupname)

  user_ocid = create_user (username, connection_properties["tenancy"],email_address)

  create_user_compartment_policies (groupname, compartment_ocid, connection_properties["tenancyname"])

  # link user and group
  #set policies on compartment


if __name__ == "__main__":
  main(sys.argv[1:])