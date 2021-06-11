#!/usr/bin/python

import sys
import oci
from oci.config import from_file
import logging
import logging.config
import json

class QUOTA_CONST:
  """
  Defines the constants related to the quotas configuration that used to navigate through the data structure
  """
  QUOTA_PROP_DEFAULT = "quotas.json"
  ## the following are attribute names in the JSON quota definition
  BUDGETALERTMSG="alert_message"
  BUDGET = "budget"
  BUDGETAMT = "amount"
  FAMILY="family_name"
  QUOTA="quota"

  QUOTAS = "quotas"
  DESC="description"
  DOC_URL="documentation_url"
  QTA_NAME="quota_name"
  NAME="name"
  QTA_VALUE="value"
  QTA_APPLY="apply"

  BUDGET_ALERT="create_budget_alert"
  QTA_DEF="quota_definition"
  BGT_DEF="budget_definition"
##########

class CONFIG_CONST:
  """
  Definition of the constant values relating to the configuration properties file
  """
  CONN_PROP_DEFAULT = "connection.properties"

  NEW_USER="new-username"
  ACTIONDESCRIPTION="actiondesc"
  EMAIL="email"
  TEAMNAME="team"
  TENANCY = "tenancy"
  USER="user"
  APP_DESCRIPTION_PREFIX = "automated setup using Python SDK"

##########
class CLI_CONST:
  """
  Defines the constants relating to the processing of command line parameters
  """
  CONFIG_CLI="config"
  QUOTA_CONFIG_CLI="quotaconfig"
  """The CLI names used to specify the locations of the config files"""

  OPTIONS = ["Y", "YES", "T", "TRUE"]
  DELETE="delete"
  ACTIONDESCRIPTION= CONFIG_CONST.ACTIONDESCRIPTION
  USER = "user"
  EMAIL=CONFIG_CONST.EMAIL
  TEAMNAME=CONFIG_CONST.TEAMNAME
  LIST="listquota"
  VALIDATE_QUOTA="validate"
  LOGGING="logconf"
##########


class QRY_CONST:
  """
  Defines the constants needed to work with the the structured queries on the SDK
  """

  USER="user"
  COMPARTMENT="compartments"
  GROUP="group"
  ALL = "all"
  NAMED="named"
  POLICY="policy"
  QUOTA="quota"
  QRY_TYPE='Structured'
  BUDGET="budget"
##########

class TFM_CONST:
  """
  Constants relating to the handling of Terraform command communication
  """
  ACTION="action" #identifies a CSV identifying the requested actions to be performed
  QUOTA_CONFIG_FN="quotaconfigfile" # pass to override the default quota file
  CONFIG_FN="configfile" # pass to override the default config file
##########


config_props = None
"""Holds the configuration properties loaded. This configuration needs to 
include the properties necessary for the Python SDK to connect with OCI"""

quota_props = None
"""Holds the configuration properties that are used to define the quotas 
to be applied. The quotas properties need to follow a naming convention"""

config_filename = None
quota_config_filename = None

logger : logging.Logger
LOGGER_CONF_DEFAULT= "logging.properties"
"""Python logger used within this module"""

app_description = CONFIG_CONST.APP_DESCRIPTION_PREFIX



query_dictionary = {
  QRY_CONST.USER: {QRY_CONST.ALL : "query user resources where inactiveStatus = 0", QRY_CONST.NAMED : "query user resources where displayname = "},
  QRY_CONST.COMPARTMENT: {QRY_CONST.ALL : "query compartment resources where inactiveStatus = 0", QRY_CONST.NAMED : "query compartment resources where displayname = "},
  QRY_CONST.GROUP: {QRY_CONST.ALL : "query group resources where inactiveStatus = 0", QRY_CONST.NAMED : "query group resources where displayname = "},
  QRY_CONST.POLICY: {QRY_CONST.ALL : "query policy resources where inactiveStatus = 0", QRY_CONST.NAMED : "query policy resources where displayname = "},
  QRY_CONST.BUDGET: {QRY_CONST.ALL : "query budget resources where inactiveStatus = 0", QRY_CONST.NAMED : "query budget resources where displayname = "},
  QRY_CONST.QUOTA: {QRY_CONST.ALL : "query quota resources where inactiveStatus = 0", QRY_CONST.NAMED : "query quota resources where displayname = "}
}
"""A dictionary of queries to be used to obtain the OCID(s) for various types of OCI objects being used"""
##########


def init_tf_filenames (request_json):
  global config_filename, quota_config_filename, logger 
  logger.debug ("checking to see if TF ")
  if (config_filename == None):
    config_filename = CONFIG_CONST.CONN_PROP_DEFAULT
  if(quota_config_filename == None):
    quota_config_filename = QUOTA_CONST.QUOTA_PROP_DEFAULT

  if (request_json != None):
    if (TFM_CONST.CONFIG_FN in request_json):
      fn = request_json[TFM_CONST.CONFIG_FN]
      fn.strip()
      if (len(fn) > 1):
        config_filename=fn
        logger.debug ("TF data changed config file location to " + fn)
    if (TFM_CONST.QUOTA_CONFIG_FN in request_json):
      fn = request_json[TFM_CONST.QUOTA_CONFIG_FN]
      fn.strip()
      if (len(fn) > 1):
        quota_config_filename=fn
        logger.debug ("TF data changed quota config file location to " + fn)        

##########

def init_cli_filenames ():
  """
    Extracts the filenames for the configuration files from command line arguments
    Sets up the config filename variables ready to be used
    Expecting 2 files (could be mapped to the same file)
      - Connection Based Properties
      - Quota based properties
    
    """
  global config_filename, quota_config_filename, logger
  if (config_filename == None):
    config_filename = CONFIG_CONST.CONN_PROP_DEFAULT
  if(quota_config_filename == None):
    quota_config_filename = QUOTA_CONST.QUOTA_PROP_DEFAULT

  for arg in sys.argv[1:]:
    arg_elements = arg.split("=")
    if (arg_elements[0]==CLI_CONST.CONFIG_CLI):
      config_filename= arg_elements[1]
      logger.info ("config file >" + config_filename + "<") 
    elif (arg_elements[0]==CLI_CONST.QUOTA_CONFIG_CLI):
      quota_config_filename= arg_elements[1]
      logger.info ("quota config file >" + quota_config_filename + "<") 
##########

def validate_quota_config(check_minor_attributes=False):
  """
  Scans through the quota_props object checking the structure, ensuring that the necessary
  properties are configured. The errors are counted and reported. All the information regarding 
  the configuration is addressed by reporting through the logger

  Args:
      check_minor_attributes (bool, optional): [flags wither minor issues should be evaluated]. Defaults to False.
  """
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
    for quota_family in quota_props[QUOTA_CONST.QUOTAS]:
      if (QUOTA_CONST.DESC in quota_family):
        family_desc = quota_family[QUOTA_CONST.DESC]
      else:
        family_desc = "--Not Defined--"
      if (QUOTA_CONST.DESC not in quota_family) or (len(quota_family[QUOTA_CONST.DESC]) < 3):
        logger.warning ("Quota description on " + family_desc + "( family group " + str(family_count) + ") is incomplete")
        warning_count+=1
      if (QUOTA_CONST.FAMILY not in quota_family) or (len(quota_family[QUOTA_CONST.FAMILY]) < 3):
        logger.warning ("Quota Family Name on (" +family_desc+") family count " + str(family_count) + " is incomplete")
        warning_count+=1
      if (QUOTA_CONST.QUOTA not in quota_family) or (len(quota_family[QUOTA_CONST.QUOTA]) == 0):
        logger.warning ("No individual quotas set on (" +family_desc+") family count " + str(family_count) + " is incomplete")
        warning_count+=1
      if (check_minor_attributes):
        if (QUOTA_CONST.DOC_URL not in quota_family) or (len(quota_family[QUOTA_CONST.DOC_URL]) < 9):
          logger.warning ("Documentation_url on (" +family_desc+") family count " + str(family_count) + " is incomplete")
          minor_warning_count+=1
        if ("comment" not in quota_family) or (len(quota_family["comment"]) < 1):
          logger.warning ("Documentation_url on (" +family_desc+") family count " + str(family_count) + " is incomplete")
          minor_warning_count+=1

      else:
        quota_count=1
        for quota in quota_family[QUOTA_CONST.QUOTA]:
          try:
            quota_name = quota[QUOTA_CONST.QTA_NAME]
            if (QUOTA_CONST.QTA_NAME not in quota):
              logger.warning ("Quota name in family " + str(family_count) + " is missing")
              quota_name = "--Not Defined--"
              warning_count+=1
            else:
              if (len(quota[QUOTA_CONST.QTA_NAME] ) < 3):
                logger.warning ("Quota name in family " + str(family_count) + " is incomplete")
                warning_count+=1                  
            if (QUOTA_CONST.QTA_VALUE not in quota) or (quota[QUOTA_CONST.QTA_VALUE] < 0):  
              msg = family_desc+"."+quota_name+ " family " + str(family_count) + " quota no " + str(quota_count)
              logger.warning (msg + " -- value not correct")
              warning_count+=1
            if (QUOTA_CONST.QTA_APPLY not in quota): 
              msg = family_desc+"."+quota_name+ " family " + str(family_count) + " quota no " + str(quota_count)
              logger.warning (msg + " -- apply to specified")  
              warning_count+=1
            else:
              if (quota[QUOTA_CONST.QTA_APPLY] == False):  
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
  Loads the quota information from the properties file, converts to JSON object and closes the file.
  The filename and quota properties data structure are global values
  """
  global logger, quota_props, quota_config_filename

  msg = "Quota file:"+quota_config_filename
  #logger.debug(msg)
  file = open(quota_config_filename,"r")

  quota_props = json.load(file)
  file.close()

 ##########
 
def init_connection():
  """
  Using the provided filename load the configuration file with all the values
  needed by the Python SDK to connect to OCI
    
  """
  global config_props
  config_props = from_file(file_location=config_filename)     
  oci.config.validate_config(config_props)
##########

def get_quota_statements_for_family(quota_family, quota_statements, compartment):
  """Processes each family to construct the relevant quota statements

  Args:
      quota_family (str): The JSON representation of a quota family configuration
      quota_statements (list[]): The statements to provide to OCI to control quotas
      compartment (str): name of the compartment to apply the constraint to

  Returns:
      str[]: The updated quota_statements construct
  """
  global logger
  if (QUOTA_CONST.QUOTA in quota_family):
        for quota in quota_family[QUOTA_CONST.QUOTA]:
          if ((QUOTA_CONST.QTA_APPLY not in quota) and (QUOTA_CONST.FAMILY not in quota_family) and 
              (QUOTA_CONST.QTA_NAME not in quota) and (QUOTA_CONST.QTA_VALUE not in quota_family)):
            logger.error ("Missing data in the quotas configuration")
          else:
            if (quota[QUOTA_CONST.QTA_APPLY]):
              stmt = ("Set " + quota_family[QUOTA_CONST.FAMILY] + 
                      " quota " + quota[QUOTA_CONST.QTA_NAME] + " to " + 
                      quota_family[QUOTA_CONST.QTA_VALUE] + " in compartment " + compartment)
              logger.debug (stmt)
              quota_statements.append(stmt)
  else:
    logger.warning ("No individual quotas")

  return quota_statements
##########


def get_quota_statements (compartmentname:str, parent_compartment:str = None):
  """
  Loads the quota configuration rules from the properties file to setup.
    The properties are used to populate a series of quotas

  Args:
      compartmentname (str): The compartment name that the quota is to be applied to
      parent_compartment (str, optional): The name of the parent compartment if a parent exists. Defaults to None.

  Returns:
      str[]: list of string statements
  """

  global quota_props, config_props, logger
  quota_statements = []

  # sort out which compartment
  if (parent_compartment != None) and (len(parent_compartment) > 0):
    compartment = parent_compartment+":"+compartment

  if (QUOTA_CONST.QUOTAS in quota_props):
    for quota_family in quota_props[QUOTA_CONST.QUOTAS]:
      quota_statements = get_quota_statements_for_family(quota_family, quota_statements, compartment)
  else:
    logger.warning ("No quotas in quota config")

  return quota_statements
##########



def find(name=None, query_type=QRY_CONST.USER, query_msg="", print_find = False):
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
  query = query_dictionary[query_type][QRY_CONST.ALL]
  if (name != None):
    query = query_dictionary[query_type][QRY_CONST.NAMED]+"'" + name + "'"
    # print (query)

  search_client = oci.resource_search.ResourceSearchClient(config_props)
  structured_search = oci.resource_search.models.StructuredSearchDetails(query=query,
    type=QRY_CONST.QRY_TYPE,
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

  Args:
      username : the OCI friendly username
      compartment_id : the compartment to associate the user id to
      email : User's email address

  Returns:
      the OCID for the username
  """  
  ##Todo: Need to set the IDCS side of the user up
  global logger, config_props

  user_ocid = find(username, QRY_CONST.USER, "pre create user check")
  if (user_ocid == None):
    try:
      request = oci.identity.models.CreateUserDetails()
      request.compartment_id = compartment_id
      request.name = username
      request.description = app_description
      if ((email != None) and (len(email) > 3)):
        request.email = email
        logger.debug ("request.email set")
      identity = oci.identity.IdentityClient(config_props)
      user = identity.create_user(request)
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
  idp.compartment_id = config_props[CONFIG_CONST.TENANCY]
  idp.name = 'idcs_name'
  idp.description = 'idcs_description'
  idp.product_type = 'IDCS'
  idp.protocol = 'SAML2'
  idp.metadata_url = metadata_url # The URL for retrieving the identity provider’s metadata, which contains information required for federating.
  idp.metadata = metadata
  # The XML that contains the information required for federating.
  # load local file?? Isnt this creating rhe federation?

  iam_client.create_identity_provider(idp)
  return idp.data.id

##########



def create_compartment (parent_compartment_id, compartmentname):
  """
  Creates the compartment as a child to another identified compartment. 
  If parent_compartment_id is not provided then we make a top level compartment

  Args
    compartmentname : the name of the compartment to create
    parent_compartment_id : the parent compartment if there is one. If unset 

  Returns:
    The OCID for the compartment created
  """   
  global logger, config_props

  compartment_id = None
  try:
    request = oci.identity.models.CreateCompartmentDetails()
    request.description = app_description
    request.name = compartmentname
    request.compartment_id = parent_compartment_id
    identity = oci.identity.IdentityClient(config_props)
    compartment = identity.create_compartment(request)
    compartment_id = compartment.data.id
    logger.info ("Compartment Id:" + compartment_id)

    logger.info ("waiting on compartment state")
    #client = oci.core.IdentityClient(config_props)
    oci.wait_until(identity, identity.get_compartment(compartment_id), 'lifecycle_state', 'ACTIVE')    
   
  except oci.exceptions.ServiceError as se:
    logger.error ("ERROR - Create Compartment: "+compartmentname + " child of " + parent_compartment_id)
    logger.error (se)

  return compartment_id
##########


def create_user_compartment_policies (groupname, policyname, compartmentid, compartmentname):
  """
  Creates a privileges policy for the user on the compartment. This assumes that we're
  working with the child compartment, as the parent has more restricted policies.

  ToDo: Extend so can set a more restrictive set of policies for a parent compartment

  Args:
      groupname : as policies are linked to groups not individuals, we need the groupname
      policyname : name to use for this policy
      compartmentid : the compartment that this policy is linked to
      compartmentname : the compartment name

  Returns:
    The OCID for policy created
  """   
  global logger, config_props

  policy_ocid = None
  policy_ocid = find (policyname, QRY_CONST.POLICY)
  if (policy_ocid == None):  
    try:
      manage_policy = "Allow group " + groupname +" to manage all-resources in compartment "+compartmentname
      logger.info ("add policy: " + manage_policy)
      request = oci.identity.models.CreatePolicyDetails()
      request.description = app_description
      request.name = policyname
      request.compartment_id = compartmentid
      request.statements = [manage_policy]

      identity = oci.identity.IdentityClient(config_props)
      policy = identity.create_policy(request)
      policy_ocid = policy.data.id
    except oci.exceptions.ServiceError as se:
      logger.error ("ERROR - Create Policies: " + policyname +" group is"+groupname+ " in " +compartmentname)
      logger.error (se)

  return policy_ocid
##########


def create_group (groupname):
  """
  Creates the the group if the named group doesn't exist.

  Args:
  * groupname : name of the group to create
  **Returns**
    The OCID for policy created
  """  
  global logger, config_props

  group_ocid = find(groupname, QRY_CONST.GROUP, "pre create group check")
  if (group_ocid == None):
    try:
      request = oci.identity.models.CreateGroupDetails()
      request.compartment_id = config_props[CONFIG_CONST.TENANCY]
      request.name = groupname
      request.description = app_description
      identity = oci.identity.IdentityClient(config_props)
      group = identity.create_group(request)
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

  Args:
  * quota_statements : the statements that have been assembled from the quotas configuration source
  * compartmentid : the OCID of the compartment to apply the quota to
  * quotaname : name of the quota
  **Returns**
    The OCID for the quota definition
  """  
  global logger

  quota_ocid = find(quotaname, QRY_CONST.QUOTA, "pre create quota check")
  if (quota_ocid == None):
    try:
      request = oci.limits.models.CreateQuotaDetails()
      request.compartment_id = compartmentid
      request.statements = quota_statements

      logger.info ("Quota to be applied:")
      logger.info (quota_statements)

      request.description = app_description
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

  Args:
  * budget_amount : xx
  * compartmentid : xx
  * budgetname : xx
  **Returns**
    The OCID for the budget object
  """ 
  global logger

  budget_id = None
  budget_id = find(budgetname, QUOTA_CONST.BUDGET, "pre create budget check")
  if (budget_id == None):
    try:
      request = oci.budget.models.CreateBudgetDetails()
      request.compartment_id = config_props[CONFIG_CONST.TENANCY]
      request.description = app_description
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

  Args:
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
      budgetid = find(budgetname, QUOTA_CONST.BUDGET, QUOTA_CONST.BUDGET_ALERT)

    if (budgetid == None):
      logger.error ("Failed to locate budget:" + budgetname + " no alert details will be set")
    else:
      if isinstance(budgetid, list):
        budgetid = budgetid[0]
        logger.warning ("only assigning alert to one budget")
        
      logger.info ("Located budget:" + budgetname + " ocid is:"+budgetid)

      request = oci.budget.models.CreateAlertRuleDetails()
      request.display_name = budgetalertname
      request.description = app_description
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

  Args:
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
  Produces a string representation of the value provided. Addresses the possibility that the value passed in is None
  If the received value is None then --- not Found --- is returned

  Args:
      object (any): The object to have a string representation, this could be None

  Returns:
      str: the string representation
  """

  result = "--- not Found ---"

  if (object != None):
    result = object
  
  return result
##########

def get_username(username):
  """
  Receives the current username object. If a value is not set then the value will be retrieved from the
  configuration properties. The username is processed to remove any characters that could cause OCI trouble

  Args:
      username (str): A string or None value. This is the currently set value if one has been set.

  Returns:
      str: A sanitized username string
  """
  username = username_to_oci_compatible_name(username)

  if (username == None):
    username = config_props[CONFIG_CONST.NEW_USER]
    username_to_oci_compatible_name(username)
    #ToDo: add logic that says if empty string or None then throw error
  return username
##########


def get_parent_compartment_ocid(teamname):
  """
  Retrieves the OCID for the compartment based on the team name (assuming the model of root -- team -- individual
  structure of compartments.

  Args:
      teamname (str): name of the team level compartment

  Returns:
      str: The OCId or None - None is only returned in the event of an internal error
  """
  global logger

  parent_compartment_ocid = None
  try:
    if (teamname != None):
      parent_compartment_ocid = find (teamname, QRY_CONST.COMPARTMENT)
      if (parent_compartment_ocid == None):
        raise LookupError ("No compartment found")
    else:
      parent_compartment_ocid = config_props[CONFIG_CONST.TENANCY]
  except LookupError as le:
    logger.error ("Compartment lookup failed", le)

  return parent_compartment_ocid
##########

def set_app_description(arg_elements):
  """
  Used to clean up the application label name incase it has been escaped when being passed over
  The value is applied to a global value
  Args:
      arg_elements (str[]): key value pair to represent the action value
  """
  global logger, app_description

  actiondesc = arg_elements[1]
  actiondesc.replace("'", "")
  actiondesc.replace('"', "")
  if (len (actiondesc) > 0):
    app_description = CONFIG_CONST.APP_DESCRIPTION_PREFIX + " - " + arg_elements[1]
    logger.debug ("App description >"+app_description+"<")
##########

def get_budget_amount (budget_amount_override=None):
  """
Uses the quota JSON object holding the quota and budget values the standard budget amount is retrieved. This value is only used
if the received override value is provided

  Args:
      budget_amount_override (float or str, optional): Representation of the budget value which will be used to override 
      the configuration file. Defaults to None.

  Returns:
      float: the budget value to use
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
    if (QUOTA_CONST.BGT_DEF in quota_props):
      budget = quota_props[QUOTA_CONST.BGT_DEF]
      if (QUOTA_CONST.BUDGETAMT in budget):
        budget_amount = budget[QUOTA_CONST.BUDGETAMT]
        
  return budget_amount
##########

def get_definition_name (definition_type, override=None): 
  """
  Navigates the definition structure for both budgets and quotas in our JSON structure and retrieves the name value

  Args:
      definition_type (str): indication of whether the required value is for the budget or quota
      override ([type], optional): [description]. Defaults to None.

  Returns:
      str: the name value or an empty string
  """

  global logger, quota_props
  name=""
  try:
    if (override != None)and (isinstance(override, str)):
      budget_amount_override = budget_amount_override.strip()
      if (len(budget_amount_override) > 0):
        budget_amount = float(budget_amount_override)

  except ValueError as ve:
    logger.error ("Error converting budget amount to a numeric", ve)
    
  if (name == "") and (quota_props != None):
    if (definition_type in quota_props):
      container = quota_props[definition_type]
      if (QUOTA_CONST.NAME in container):
        name = container[QUOTA_CONST.NAME]

  return name
##########

def list_quotas ():
  global logger
  
  limits_client = oci.limits.QuotasClient(config_props)

  list_quotas_response = limits_client.list_quotas(
    compartment_id=config_props[CONFIG_CONST.TENANCY],
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
    ocid = (find(username, QRY_CONST.USER))
    if (ocid != None):
      delete_list.append(ocid)

  if (compartmentname != None):
    ocid = (find(compartmentname, QRY_CONST.COMPARTMENT))
    if (ocid != None):
      delete_list.append(ocid)

  if (groupname != None):
    ocid = (find(groupname, QRY_CONST.GROUP))
    if (ocid != None):
      delete_list.append(ocid)

  if (policyname != None):
    ocid = (find(policyname, QRY_CONST.POLICY))
    if (ocid != None):
      delete_list.append(ocid)

    client = oci.core.IdentityClient(config_props)
    client.bulk_delete_resources(compartmentid, delete_list)

def init_logger():
  global logger
  log_conf = LOGGER_CONF_DEFAULT
  logging.config.fileConfig(log_conf)
  logger = logging.getLogger()
  if (logger == None):
    print ("oh damn")
##########

def terraform_main():
  global logger
  init_logger()
  request = sys.stdin.read()
  response = None
  action = ""

  request_json = json.loads(request)
  if (TFM_CONST.ACTION in request_json):
    action = request_json[TFM_CONST.ACTION]
  else:
    logger.error ("No action supplied")
    response = '{"error":"no_action"}'

  logger.debug(action)

  init_connection()
  init_quota()

  sys.out.write(response)
  exit(0)
##########

def cli_main(*args):
  """
  XXXX

  **Parameters**
  * args : xx~

  """  
  global logger
  init_logger()
  init_cli_filenames()
  init_connection()

  budget_amount = float(-1)


  username = config_props.get(CONFIG_CONST.USER)
  teamname = config_props.get(CONFIG_CONST.TEAMNAME)
  email_address = config_props.get(CONFIG_CONST.EMAIL)
  quotaname = None
  budgetname = None

  delete = False
  list_quota=False
  validate_quota=False
  
  CLIMSG = "CLI set "

  if CONFIG_CONST.ACTIONDESCRIPTION in config_props:
      set_app_description([CONFIG_CONST.ACTIONDESCRIPTION, config_props[CONFIG_CONST.ACTIONDESCRIPTION]])

  for arg in sys.argv[1:]:
    arg_elements = arg.split("=")

    if (arg_elements[0]==CLI_CONST.USER):
      username = arg_elements[1]
      logger.info (CLIMSG+CLI_CONST.USER+"  >" + username + "<")    

    elif (arg_elements[0]==CLI_CONST.TEAMNAME):
      teamname= arg_elements[1]
      logger.info (CLIMSG+CLI_CONST.TEAMNAME+"  >" + teamname + "<")    

    elif (arg_elements[0]==CLI_CONST.EMAIL):
      email_address=  arg_elements[1]
      email_address = email_address.strip()
      if (len(email_address) < 3):
          email_address = config_props(CONFIG_CONST.EMAIL)
          logger.warn("CLI setting for " + CONFIG_CONST.EMAIL + " ignored, value too short")
      logger.info (CLIMSG+CLI_CONST.EMAIL+"  >" + email_address + "<")    

    elif (arg_elements[0]==QUOTA_CONST.BUDGET):
      budgetname = arg_elements[1]
      logger.info (CLIMSG+QUOTA_CONST.BUDGET+"  >" + arg_elements[1] + "<")      

    elif (arg_elements[0]==QUOTA_CONST.BUDGETAMT):
      budget_amount = get_budget_amount(arg_elements[1])
      logger.info (CLIMSG+QUOTA_CONST.BUDGETAMT+"  >" + budget_amount + "<")

    elif (arg_elements[0]==CLI_CONST.ACTIONDESCRIPTION):
      set_app_description(arg_elements[1])
      logger.info (CLIMSG+CLI_CONST.ACTIONDESCRIPTION+"  >" + arg_elements[1] + "<")

    elif (arg_elements[0]==CLI_CONST.LOGGING):
      log_conf= arg_elements[1]
      log_conf.strip()
      if (len(log_conf) < 1):
        log_conf = LOGGER_CONF_DEFAULT
      logging.config.fileConfig(log_conf)
      logger = logging.getLogger()

    elif (arg_elements[0]==CLI_CONST.DELETE):
      if (arg_elements[1].upper() in CLI_CONST.OPTIONS):
        delete = True
        logger.warning(CLI_CONST.DELETE + "option not available")

    elif (arg_elements[0]==CLI_CONST.VALIDATE_QUOTA):
      if (arg_elements[1].upper() in CLI_CONST.OPTIONS):
        validate_quota = True

    elif (arg_elements[0]==CLI_CONST.LIST):
      if (arg_elements[1].upper() in CLI_CONST.OPTIONS):
        list_quota = True

    elif (arg_elements[0]==CLI_CONST.CONFIG_CLI or arg_elements[0]==CLI_CONST.QUOTA_CONFIG_CLI):
      logger.debug ("processed " + arg + " separately")
    else:
        logger.warning(arg_elements[0] + " Unknown config, original value="+arg)
##########


  init_quota()
  if (validate_quota):
    validate_quota_config()
    exit(0)

  quotaname = get_definition_name(QUOTA_CONST.QTA_DEF, quotaname)
  budgetname = get_definition_name(QUOTA_CONST.BGT_DEF, budgetname)

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
  OCID_MSG = " ocid="
  logger.info (LOCATEDMSG + username + OCID_MSG + tostring(find(username, QRY_CONST.USER)))
  logger.info (LOCATEDMSG + compartmentname + OCID_MSG + tostring(find(compartmentname, QRY_CONST.COMPARTMENT)))
  logger.info (LOCATEDMSG + groupname + OCID_MSG + tostring(find(groupname, QRY_CONST.GROUP)))
  logger.info (LOCATEDMSG + policyname + OCID_MSG + tostring(find(policyname, QRY_CONST.POLICY)))

  if (search_only == False):

    parent_compartment_ocid = get_parent_compartment_ocid(teamname)

    compartment_ocid = find(compartmentname, QRY_CONST.COMPARTMENT)
    if (compartment_ocid == None):
      compartment_ocid = create_compartment (parent_compartment_ocid, compartmentname)


    group_ocid = create_group(groupname)
    logger.info (groupname + OCID_MSG + tostring(group_ocid))

    user_ocid = create_user (username, config_props[CONFIG_CONST.TENANCY], email_address)
    logger.info (username + OCID_MSG + tostring(user_ocid))


    policyname_ocid = create_user_compartment_policies (groupname, policyname, compartment_ocid, compartmentname)
    logger.info (policyname + OCID_MSG + tostring(policyname_ocid))

    if (config_props != None):
      alert_message = ""
      alert_recipients = ""
      if (parent_compartment_ocid != None):
        quota_ocid = create_compartment_quota (get_quota_statements(compartmentname, teamname),config_props[CONFIG_CONST.TENANCY],quotaname)
      else:
        quota_ocid = create_compartment_quota (get_quota_statements(compartmentname),config_props[CONFIG_CONST.TENANCY],quotaname)
      logger.info (quotaname + OCID_MSG + tostring(quota_ocid))

      try:
        alert_message = quota_props[QUOTA_CONST.BGT_DEF][QUOTA_CONST.BUDGETALERTMSG] + " for Compartment:" + compartmentname
        logger.debug ("Alert message:" + alert_message)
      except Exception as err:
        logger.error (err)
        alert_message = "alert"

      try:
        alert_recipients = quota_props[QUOTA_CONST.BGT_DEF][QUOTA_CONST.BUDGETALERTRECIPIENTS]
        logger.debug ("Alert recipients:" + alert_recipients)
      except Exception as err:
        logger.error (err)
        alert_recipients = "alert"

      budget_ocid = create_compartment_budget(budget_amount, compartment_ocid, budgetname)
      logger.info (CREATEDMSG + budgetname + OCID_MSG + tostring(budget_ocid))
      budgetalert_ocid =  create_budget_alert(budget_ocid, budgetname, budgetalertname, alert_recipients, alert_message)
      logger.info (CREATEDMSG + budgetalertname + OCID_MSG + tostring(budgetalert_ocid))

    else:
      logger.warning ("problem with quota props not existing - not quotas or budgets set")

##########
def main():
    if sys.argv[0] != "addUser.py":
      # we know that this has been a Terraform invoked call
      print ("Executing TF process")
      terraform_main()
    else:
      print ("Executing CLI")
      cli_main(sys.argv[1:])

##########
if __name__ == "__main__":
      main()
