#!/usr/bin/python

import sys
import oci
from oci.config import from_file
import logging
import logging.config
import json

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

Identity = None

APP_DESCRIPTION_PREFIX = "automated user setup by Python SDK"
APP_DESCRIPTION = APP_DESCRIPTION_PREFIX
    
CONN_PROP_DEFAULT = "connection.properties"
QUOTA_PROP_DEFAULT = "quotas.json"

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
LIST="listquota"
VALIDATE_QUOTA="validate"

CONFIGCLI="config"
QUOTACONFIGCLI="quotaconfig"
"""The CLI names used to specify the locations of the config files"""

BUDGETALERTMSG="alert_message"
BUDGETALERTRECIPIENTS = "alert_recipients"
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
  quota_config_filename = QUOTA_PROP_DEFAULT

  for arg in sys.argv[1:]:
    arg_elements = arg.split("=")
    if (arg_elements[0]==CONFIGCLI):
      config_filename= arg_elements[1]
      logger.info ("config file >" + config_filename + "<") 
    elif (arg_elements[0]==QUOTACONFIGCLI):
      quota_config_filename= arg_elements[1]
      logger.info ("quota config file >" + quota_config_filename + "<") 
##########

def validate_quota_config(check_minor_attributes=False):
  global logger, quota_props

  logger.debug("Validating Quota file")
  err_count = 0
  warning_count = 0
  minor_warning_count = 0
  unused_count=0

  family_count = 1
  family_desc = ""
  quota_name = ""
  try:
    for quota_family in quota_props["quotas"]:
      if ("description" in quota_family):
        family_desc = quota_family["description"]
      else:
        family_desc = "--Not Defined--"
      if ("description" not in quota_family) or (len(quota_family["description"]) < 3):
        logger.warning ("Quota description on " + family_desc + "( family group " + str(family_count) + ") is incomplete")
        warning_count+=1
      if ("family_name" not in quota_family) or (len(quota_family["family_name"]) < 3):
        logger.warning ("Quota Family Name on (" +family_desc+") family count " + str(family_count) + " is incomplete")
        warning_count+=1
      if ("quota" not in quota_family) or (len(quota_family["quota"]) == 0):
        logger.warning ("No individual quotas set on (" +family_desc+") family count " + str(family_count) + " is incomplete")
        warning_count+=1
      if (check_minor_attributes):
        if ("documentation_url" not in quota_family) or (len(quota_family["documentation_url"]) < 9):
          logger.warning ("Documentation_url on (" +family_desc+") family count " + str(family_count) + " is incomplete")
          minor_warning_count+=1
        if ("comment" not in quota_family) or (len(quota_family["comment"]) < 1):
          logger.warning ("Documentation_url on (" +family_desc+") family count " + str(family_count) + " is incomplete")
          minor_warning_count+=1

      else:
        quota_count=1
        for quota in quota_family["quota"]:
          try:
            quota_name = quota["quota_name"]
            if ("quota_name" not in quota):
              logger.warning ("Quota name in family " + str(family_count) + " is missing")
              quota_name = "--Not Defined--"
              warning_count+=1
            else:
              if (len(quota["quota_name"] ) < 3):
                logger.warning ("Quota name in family " + str(family_count) + " is incomplete")
                warning_count+=1                  
            if ("value" not in quota) or (quota["value"] < 0):  
              msg = family_desc+"."+quota_name+ " family " + str(family_count) + " quota no " + str(quota_count)
              logger.warning (msg + " -- value not correct")
              warning_count+=1
            if ("apply" not in quota): 
              msg = family_desc+"."+quota_name+ " family " + str(family_count) + " quota no " + str(quota_count)
              logger.warning (msg + " -- apply to specified")  
              warning_count+=1
            else:
              if (quota["apply"] == False):  
                msg = family_desc+"."+quota_name+ " family " + str(family_count) + " quota no " + str(quota_count)
                logger.warning (msg + " -- value wont be used")        
                unused_count+=1               
          
          except Exception as err:
            msg = family_desc+"."+quota_name+ " family " + str(family_count) + " quota no " + str(quota_count) + " errored"
            logger.error(msg, err)
            err_count+=1
          quota_count+=1
      family_count += 1
  except Exception as err:
    logger.error(err)
    err_count+=1

  if (err_count > 0):
    logger.warning ("Total of " + str(err_count) + " errors found")
  else:
    logger.info ("Total of " + str(err_count) + " errors found")
  if (warning_count > 0):
    logger.warning ("Total of " + str(warning_count) + " warnings found")
  else:
    logger.info ("Total of " + str(warning_count) + " warnings found")
  if (minor_warning_count > 0):
    logger.warning ("Total of " + str(minor_warning_count) + " minor warnings found")
  else:
    logger.info ("Total of " + str(minor_warning_count) + " minor warnings found")

  logger.info ("Total of " + str(unused_count) + " individual quotes not to be used")

##########         

def init_quota():
  """
  Using the provided filename load the quota file into a properties structure
    
  """
  global quota_props, logger

  logger.debug("Quota file:"+quota_config_filename)
  file = open(quota_config_filename,"r")

  quota_props = json.load(file)
  file.close()

 ##########
 
def init_connection():
  """
  Using the provided filename load the configuration file with all the values
  needed by the Python SDK to connect to OCI
    
  """
  global config_props, Identity
  config_props = from_file(file_location=config_filename)     
  oci.config.validate_config(config_props)
  Identity = oci.identity.IdentityClient(config_props)
##########


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

  # sort out which compartment
  if (parent_compartment != None) and (len(parent_compartment) > 0):
    compartment = parent_compartment+":"+compartment

  if ("quotas" in quota_props):
    for quota_family in quota_props["quotas"]:
      if ("quota" in quota_family):
        for quota in quota_family["quota"]:
          if ("apply" not in quota) and ("family_name" not in quota_family) and ("quota_name" not in quota) and ("value" not in quota_family):
            logger.error ("Missing data in the quotas configuration")
          else:
            if (quota["apply"]):
              stmt = "Set " + quota_family["family_name"] + " quota " + quota["quota_name"] + " to " + quota_family["value"] + " in compartment " + compartment
              logger.debug (stmt)
              quota_statements.append(stmt)
      else:
        logger.warning ("No individual quotas")
  else:
    logger.warning ("No quotas in quota config")

  return quota_statements
##########



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
##########


def create_user (username, compartment_id, email):
  """
  Creates the user, linking the user to the compartment and provides the email for the user.
  This will trigger an email to the user to confirm their account

  **Parameters**
  * username : the OCI friendly username
  * compartmentid : the compartment to associate the user id to
  * email : User's email address

  **Returns**
  the OCID for the username
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
      user = Identity.create_user(request)
      user_id = user.data.id

      logger.info("User Name :"+ username + "; email:"+ email +";User Id:" + user_id)
    except oci.exceptions.ServiceError as se:
      logger.error ("Create User: " + username)
      logger.error (se)

  return user_ocid
##########

def create_idcs_user (tenancyid, idcs_name, metadata_url, metadata):
  # https://github.com/oracle/oci-python-sdk/issues/232
  # https://medium.com/@madajewski.b/oci-creating-a-new-user-605519963b2d
  global logging, config_props
  
  return None
  iam_client = oci.identity.IdentityClient(config_props)

  idp = oci.identity.models.CreateSaml2IdentityProviderDetails ()
  idp.compartment_id = config_props[TENANCY]
  idp.name = 'idcs_name'
  idp.description = 'idcs_description'
  idp.product_type = 'IDCS'
  idp.protocol = 'SAML2'
  idp.metadata_url = metadata_url # The URL for retrieving the identity provider’s metadata, which contains information required for federating.
  idp.metadata = metadata
  # The XML that contains the information required for federating.
  # load local file?? Isnt this creating trhe federation?

  iam_client.create_identity_provider(idp)
  return idp.data.id

##########



def create_compartment (parentcompartmentid, compartmentname):
  """
  Creates the compartment as a child to another identified compartment. 
  If parentcompartmentid is not provided then we make a top level compartment

  **Parameters**
  * compartmentname : the name of the compartment to create
  * parentcompartmentid : the parent compartment if there is one. If unset 

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
    compartment = Identity.create_compartment(request)
    compartment_id = compartment.data.id
    logger.info ("Compartment Id:" + compartment_id)

    logger.info ("waiting on compartment state")
    #client = oci.core.IdentityClient(config_props)
    oci.wait_until(Identity, Identity.get_compartment(compartment_id), 'lifecycle_state', 'ACTIVE')    
   
  except oci.exceptions.ServiceError as se:
    logger.error ("ERROR - Create Compartment: "+compartmentname + " child of " + parentcompartmentid)
    logger.error (se)

  return compartment_id
##########


def create_user_compartment_policies (groupname, policyname, compartmentid, compartmentname):
  """
  Creates a privileges policy for the user on the compartment. This assumes that we're
  working with the child compartment, as the parent has more restricted policies.

  ToDo: Extend so can set a more restrictive set of policies for a parent compartment

  **Parameters**
  * groupname : as policies are linked to groups not individuals, we need the groupname
  * policyname : name to use for this policy
  * compartmentid : the compartment that this policy is linked to
  * compartmentname : the compartment name
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

      policy = Identity.create_policy(request)
      policy_ocid = policy.data.id
    except oci.exceptions.ServiceError as se:
      logger.error ("ERROR - Create Policies: " + policyname +" group is"+groupname+ " in " +compartmentname)
      logger.error (se)

  return policy_ocid
##########


def create_group (groupname):
  """
  Creates the the group if the named group doesn't exist.

  **Parameters**
  * groupname : name of the group to create
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
      group = Identity.create_group(request)
      group_ocid = group.data.id
      logger.info("Group Id:" + group.data.id)
    except oci.exceptions.ServiceError as se:
      logger.error ("ERROR - Create Group: ")
      logger.error (se)

  return group_ocid
##########


def create_compartment_quota (quota_statements, compartmentid, quotaname):
  """
  Set the quota on a compartment. If the quota already exists then we return the existing quota's OCID

  **Parameters**
  * quota_statements : the statements that have been assembled from the quotas configuration source
  * compartmentid : the OCID of the compartment to apply the quota to
  * quotaname : name of the quota
  **Returns**
    The OCID for the quota definition
  """  
  global logger

  quota_ocid = find(quotaname, QUOTA, "pre create quota check")
  if (quota_ocid == None):
    try:
      request = oci.limits.models.CreateQuotaDetails()
      request.compartment_id = compartmentid
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
##########


def create_compartment_budget(budget_amount, compartmentid, budgetname):
  """
  XXXX
  https://oracle-cloud-infrastructure-python-sdk.readthedocs.io/en/latest/api/budget/models/oci.budget.models.UpdateBudgetDetails.html#oci.budget.models.UpdateBudgetDetails

  **Parameters**
  * budget_amount : xx
  * compartmentid : xx
  * budgetname : xx
  **Returns**
    The OCID for the budget object
  """ 
  global logger

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
      request.targets = [compartmentid]

      client = oci.budget.BudgetClient(config_props)

      budget_created = oci.budget.BudgetClient.create_budget(client, request)
      budget_id = budget_created.data.id
      logger.info ("Budget rule: " + budget_id)
      oci.wait_until(client, client.get_budget(budget_id), 'lifecycle_state', 'ACTIVE')    

    except oci.exceptions.ServiceError as se:
      logger.error ("ERROR - Create budget: ")
      logger.error (se) 

  return budget_id
##########


def create_budget_alert(budgetid, budgetname, budgetalertname, alert_recipients, alert_message):
  """
  XXXX

  **Parameters**
  * budgetid : xx~
  * budgetname : xx
  * budgetalertname : xx
  * alert_recipients : xx
  * alert_message
  **Returns**
    The OCID for 
  """    
  global logger

  logger.debug ("Entered create_budget_alert")
  try:
    budget_alert_id = None
    if (budgetid == None):
      budgetid = find(budgetname, BUDGET, "create_budget_alert")

    if (budgetid == None):
      logger.error ("Failed to locate budget:" + budgetname + " no alert details will be set")
    else:
      if isinstance(budgetid, list):
        budgetid = budgetid[0]
        logger.warning ("only assigning alert to one budget")
        
      logger.info ("Located budget:" + budgetname + " ocid is:"+budgetid)

      request = oci.budget.models.CreateAlertRuleDetails()
      request.display_name = budgetalertname
      request.description = APP_DESCRIPTION
      request.type = request.TYPE_ACTUAL
      request.threshold_type = request.THRESHOLD_TYPE_ABSOLUTE
      request.threshold = 90.0
      request.message = alert_message
      request.recipients = alert_recipients

      client = oci.budget.BudgetClient(config_props)

      budget_alert = oci.budget.BudgetClient.create_alert_rule(client, budgetid, request)
      budget_alert_id = budget_alert.data.id
      #logger.info ("Budget Alert :" + budgetalertname + " ocid:"+ budget_alert_id)

  except oci.exceptions.ServiceError as se:
    logger.error ("ERROR - Create budget rule: ")
    logger.error (se) 
    logger.error ("alert message:" + alert_message)  
    logger.error ("alert recipients:" + alert_recipients)

  logger.debug (budget_alert_id)
  return budget_alert_id
##########


def username_to_oci_compatible_name(username):
  """
  XXXX

  **Parameters**
  * username : xx

  **Returns**
    The xx
  """  
  if (username != None):
    username = username.replace(".com", "")
    username = username.replace(".org", "")
    username = username.replace("@", "-")
    username = username.replace(".", "-")
    username = username.replace(" ", "")
    
  return username
##########


def tostring (object):
  """
  XXXX

  **Parameters**
  * object : xx

  **Returns**
    The xx
  """  
  result = "--- not Found ---"

  if (object != None):
    result = object
  
  return result
##########

def get_username(username):
  """
  XXXX

  **Parameters**
  * username : xx~

  **Returns**
    The username
  """  
  username = username_to_oci_compatible_name(username)

  if (username == None):
    username = config_props["new-username"]
    username_to_oci_compatible_name(username)
    #ToDo: add logic that says if empty string or None then throw error
  return username
##########


def get_parent_compartment_ocid(teamname):
  parent_compartment_ocid = None
  if (teamname != None):
    parent_compartment_ocid = find (teamname, COMPARTMENT)
    if (parent_compartment_ocid == None):
      raise LookupError ("No compartment found")
  else:
    parent_compartment_ocid = config_props[TENANCY]
  return parent_compartment_ocid
##########

def set_action_description(arg_elements):
  """
  XXXX

  **Parameters**
  * arg_elements : xx~

  """    
  global logger

  actiondesc = arg_elements[1]
  actiondesc.replace("'", "")
  actiondesc.replace('"', "")
  if (len (actiondesc) > 0):
    APP_DESCRIPTION = APP_DESCRIPTION_PREFIX + " - " + arg_elements[1]
    logger.debug ("Action description >"+APP_DESCRIPTION+"<")
##########

def get_budget_amount (budget_amount_override=None):
  """
  XXXX

  **Returns**
    The budget amount
  """    
  global logger, quota_props
  budget_amount = float(0)
  try:
    if (budget_amount_override != None):
      if (isinstance(budget_amount_override, str)):
        budget_amount_override = budget_amount_override.strip()
        if (len(budget_amount_override) > 0):
          budget_amount = float(budget_amount_override)
      elif (isinstance(budget_amount_override, float)):
        budget_amount = budget_amount_override
  except ValueError as ve:
    logger.error ("Error converting budget amount to a numeric", ve)
    
  if (budget_amount == 0) and (quota_props != None):
    budget = None
    if ("budget_definition" in quota_props):
      budget = quota_props["budget_definition"]
      if ("amount" in budget):
        budget_amount = budget["amount"]
        

  return budget_amount
##########

def get_definition_name (definition_type, override=None):
  """
  XXXX

  **Returns**
    The budget amount
  """    
  global logger, quota_props
  name=""
  try:
    if (override != None):
      if (isinstance(override, str)):
        budget_amount_override = budget_amount_override.strip()
        if (len(budget_amount_override) > 0):
          budget_amount = float(budget_amount_override)

  except ValueError as ve:
    logger.error ("Error converting budget amount to a numeric", ve)
    
  if (name == "") and (quota_props != None):
    if (definition_type in quota_props):
      container = quota_props[definition_type]
      if ("name" in container):
        name = container["name"]

  return name
##########

def list_quotas ():
  global logger
  
  limits_client = oci.limits.QuotasClient(config_props)

  list_quotas_response = limits_client.list_quotas(
    compartment_id=config_props[TENANCY],
    limit=1000,
    #lifecycle_state="ACTIVE"
    )

  # Get the data from response
  print(list_quotas_response.data)

##########


def delete(compartmentid, username=None, compartmentname=None, groupname=None, policyname=None):
  # https://oracle-cloud-infrastructure-python-sdk.readthedocs.io/en/latest/api/identity/models/oci.identity.models.BulkDeleteResourcesDetails.html
  request = oci.identity.models.BulkDeleteResourcesDetails()
  delete_list = []

  if (username != None):
    ocid = (find(username, USER))
    if (ocid != None):
      delete_list.append(ocid)

  if (compartmentname != None):
    ocid = (find(compartmentname, COMPARTMENT))
    if (ocid != None):
      delete_list.append(ocid)

  if (groupname != None):
    ocid = (find(groupname, GROUP))
    if (ocid != None):
      delete_list.append(ocid)

  if (policyname != None):
    ocid = (find(policyname, POLICY))
    if (ocid != None):
      delete_list.append(ocid)

    client = oci.core.IdentityClient(config_props)
    client.bulk_delete_resources(compartmentid, delete_list)


def main(*args):
  """
  XXXX

  **Parameters**
  * args : xx~

  """  
  global logger
  print (args)

  log_conf = LOGGER_CONF_DEFAULT
  logging.config.fileConfig(log_conf)
  logger = logging.getLogger()
  if (logger == None):
    print ("oh damn")

  init_config_filename(args)
  init_connection()

  budget_amount = float(-1)


  username = config_props.get(USER)
  teamname = config_props.get(TEAMNAME)
  email_address = config_props.get(EMAIL)
  quotaname = None
  budgetname = None


  delete = False
  list_quota=False
  validate_quota=False
  OPTIONS = ["Y", "YES", "T", "TRUE"]
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
      if (arg_elements[1].upper() in OPTIONS):
        delete = True
        logger.warning(DELETE + "option not available")

    elif (arg_elements[0]==VALIDATE_QUOTA):
      if (arg_elements[1].upper() in OPTIONS):
        validate_quota = True

    elif (arg_elements[0]==LIST):
      if (arg_elements[1].upper() in OPTIONS):
        list_quota = True
        logger.warning(DELETE + "option not available")

    elif (arg_elements[0]==CONFIGCLI or arg_elements[0]==QUOTACONFIGCLI):
      logger.debug ("processed " + arg + " separately")
    else:
        logger.warning(arg_elements[0] + " Unknown config, original value="+arg)


  init_quota()
  if (validate_quota):
    validate_quota_config()
    exit(0)

  quotaname = get_definition_name("quota_definition", quotaname)
  budgetname = get_definition_name("budget_definition", budgetname)

  if (list_quota):
    list_quotas()
    exit(0)

  budget_amount = get_budget_amount(budget_amount)

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

    if (config_props != None):
      alert_message = ""
      alert_recipients = ""
      if (parent_compartment_ocid != None):
        quota_ocid = create_compartment_quota (get_quota_statements(compartmentname, teamname),config_props[TENANCY],quotaname)
      else:
        quota_ocid = create_compartment_quota (get_quota_statements(compartmentname),config_props[TENANCY],quotaname)
      logger.info (quotaname + OCIDMSG + tostring(quota_ocid))

      try:
        alert_message = quota_props["budget_definition"][BUDGETALERTMSG] + " for Compartment:" + compartmentname
        logger.debug ("Alert message:" + alert_message)
      except Exception as err:
        logger.error (err)
        alert_message = "alert"

      try:
        alert_recipients = quota_props["budget_definition"][BUDGETALERTRECIPIENTS]
        logger.debug ("Alert recipients:" + alert_recipients)
      except Exception as err:
        logger.error (err)
        alert_recipients = "alert"

      budget_ocid = create_compartment_budget(budget_amount, compartment_ocid, budgetname)
      logger.info (CREATEDMSG + budgetname + OCIDMSG + tostring(budget_ocid))
      budgetalert_ocid =  create_budget_alert(budget_ocid, budgetname, budgetalertname, alert_recipients, alert_message)
      logger.info (CREATEDMSG + budgetalertname + OCIDMSG + tostring(budgetalert_ocid))

    else:
      logger.warning ("problem with quota props not existing - not quotas or budgets set")


if __name__ == "__main__":
  main(sys.argv[1:])