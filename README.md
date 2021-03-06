# oci-utilities



# addUser.py

This utility has been written to make it quick and easy to setup developers in development teams on OCI such that they have freedom to do as they wish within their compartment, they have some privileges in a team compartment and non in the root of the tenancy. The idea is the team compartment can be used for more expensive services that could be shared, consider OIC, ODA for example.  But also provide the developers with a 'sand-pit' in which they can do as they see fit.

The compartments have quotas and budgets set. To minimize accidentally spinning up resources that could consume a lot of cost, for example an Exadata server, or asking for petabytes of storage.

## Configuration

Configuration comes from three parts.

- A properties file that supplies the information necessary for the Python SDK to connect to the tenancy (this will require admin privileges). If not defined the default file is *connection.properties*
- A properties file to define the budget and quota values, this can be the same file as the connection properties, and uses by default the same file.
- Command line parameters in a name-value pair format which can be used to override most settings in the properties file(s), including defining the property file locations themselves.  An example of this is shown below. Not all the values can be command line overridden as for example setting up the quotas for example is not practical.

The following tables describe the property file values and the command line options.



### Connection Properties File

| Property           | Description                                                  | Example Value                     |
| ------------------ | ------------------------------------------------------------ | --------------------------------- |
| user               | OCID for the user with admin privileges to run the script. As this information is going into a configuration file, we would recommend considering that a separate 'system user' be setup, so if someone accidentally shares/commits the configuration then it is less disruptive to block the user. The downside is you can't directly attribute the execution to an individual.  To address this - there is an an additional parameter called 'action_description' which will append to the description a message e.g. use action_description to the name of the individual. | ocid1.user.oc1..xxxxaaaaabbbbcccc |
| key_file           |                                                              | my-key-file.pem                   |
| tenancy            | OCID of the tenancy                                          | ocid1.user.oc1..wwwwwwwxxxxxyyyzz |
| fingerprint        | This is the finger print generated for the user in IAM / IDCS | bd:........................:0b:e4 |
| region             | The region that the maybe targets. For logic relating to user and compartment configuration, this is region agnostic. | us-ashburn-1                      |
|                    | *Attributes to setup the new dev user - all prefixed with new_* |                                   |
| new-groupname      | name of the group that will have the parent compartment      | PaaSTeam                          |
| new-username       | the new user, this is more easily defined using the command line parameters | joe.blogs@example.com             |
|                    | *Other useful attributes*                                    |                                   |
| action_desc        | Any message to be appended to the action description         | run by monster                    |
| policiesconfigfile | Defines an alternate config file to the default              |                                   |
| common_groups      | list of space or comma separated group names that the user should be added to that already exist | testgrp,testgrp2                  |





### Command Line Parameters

| Parameter    | Description                                                  | Example Value                                                |
| ------------ | ------------------------------------------------------------ | ------------------------------------------------------------ |
| user         | name of the new user. you can provide this as an email address | joe@example.com                                              |
| team         | The name of the team the user is to be attributed to         | paas                                                         |
| budget       | Override of the budget amount in the configuration JSON      | 10000                                                        |
| config       | location of the configuration file                           | ./not_default_filename.properties                            |
| quotaconfig  | location of the JSON file to be used. This defaults to the local holder if not specified. The default is *policy-set.json* | ../myOtherConfig.son                                         |
| validate     | This will get the configuration files for quota (and later the policier to validated without actually applying the configuration). Validate will not run onto processing the request. | Accepted values are "y", "t", "true" - any other value is interpreted as false |
| idcs         | Tells the tool to establish the link between IAM and IDCS (IDP) | Accepted values are "y", "t", "true" - any other value is interpreted as false |
| action_desc  | overrides the config file setting                            | "run by monster"                                             |
| gen_policies | This flag will enable the processing of the policies configuration file | Accepted values are "y", "t", "true" - any other value is interpreted as false |
| add-to-grp   | a comma separated list of group names that the user will be added to | testgrp,testgrp2                                             |



### Example of the command line:

```shell
py addUser.py user=joe@example.com actiondesc="run by Phil" team=paas config=connection.properties
```

Depending upon your environment yoyu may nered to replace _py_ with _python_ or _python3_.

### Quota JSON File

The information about the construction of the quotas file is in [README-quotas.md]()

### Policies JSON File

The information about the construction of the quotas file is in [README-policies.md]()

## Deploying and running in the OCI Shell

The utility can be run on you laptop or desktop, but you may also consider deploying the utility to the OCI Shell. This can be done by either using a GIT clone command :

`git clone https://github.com/mp3monster/oci-utilities.git`

Then the update the configuration files connection.properties, your private key file, quotas and policies. We would recommend that you keep a copy of these in a separate folder so if you re-pull from GitHub then the config isn't overwritten by accident.

We also recommend setting up in ther .bashrc file a couple of alias commands to jump to the right folder and to copy in your connection.properties etc.

## Design / Implementation Approach

A lot of the background details to the design and implementation of this tool are available in this Oracle blog (TBD). Covering considerations of ...

- Why Python and the SDK is used
- Why this tool has been developed, including the parent child relationship with the compartments - note, that this is __NOT__ enforced.
- The use of structured queries against the OCI API - __recommended__ reading as this is a very powerful feature.
- Within the logic we have tried to apply a locate and build upon existing settings in most cases

## Improvements & Known Issues

Improvements have details included in [README-features.md]() and all issues and improvement ideas are tickets in GitHub

## Testing 

Testing for the changes isn't the easiest of tasks because trying to mock the SDK isn't a trivial exercise. But we have produced unit tests against logic that doesn't involve the SDK and some basic checks for existence of settings in OCI.

When preparing to test against a live environment then it can take upto 2 hours to delete a compartment, and if the compartment has relationships the delete can take time.  To address this we've added a sneaky option so that the compartment created is extended with a date-time stamp. This is controlled by a property in the properties file called  _UseDTGCompartmentNameIfRequired_ this has to exist and be set to true.

  ## Useful resources

  * https://github.com/pyenv-win/pyenv-win#installation -- the setting up of pyenv to help Python environments
  
  * https://realpython.com/effective-python-environment/#virtual-environments -- creating a virtual environment separation on top of what pyenv does
  
  * https://docs.pipenv.org/en/latest/ -- the virtual environment extended version of PIP
  
  * https://oracle-cloud-infrastructure-python-sdk.readthedocs.io/en/latest/installation.html -- a quick guide to getting setup to develop with the SDK
  
  * https://mytechretreat.com/how-to-use-the-oci-python-sdk-to-make-api-calls/ 
  
  * https://github.com/oracle/oci-python-sdk/blob/master/examples/quotas_example.py -- quotas example update
  
  * https://docs.oracle.com/en-us/iaas/Content/Search/Concepts/querysyntax.htm - search query syntax
  
  * https://docs.oracle.com/en-us/iaas/Content/General/Concepts/resourcequotas.htm - setting quotas
  
  * https://docs.oracle.com/en-us/iaas/Content/Billing/Concepts/budgetsoverview.htm#Budgets_Overview - setting budgets

  
