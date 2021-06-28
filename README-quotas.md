# oci-utilities about quotas





An example configuration for the quotas file is provided, called [example-quotas.json]().  A few of the example settings are currently disabled as the comments section will indicate as their appears to be a mismatch between the documentation and the implementation.

In the quotas file we have included Hyperlinks to the Oracle documentation.



Each of the attributes is described in the following table, with the naming using a dot notation from the root.



### Quota JSON File

| Property                           | Description                                                  | Example Value                                                |
| ---------------------------------- | ------------------------------------------------------------ | ------------------------------------------------------------ |
| budget_definition                  |                                                              |                                                              |
| budget_definition.amount           | The budget amount ass float                                  | 10.0                                                         |
| budget_definition.name             | Name of the budget to use                                    | myBudget                                                     |
| budget_definition.alert_message    | The text to include in the email sent when a budget limit is exceeded | Show me the money                                            |
| budget_definition.alert_recipients | The email address(es) to send the alerts to                  | joe@example.com, fred@example.com                            |
| quotas                             | list of families of quotas                                   |                                                              |
| quotas.description                 | Meaningful name - typically following the Oracle name        | analytics                                                    |
| quotas.comment                     | general comments                                             | this is my own comment                                       |
| quotas.deployment_grouping         | currently not used - potential for separating individual and group setup | individual or team                                           |
| quotas.documentation_url           | Link to the quota family documentation                       | https://docs.oracle.com/en-us/iaas/digital-assistant/doc/order-service-and-provision-instance.html |
| quotas.family_name                 | Description of the family - correlates back to Oracle's definition |                                                              |
| quotas.quota                       | List made up with the following values                       |                                                              |
| quotas.quota.quota_name            | Oracle defined quota within the family                       | see oracle documentation  e.g. analytics                     |
| quotas.quota.value                 | The value to set as a quota. Numeric integer                 | 3                                                            |
| quotas.quota.apply                 | Boolean flag indication whether the quota should be used. Rather than deleting records and not spotting what has been removed we use this to include/e | True or False                                                |

