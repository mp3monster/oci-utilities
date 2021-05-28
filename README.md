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

| Property      | Description                                                  | Example Value                     |
| ------------- | ------------------------------------------------------------ | --------------------------------- |
| user          | OCID for the user with admin privileges to run the script. As this information is going into a configuration file, we would recommend considering that a separate 'system user' be setup, so if someone accidentally shares/commits the configuration then it is less disruptive to block the user. The downside is you can't directly attribute the execution to an individual.  To address this - there is an an additional parameter called 'action_description' which will append to the description a message e.g. use action_description to the name of the individual. | ocid1.user.oc1..xxxxaaaaabbbbcccc |
| key_file      |                                                              | my-key-file.pem                   |
| tenancy       | OCID of the tenancy                                          | ocid1.user.oc1..wwwwwwwxxxxxyyyzz |
| fingerprint   | This is the finger print generated for the user in IAM / IDCS | bd:........................:0b:e4 |
| region        | The region that the maybe targets. For logic relating to user and compartment configuration, this is region agnostic. | us-ashburn-1                      |
|               | *Attributes to setup the new dev user - all prefixed with new_* |                                   |
| new-groupname |                                                              | PaaSTeam                          |
| new-username  |                                                              | joe.blogs@example.com             |
|               | *Other useful attributes*                                    |                                   |
| action_desc   | Any message to be appended to the action description         | run by monster                    |
|               |                                                              |                                   |



### Quota Properties File

| Property                                                  | Description | Example Value |
| --------------------------------------------------------- | ----------- | ------------- |
| *quota_*<[quota_family] *quota* [quota value]>*=*[number] |             |               |
| budget_alert_message                                      |             |               |
| budget_alert_recipients                                   |             |               |
| budget                                                    |             |               |



### Command Line Parameters

| Parameter   | Description | Example Value    |
| ----------- | ----------- | ---------------- |
| user        |             |                  |
| team        |             |                  |
| budget      |             |                  |
| config      |             |                  |
| quotaconfig |             |                  |
| action_desc |             | "run by monster" |



### Example of the command line:

```shell
py addUser.py user=phil.wilkins@capgemini.com acctiondesc="run by Phil" team=paas config=connection.properties
```

## Design / Implementation Approach

__TBD - to include__

- Choose to use Python ...
- naming convention applied
- find and continue
- structured query

## Known Issues

The following lists the currently known issues in the solution:

- Currently Quotas appear to only be possible on the first level compartments i.e. the children of the tenancy. Any child compartments (i.e. second level) do not support the idea of compartments.

- The logic currently doesn't support amending existing compartments, users and related policy constructs.



  ## Useful resources

  * https://github.com/pyenv-win/pyenv-win#installation -- the setting up of pyenv to help Python environments
  
  * https://realpython.com/effective-python-environment/#virtual-environments -- creating a virtual environment separation ontop of what pyenv does
  
  * https://docs.pipenv.org/en/latest/ -- the virtual environment extended version of PIP
  
  * https://oracle-cloud-infrastructure-python-sdk.readthedocs.io/en/latest/installation.html -- a quick guide to getting setup to develop with the SDK
  
  * https://mytechretreat.com/how-to-use-the-oci-python-sdk-to-make-api-calls/ 
  
  * https://github.com/oracle/oci-python-sdk/blob/master/examples/quotas_example.py -- quotas example update
  
  * https://docs.oracle.com/en-us/iaas/Content/Search/Concepts/querysyntax.htm - search query syntax
  
  * https://docs.oracle.com/en-us/iaas/Content/General/Concepts/resourcequotas.htm - setting quotas
  
  * https://docs.oracle.com/en-us/iaas/Content/Billing/Concepts/budgetsoverview.htm#Budgets_Overview - setting budgets

  
