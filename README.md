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

| Property     | Description | Example Valu |
| ------------ | ----------- | ------------ |
|              |             |              |
|              |             |              |
| new-username |             |              |



### Quota Properties File

| Property                                                  | Description | Example Valu |
| --------------------------------------------------------- | ----------- | ------------ |
| *quota_*<[quota_family] *quota* [quota value]>*=*[number] |             |              |
| budget_alert_message                                      |             |              |
| budget_alert_recipients                                   |             |              |
| budget                                                    |             |              |



### Command Line Parameters

| Parameter   | Description | Example Valu |
| ----------- | ----------- | ------------ |
| user        |             |              |
| team        |             |              |
| budget      |             |              |
| config      |             |              |
| quotaconfig |             |              |



### Example of the command line:

```shell
py addUser.py user=phil.wilkins@capgemini.com b=c team=paas config=connection.properties
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

  
