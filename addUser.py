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
# https://docs.oracle.com/en-us/iaas/Content/General/Concepts/resourcequotas.htm - setting quotas
# https://docs.oracle.com/en-us/iaas/Content/Billing/Concepts/budgetsoverview.htm#Budgets_Overview - setting budgets

config_props = None
quota_props = None
config_filename = None
quota_config_filename = None

identity = None

APP_DESCRIPTION = "automated user setup by Python SDK"
    
CONN_PROP_DEFAULT = "connection.properties"    
TENANCY = "tenancy"

USER = "users"
COMPARTMENT="compartments"
GROUP="group"
ALL = "all"
NAMED="named"
POLICY="policy"

BUDGETALERTMSG="budget_alert_message"
BUDGETALERTRECIPIENTS = "budget_alert_recipients"
BUDGET = "budget"

query_dictionary = {
  USER: {ALL : "query user resources where inactiveStatus = 0", NAMED : "query user resources where displayname = "},
  COMPARTMENT: {ALL : "query compartment resources where inactiveStatus = 0", NAMED : "query compartment resources where displayname = "},
  GROUP: {ALL : "query group resources where inactiveStatus = 0", NAMED : "query group resources where displayname = "},
  POLICY: {ALL : "query policy resources where inactiveStatus = 0", NAMED : "query policy resources where displayname = "},
  BUDGET: {ALL : "query budget resources where inactiveStatus = 0", NAMED : "query budget resources where displayname = "}

}

QUOTA_PREFIX = "quota_"
QUOTA_PRE_LEN = len(QUOTA_PREFIX)

def init_config_filename (*args):
  global config_filename, quota_config_filename
  config_filename = CONN_PROP_DEFAULT
  quota_config_filename = CONN_PROP_DEFAULT

  for arg in sys.argv[1:]:
    arg_elements = arg.split("=")
    if (arg_elements[0]=="config"):
      config_filename= arg_elements[1]
      print ("config file >" + config_filename + "<") 
    elif (arg_elements[0]=="quotaconfig"):
      quota_config_filename= arg_elements[1]
      print ("quota config file >" + config_filename + "<") 

def init_quota():
  global quota_props
  quota_props = from_file(file_location=quota_config_filename)     

def init_connection():
  global config_props, identity
  config_props = from_file(file_location=config_filename)     
  oci.config.validate_config(config_props)
  identity = oci.identity.IdentityClient(config_props)

def get_quota_statements (compartmentname):
  global quota_props, config_props
  quota_statements = []

  for config in quota_props:
    if (config.startswith(QUOTA_PREFIX)):
      quota_name = config[QUOTA_PRE_LEN:]
      stmt = "Set " + quota_name + " to " + config_props[config] + " in compartment " + compartmentname
      print (stmt)
      quota_statements.append(stmt)
    # else:
      # print ("ignoring " + config)
  return quota_statements



def find(name=None, query_type=USER):
  found_id = None
  query = query_dictionary[query_type][ALL]
  if (name != None):
    query = query_dictionary[query_type][NAMED]+"'" + name + "'"
    # print (query)

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
    request.description = APP_DESCRIPTION
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
    request.description = APP_DESCRIPTION
    request.name = compartmentname
    request.compartment_id = parentcompartment
    compartment = identity.create_compartment(request)
    compartment_id = compartment.data.id
    print ("Compartment Id:" + compartment_id)

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
    request.description = APP_DESCRIPTION
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
    request.compartment_id = config_props[TENANCY]
    request.name = groupname
    request.description = APP_DESCRIPTION
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
    request.description = APP_DESCRIPTION
    request.name = quotaname
    client = oci.limits.QuotasClient(config_props)

    quota = oci.limits.QuotasClient.create_quota(client,request)
    return quota.data.id

  except oci.exceptions.ServiceError as se:
    print ("ERROR - Create Quota: ")
    print (se)


def create_compartment_budget(budget_amount, compartment_id, budgetname, alert_recipients, alert_message):
  # https://oracle-cloud-infrastructure-python-sdk.readthedocs.io/en/latest/api/budget/models/oci.budget.models.UpdateBudgetDetails.html#oci.budget.models.UpdateBudgetDetails
  budget_id = None
  try:
    request = oci.budget.models.CreateBudgetDetails()
    request.compartment_id = config_props[TENANCY]
    request.description = APP_DESCRIPTION
    request.display_name = budgetname
    request.amount = budget_amount
    request.reset_period = oci.budget.models.CreateBudgetDetails.RESET_PERIOD_MONTHLY
    request.target_type = oci.budget.models.CreateBudgetDetails.TARGET_TYPE_COMPARTMENT
    request.targets = [compartment_id]

    client = oci.budget.BudgetClient(config_props)

    budget_created = oci.budget.BudgetClient.create_budget(client, request)
    budget_id = budget_created.data.id
    print ("Budget rule: " + budget_id)
    oci.wait_until(client, client.get_instance(budget_created.data.id), 'lifecycle_state', 'ACTIVE')    

  except oci.exceptions.ServiceError as se:
    print ("ERROR - Create budget: ")
    print (se)   

  try:
    request2 = oci.budget.models.CreateAlertRuleDetails()
    request2.display_name = budgetname+"-alert"
    request2.description = APP_DESCRIPTION
    request2.type = request2.TYPE_ACTUAL
    request2.threshold_type = request2.THRESHOLD_TYPE_ABSOLUTE
    request2.threshold = 90.0
    request2.message = alert_message
    request2.recipients = alert_recipients

    client = oci.budget.BudgetClient(config_props)

    if (budget_id == None):
      budget_id = find(budgetname, BUDGET)

    budget_alert = oci.budget.BudgetClient.create_alert_rule(client, budget_id, request2)
    print ("Budget Alert :" + budget_alert.data.id)
    return budget_alert.data.id

  except oci.exceptions.ServiceError as se:
    print ("ERROR - Create budget rule: ")
    print (se)    


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
  budget_amount = float(-1)

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
    elif (arg_elements[0]=="budget"):
      budget_amount= float(arg_elements[1])
      print ("Budget  >" + budget_amount + "<")    


  init_config_filename(args)
  init_connection()
  init_quota()

  username = get_username(username)
    #ToDo: add logic that says if empty string or None then throw error

  groupname = username+"-grp"
  compartmentname = username+"-cmt"
  policyname = username+"-pol"
  quotaname = username+"-qta"
  budgetname = username+"-bdg"

  search_only = False

  # find()
  LOCATEDMSG = "located "
  OCIDMSG = " ocid="
  print (LOCATEDMSG + username + OCIDMSG + tostring(find(username, USER)))
  print (LOCATEDMSG + compartmentname + OCIDMSG + tostring(find(compartmentname, COMPARTMENT)))
  print (LOCATEDMSG + groupname + OCIDMSG + tostring(find(groupname, GROUP)))
  print (LOCATEDMSG + policyname + OCIDMSG + tostring(find(policyname, POLICY)))
  # print (get_quota_statements(compartmentname))


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

    if ((budget_amount == -1) and (quota_props != None)):
      budget_amount = float(quota_props[BUDGET])

    alert_message = ""
    alert_recipients = ""
    if (quota_props != None):
      alert_message = quota_props[BUDGETALERTMSG] + "\n for Compartment:" + compartmentname
      # print ("Alert message:" + alert_message)
      alert_recipients = quota_props[BUDGETALERTRECIPIENTS]
      # print (alert_recipients)
    else:
      print ("problem with quota props")

    create_compartment_budget(budget_amount, compartment_ocid, budgetname, alert_recipients, alert_message)




if __name__ == "__main__":
  main(sys.argv[1:])