#!/usr/bin/python

import sys
import oci
from oci.config import from_file
import logging
import logging.config

config_props = None
quota_props = None
config_filename = None
quota_config_filename = None

logger : logging.Logger

identity = None

APP_DESCRIPTION_PREFIX = "automated user setup by Python SDK"
APP_DESCRIPTION = APP_DESCRIPTION_PREFIX
    
CONN_PROP_DEFAULT = "connection.properties"
LOGGER_CONF_DEFAULT= "logging.properties"
TENANCY = "tenancy"

USER = "user"
COMPARTMENT="compartments"
GROUP="group"
ALL = "all"
NAMED="named"
POLICY="policy"
ACTIONDESCRIPTION="actiondesc"
DELETE="delete"
LOGGING="logconf"
EMAIL="email"
TEAMNAME="team"
CONFIGCLI="config"
QUOTACONFIGCLI="quotaconfig"

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
  """
    Extracts the filenames for the configuration files from command line arguments
    Sets up the config filename variables ready to be used
    Expecting 2 files (could be mapped to the same file)
      - Connection Based Properties
      - Quota based properties
    
    Parameters:
    arg : The commandline arguments
    """

  global config_filename, quota_config_filename, logger
  config_filename = CONN_PROP_DEFAULT
  quota_config_filename = CONN_PROP_DEFAULT

  for arg in sys.argv[1:]:
    arg_elements = arg.split("=")
    if (arg_elements[0]==CONFIGCLI):
      config_filename= arg_elements[1]
      logger.info ("config file >" + config_filename + "<") 
    elif (arg_elements[0]==QUOTACONFIGCLI):
      quota_config_filename= arg_elements[1]
      logger.info ("quota config file >" + quota_config_filename + "<") 


def init_quota():
  """
  Using the provided filename load the quota file into a properties structure
    
  """
  global quota_props
  quota_props = from_file(file_location=quota_config_filename)     

def init_connection():
  """
  Using the provided filename load the configuration file with all the values
  needed by the Python SDK to connect to OCI
    
  """
  global config_props, identity
  config_props = from_file(file_location=config_filename)     
  oci.config.validate_config(config_props)
  identity = oci.identity.IdentityClient(config_props)


def get_quota_statements (compartmentname:str, parent_compartment:str = None):
  global quota_props, config_props, logger
  quota_statements = []

  for config in quota_props:
    if (config.startswith(QUOTA_PREFIX)):
      quota_name = config[QUOTA_PRE_LEN:]
      compartment = compartmentname
      if (parent_compartment != None) and (len(parent_compartment) > 0):
        compartment = parent_compartment+":"+compartment

      stmt = "Set " + quota_name + " to " + config_props[config] + " in compartment " + compartment
      logger.info (stmt)
      quota_statements.append(stmt)
    else:
       logger.debug("ignoring config " + config + " not a quota property")
  return quota_statements



def find(name=None, query_type=USER, query_msg="", print_find = False):
  global logger

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
    logger.info ("Matched multiple values - returning a list")
    found_id = []
    for id in range(len(found_resources.data.items)):
      found_id.append (found_resources.data.items[id].identifier)

  if print_find:
    print()
    print(" Performing Query:"+query + " for " + query_msg)
    print("=========================================================")
    print (found_resources.data.items)
    print("=========================================================")

  return found_id


def create_user (username, compartment_id, email):
  global logger

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

    logger.info("User Name :"+ username + ";User Id:" + user_id)
  except oci.exceptions.ServiceError as se:
    logger.error ("Create User: " + username)
    logger.error (se)

  return user_id


def create_compartment (parentcompartmentid, compartmentname):
  global logger

  compartment_id = None
  try:
    request = oci.identity.models.CreateCompartmentDetails()
    request.description = APP_DESCRIPTION
    request.name = compartmentname
    request.compartment_id = parentcompartmentid
    compartment = identity.create_compartment(request)
    compartment_id = compartment.data.id
    logger.info ("Compartment Id:" + compartment_id)

    logger.info ("waiting on compartment state")
    client = oci.core.IdentityClient(config_props)
    oci.wait_until(client, client.get_compartment(compartment_id), 'lifecycle_state', 'ACTIVE')    
   
  except oci.exceptions.ServiceError as se:
    logger.error ("ERROR - Create Compartment: "+compartmentname + " child of " + parentcompartmentid)
    logger.error (se)

  return compartment_id


def create_user_compartment_policies (groupname, policyname, compartment_id, compartmentname):
  global logger

  policy_id = None
  try:
    manage_policy = "Allow group " + groupname +" to manage all-resources in compartment "+compartmentname
    logger.info ("add policy: " + manage_policy)
    request = oci.identity.models.CreatePolicyDetails()
    request.description = APP_DESCRIPTION
    request.name = policyname
    request.compartment_id = compartment_id
    request.statements = [manage_policy]

    policy_id = identity.create_policy(request)
  except oci.exceptions.ServiceError as se:
    logger.error ("ERROR - Create Policies: " + policyname +" group is"+groupname+ " in " +compartmentname)
    logger.error (se)
  return policy_id.data.id



def create_group (groupname):
  global logger

  try:
    request = oci.identity.models.CreateGroupDetails()
    request.compartment_id = config_props[TENANCY]
    request.name = groupname
    request.description = APP_DESCRIPTION
    group = identity.create_group(request)
    logger.info("Group Id:" + group.data.id)
  except oci.exceptions.ServiceError as se:
    logger.error ("ERROR - Create Group: ")
    logger.error (se)
  return group.data.id


def create_compartment_quota (quota_statements, compartment_id, quotaname):
  global logger

  try:
    request = oci.limits.models.CreateQuotaDetails()
    request.compartment_id = compartment_id
    request.statements = quota_statements

    logger.info ("Quota to be applied:")
    logger.info (quota_statements)

    request.description = APP_DESCRIPTION
    request.name = quotaname
    client = oci.limits.QuotasClient(config_props)

    quota = oci.limits.QuotasClient.create_quota(client,request)
    return quota.data.id

  except oci.exceptions.ServiceError as se:
    logger.error ("ERROR - Create Quota: ")
    logger.error (se)


def create_compartment_budget(budget_amount, compartment_id, budgetname):
  global logger

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
    logger.info ("Budget rule: " + budget_id)
    oci.wait_until(client, client.get_budget(budget_id), 'lifecycle_state', 'ACTIVE')    

  except oci.exceptions.ServiceError as se:
    logger.error ("ERROR - Create budget: ")
    logger.error (se)   
  return budget_id

def create_budget_alert(budget_id, budgetname, budgetalertname, alert_recipients, alert_message):
  global logger

  try:
    budget_alert_id = None
    if (budget_id == None):
      budget_id = find(budgetname, BUDGET, "create_compartment_budget")
      budget_id_str = ""

      if (budget_id == None):
        logger.info ("Had to locate budget:" + budgetname + " ocid is:"+budget_id_str)
      else:
        if isinstance(budget_id, list):
          budget_id = budget_id[0]
          logger.warning ("only assigning alert to one budget")

        request = oci.budget.models.CreateAlertRuleDetails()
        request.display_name = budgetalertname
        request.description = APP_DESCRIPTION
        request.type = request.TYPE_ACTUAL
        request.threshold_type = request.THRESHOLD_TYPE_ABSOLUTE
        request.threshold = 90.0
        request.message = alert_message
        request.recipients = alert_recipients

        client = oci.budget.BudgetClient(config_props)

        budget_alert = oci.budget.BudgetClient.create_alert_rule(client, budget_id, request)
        budget_alert_id = budget_alert.data.id
        logger.info ("Budget Alert :" + budgetalertname + " ocid:"+ budget_alert_id)
    return budget_alert_id

  except oci.exceptions.ServiceError as se:
    logger.info ("ERROR - Create budget rule: ")
    logger.info (se) 
    logger.info ("alert message:" + alert_message)  
    logger.info ("alert recipients:" + alert_recipients)


def username_to_oci_compatible_name(username):

  if (username != None):
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

def get_parent_compartment_ocid(teamname):
  parent_compartment_ocid = None
  if (teamname != None):
    parent_compartment_ocid = find (teamname, COMPARTMENT)
    if (parent_compartment_ocid == None):
      raise LookupError ("No compartment found")
  else:
    parent_compartment_ocid = config_props[TENANCY]
  return parent_compartment_ocid

def set_action_description(arg_elements):
  global logger

  actiondesc = arg_elements[1]
  actiondesc.replace("'", "")
  actiondesc.replace('"', "")
  if (len (actiondesc) > 0):
    APP_DESCRIPTION = APP_DESCRIPTION_PREFIX + " - " + arg_elements[1]
    logger.debug ("Action description >"+APP_DESCRIPTION+"<")


#def delete_compartment_content (compartment_id, ocid_list):
#  delrequest = oci.identity.models.BulkDeleteResourcesDetails()
#  delrequest.description = APP_DESCRIPTION
#  delrequest.
#
#  bulk_delete_resources(compartment_id, delrequest)


def main(*args):
  global logger
  print (args)

  log_conf = LOGGER_CONF_DEFAULT
  logging.config.fileConfig(log_conf)
  logger = logging.getLogger()
  if (logger == None):
    print ("oh damn")

  username = None
  teamname = None
  compartmentname = None
  email_address = None
  budget_amount = float(-1)
  delete = False
  DELOPTIONS = ["Y", "YES", "T", "TRUE"]
  CLIMSG = "CLI set "

  init_config_filename(args)
  init_connection()
  init_quota()

  if ACTIONDESCRIPTION in config_props:
      set_action_description([ACTIONDESCRIPTION, config_props[ACTIONDESCRIPTION]])


  for arg in sys.argv[1:]:
    arg_elements = arg.split("=")

    if (arg_elements[0]==USER):
      username = arg_elements[1]
      logger.info (CLIMSG+USER+"  >" + username + "<")    

    elif (arg_elements[0]==TEAMNAME):
      teamname= arg_elements[1]
      logger.info (CLIMSG+TEAMNAME+"  >" + teamname + "<")    

    elif (arg_elements[0]==EMAIL):
      email_address= arg_elements[1]
      logger.info (CLIMSG+EMAIL+"  >" + email_address + "<")    

      #ToDO: do we need this ?
    elif (arg_elements[0]==BUDGET):
      budget_amount= float(arg_elements[1])
      logger.info (CLIMSG+BUDGET+"  >" + budget_amount + "<")

    elif (arg_elements[0]==ACTIONDESCRIPTION):
      set_action_description(arg_elements[1])
      logger.info (CLIMSG+ACTIONDESCRIPTION+"  >" + arg_elements[1] + "<")

    elif (arg_elements[0]==LOGGING):
      log_conf= arg_elements[1]
      log_conf.strip()
      if (len(log_conf) < 1):
        log_conf = LOGGER_CONF_DEFAULT
      logging.config.fileConfig(log_conf)
      logger = logging.getLogger()

    elif (arg_elements[0]==DELETE):
      if (arg_elements[1].upper() in DELOPTIONS):
        delete = True
        logger.warning(DELOPTIONS + "option not available")
    else:
        logger.warning(arg_elements[0] + " Unknown config")


  username = get_username(username)
    #ToDo: add logic that says if empty string or None then throw error

  groupname = username+"-grp"
  compartmentname = username+"-cmt"
  policyname = username+"-pol"
  quotaname = username+"-qta"
  budgetname = username+"-bdg"
  budgetalertname = budgetname+"-alt"

  search_only = False

  # find()
  LOCATEDMSG = "located "
  CREATEDMSG = "created "
  OCIDMSG = " ocid="
  logger.info (LOCATEDMSG + username + OCIDMSG + tostring(find(username, USER)))
  logger.info (LOCATEDMSG + compartmentname + OCIDMSG + tostring(find(compartmentname, COMPARTMENT)))
  logger.info (LOCATEDMSG + groupname + OCIDMSG + tostring(find(groupname, GROUP)))
  logger.info (LOCATEDMSG + policyname + OCIDMSG + tostring(find(policyname, POLICY)))


  if (search_only == False):

    parent_compartment_ocid = get_parent_compartment_ocid(teamname)

    compartment_ocid = find(compartmentname, COMPARTMENT)
    if (compartment_ocid == None):
      compartment_ocid = create_compartment (parent_compartment_ocid, compartmentname)

    group_ocid = find(groupname, GROUP)
    if (group_ocid == None):
      group_ocid = create_group(groupname)
      print (CREATEDMSG + groupname + OCIDMSG + tostring(group_ocid))


    user_ocid = find(username, USER)
    if (user_ocid == None):
      user_ocid = create_user (username, config_props[TENANCY],email_address)
      print (CREATEDMSG + username + OCIDMSG + tostring(user_ocid))


    policyname_ocid = find (policyname, POLICY)
    if (policyname_ocid== None):
      policyname_ocid = create_user_compartment_policies (groupname, policyname, compartment_ocid, compartmentname)
      print (CREATEDMSG + policyname + OCIDMSG + tostring(policyname_ocid))

    if (parent_compartment_ocid != None):
      quota_ocid = create_compartment_quota (get_quota_statements(compartmentname, teamname),config_props[TENANCY],quotaname)
    else:
      quota_ocid = create_compartment_quota (get_quota_statements(compartmentname),config_props[TENANCY],quotaname)
    print (CREATEDMSG + budgetname + OCIDMSG + tostring(quota_ocid))

    if ((budget_amount == -1) and (quota_props != None)):
      budget_amount = float(quota_props[BUDGET])

    alert_message = ""
    alert_recipients = ""
    if (quota_props != None):
      alert_message = quota_props[BUDGETALERTMSG] + "\n for Compartment:" + compartmentname
      logger.debug ("Alert message:" + alert_message)
      alert_recipients = quota_props[BUDGETALERTRECIPIENTS]
      logger.debug (alert_recipients)
    else:
      logger.warning ("problem with quota props")

    budget_ocid = create_compartment_budget(budget_amount, compartment_ocid, budgetname)
    logger.info (CREATEDMSG + budgetname + OCIDMSG + tostring(budget_ocid))
    budgetalert_ocid =  create_budget_alert(budget_ocid, budgetname, budgetalertname, alert_recipients, alert_message)
    logger.info (CREATEDMSG + budgetalertname + OCIDMSG + tostring(budgetalert_ocid))




if __name__ == "__main__":
  main(sys.argv[1:])