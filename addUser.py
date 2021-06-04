#!/usr/bin/python

import sys
import oci
from oci.config import from_file
import logging
import logging.config

config_props = None
"""Holds the configuration properties loaded. This configuration needs to 
include the properties necessary for the Python SDK to connect with OCI"""

quota_props = None
"""Holds the configuration properties that are used to define the quotas 
to be applied. The quotas properties need to follow a naming convention"""

QUOTA_PREFIX = "quota_"
QUOTA_PRE_LEN = len(QUOTA_PREFIX)
"""The prefix to recognize the quotas"""

config_filename = None
quota_config_filename = None

logger : logging.Logger
"""Python logger used within this module"""

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
QUOTA="quota"
QUOTANAME = "quotaname"
BUDGETNAME= "budgetname"

CONFIGCLI="config"
QUOTACONFIGCLI="quotaconfig"
"""The CLI names used to specify the locations of the config files"""

BUDGETALERTMSG="budget_alert_message"
BUDGETALERTRECIPIENTS = "budget_alert_recipients"
BUDGET = "budget"
BUDGETAMT = "budgetamount"

query_dictionary = {
  USER: {ALL : "query user resources where inactiveStatus = 0", NAMED : "query user resources where displayname = "},
  COMPARTMENT: {ALL : "query compartment resources where inactiveStatus = 0", NAMED : "query compartment resources where displayname = "},
  GROUP: {ALL : "query group resources where inactiveStatus = 0", NAMED : "query group resources where displayname = "},
  POLICY: {ALL : "query policy resources where inactiveStatus = 0", NAMED : "query policy resources where displayname = "},
  BUDGET: {ALL : "query budget resources where inactiveStatus = 0", NAMED : "query budget resources where displayname = "},
  QUOTA: {ALL : "query quota resources where inactiveStatus = 0", NAMED : "query quota resources where displayname = "}
}
"""A dictionary of queries to be used to obtain the OCID(s) for various types of OCI objects being used"""




def init_config_filename (*args):
  """
    Extracts the filenames for the configuration files from command line arguments
    Sets up the config filename variables ready to be used
    Expecting 2 files (could be mapped to the same file)
      - Connection Based Properties
      - Quota based properties
    
    **Parameters**
    - arg : The commandline arguments
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
  """
    Loads the quota configuration rules from the properties file to setup.
    The properties are used to populate a series of quotas
    
    **Parameters**
    * compartmentname : The compartment name that the quota is to be applied to
    * parent_compartment : The name of the parent compartment if a parent exists. 
    
    **Returns**
    list of string statements
    """  
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
  """
    Locates the OCID for different types of entities. This includes the means to send to the
    console the list of OCI entities located
    
    **Parameters**
    * name : the name of a specific OCI object wanted. If set to None then the query for all is applied
    * query_type : The type of OCI entity to be searched for. Used as part of the key into the data structure of queries. Values
    accepted are:
      * USER
      * COMPARTMENT
      * GROUP
      * POLICY
      * BUDGET
      * QUOTA
    * query_msg : Used in the logging to help show indicate the origin/reason for the query
    * print_find : Whether to send the search result the console
    
    **Returns**
    OCID if a single entity is located. If multiple entities are found this is a 
    list of OCIDs
    """    
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
  """
  Creates the user, linking the user to the compartment and provides the email for the user.
  This will trigger an email to the user to confirm their account

  **Parameters**
  * username : xx
  * compartmentid : xx
  * email : User's email address

  **Returns**

  """  
  ##Todo: Need to set the IDCS side of the user up
  global logger

  user_ocid = find(username, USER, "pre create user check")
  if (user_ocid == None):
    try:
      request = oci.identity.models.CreateUserDetails()
      request.compartment_id = compartment_id
      request.name = username
      request.description = APP_DESCRIPTION
      if ((email != None) and (len(email) > 3)):
        request.email = email
        logger.debug ("request.email set")
      user = identity.create_user(request)
      user_id = user.data.id

      logger.info("User Name :"+ username + "; email:"+ email +";User Id:" + user_id)
    except oci.exceptions.ServiceError as se:
      logger.error ("Create User: " + username)
      logger.error (se)

  return user_ocid


def create_compartment (parentcompartmentid, compartmentname):
  """
  Creates the compartment as a child to another identified compartment. 
  If parentcompartmentid is not provided then we make a top level compartment

  **Parameters**
  * compartmentname : xx
  * parentcompartmentid : xx

  **Returns**
    The OCID for the compartment created
  """   
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


def create_user_compartment_policies (groupname, policyname, compartmentid, compartmentname):
  """
  Creates the XXXX

  **Parameters**
  * groupname : xx
  * policyname : xx
  * compartmentid : xx
  * compartmentname : xx
  **Returns**
    The OCID for policy created
  """   
  global logger

  policy_ocid = None
  policy_ocid = find (policyname, POLICY)
  if (policy_ocid == None):  
    try:
      manage_policy = "Allow group " + groupname +" to manage all-resources in compartment "+compartmentname
      logger.info ("add policy: " + manage_policy)
      request = oci.identity.models.CreatePolicyDetails()
      request.description = APP_DESCRIPTION
      request.name = policyname
      request.compartment_id = compartmentid
      request.statements = [manage_policy]

      policy = identity.create_policy(request)
      policy_ocid = policy.data.id
    except oci.exceptions.ServiceError as se:
      logger.error ("ERROR - Create Policies: " + policyname +" group is"+groupname+ " in " +compartmentname)
      logger.error (se)

  return policy_ocid

def create_group (groupname):
  """
  Creates the the group if the named group doesnt exist.

  **Parameters**
  * groupname : xx~
  **Returns**
    The OCID for policy created
  """  
  global logger

  group_ocid = find(groupname, GROUP, "pre create group check")
  if (group_ocid == None):
    try:
      request = oci.identity.models.CreateGroupDetails()
      request.compartment_id = config_props[TENANCY]
      request.name = groupname
      request.description = APP_DESCRIPTION
      group = identity.create_group(request)
      group_ocid = group.data.id
      logger.info("Group Id:" + group.data.id)
    except oci.exceptions.ServiceError as se:
      logger.error ("ERROR - Create Group: ")
      logger.error (se)

  return group_ocid


def create_compartment_quota (quota_statements, compartment_id, quotaname):
  global logger

  quota_ocid = find(quotaname, QUOTA, "pre create quota check")
  if (quota_ocid == None):
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
      quota_ocid = quota.data.id

    except oci.exceptions.ServiceError as se:
      logger.error ("ERROR - Create Quota: ")
      logger.error (se)

  return quota_ocid


def create_compartment_budget(budget_amount, compartment_id, budgetname):
  global logger

  # https://oracle-cloud-infrastructure-python-sdk.readthedocs.io/en/latest/api/budget/models/oci.budget.models.UpdateBudgetDetails.html#oci.budget.models.UpdateBudgetDetails
  budget_id = None
  budget_id = find(budgetname, BUDGET, "pre create budget check")
  if (budget_id == None):
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

  logger.debug ("Entered create_budget_alert")
  try:
    budget_alert_id = None
    if (budget_id == None):
      budget_id = find(budgetname, BUDGET, "create_budget_alert")

    if (budget_id == None):
      logger.error ("Failed to locate budget:" + budgetname + " no alert details will be set")
    else:
      if isinstance(budget_id, list):
        budget_id = budget_id[0]
        logger.warning ("only assigning alert to one budget")
        
      logger.info ("Located budget:" + budgetname + " ocid is:"+budget_id)

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
      #logger.info ("Budget Alert :" + budgetalertname + " ocid:"+ budget_alert_id)

  except oci.exceptions.ServiceError as se:
    logger.error ("ERROR - Create budget rule: ")
    logger.error (se) 
    logger.error ("alert message:" + alert_message)  
    logger.error ("alert recipients:" + alert_recipients)

  logger.debug (budget_alert_id)
  return budget_alert_id


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


def get_budget_amount (budget_amt_obj):
  global logger
  budget_amount = float(-1)
  if (budget_amt_obj != None):
    try:
      budget_amount = float(budget_amt_obj)
    except ValueError as ve:
      logger.error ("Error converting budget amount to a numeric", ve)
  return budget_amount


def main(*args):
  global logger
  print (args)

  log_conf = LOGGER_CONF_DEFAULT
  logging.config.fileConfig(log_conf)
  logger = logging.getLogger()
  if (logger == None):
    print ("oh damn")

  init_config_filename(args)
  init_connection()
  init_quota()

  username = config_props.get(USER)
  teamname = config_props.get(TEAMNAME)
  email_address = config_props.get(EMAIL)
  quotaname = config_props.get(QUOTANAME)
  budgetname = config_props.get(BUDGETNAME)


  budget_amount = float(-1)
  if (quota_props != None):
    budget_amount = get_budget_amount(config_props.get(BUDGETAMT))


  delete = False
  DELOPTIONS = ["Y", "YES", "T", "TRUE"]
  CLIMSG = "CLI set "

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
      email_address=  arg_elements[1]
      email_address = email_address.strip()
      if (len(email_address) < 3):
          email_address = config_props(EMAIL)
          logger.warn("CLI setting for " + EMAIL + " ignored, value too short")
      logger.info (CLIMSG+EMAIL+"  >" + email_address + "<")    

    elif (arg_elements[0]==BUDGET):
      budgetname = arg_elements[1]
      logger.info (CLIMSG+BUDGET+"  >" + arg_elements[1] + "<")      

    elif (arg_elements[0]==BUDGETAMT):
      budget_amount = get_budget_amount(arg_elements[1])
      logger.info (CLIMSG+BUDGETAMT+"  >" + budget_amount + "<")

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
        logger.warning(DELETE + "option not available")

    elif (arg_elements[0]==CONFIGCLI or arg_elements[0]==QUOTACONFIGCLI):
      logger.debug ("processed " + arg + " separately")
    else:
        logger.warning(arg_elements[0] + " Unknown config, original value="+arg)

  if (email_address ==None):
    email_address = username
    logger.debug ("Set email to:" + email_address)
    # must set now as 

  username = get_username(username)
    #ToDo: add logic that says if empty string or None then throw error

  groupname = username+"-grp"
  compartmentname = username+"-cmt"
  policyname = username+"-pol"

  if (quotaname == None) or (len(quotaname) < 5):
    quotaname = username+"-qta"
    logger.info ("Quota name set to " + quotaname)


  if (budgetname == None) or (len(budgetname) < 5):
    budgetname = username+"-bdg"
    logger.info ("Budget name set to " + budgetname)

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


    group_ocid = create_group(groupname)
    logger.info (groupname + OCIDMSG + tostring(group_ocid))

    user_ocid = create_user (username, config_props[TENANCY], email_address)
    logger.info (username + OCIDMSG + tostring(user_ocid))


    policyname_ocid = create_user_compartment_policies (groupname, policyname, compartment_ocid, compartmentname)
    logger.info (policyname + OCIDMSG + tostring(policyname_ocid))

    if (quota_props != None):
      alert_message = ""
      alert_recipients = ""
      if (parent_compartment_ocid != None):
        quota_ocid = create_compartment_quota (get_quota_statements(compartmentname, teamname),config_props[TENANCY],quotaname)
      else:
        quota_ocid = create_compartment_quota (get_quota_statements(compartmentname),config_props[TENANCY],quotaname)
      logger.info (quotaname + OCIDMSG + tostring(quota_ocid))

      alert_message = quota_props[BUDGETALERTMSG] + "\n for Compartment:" + compartmentname
      logger.debug ("Alert message:" + alert_message)
      alert_recipients = quota_props[BUDGETALERTRECIPIENTS]
      logger.debug ("Alert recipients:" + alert_recipients)

      budget_ocid = create_compartment_budget(budget_amount, compartment_ocid, budgetname)
      logger.info (CREATEDMSG + budgetname + OCIDMSG + tostring(budget_ocid))
      budgetalert_ocid =  create_budget_alert(budget_ocid, budgetname, budgetalertname, alert_recipients, alert_message)
      logger.info (CREATEDMSG + budgetalertname + OCIDMSG + tostring(budgetalert_ocid))

    else:
      logger.warning ("problem with quota props not existing - not quotas or budgets set")


if __name__ == "__main__":
  main(sys.argv[1:])