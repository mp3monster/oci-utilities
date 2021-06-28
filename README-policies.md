# oci-utilities about policies





An example configuration for the policies file is provided, called  [example-policy-set.json]().  Unlike the quotas example this is not an exhaustive list of all the possible policies.



The difference between the use of policies and quotas is that we can provide fine grained controls on who can actually interact with an OCI feature. That interactions can be bounded from view to full management. Whereas quotas is purely setting a limit on the amount of resource. Imposing a quota 0 is could be considered comparable to a restrictive policy e.g.. preventing the OCI user from managing a service. But policies to provide a more nuanced level of control.



### Quota JSON File

| Property                                    | Description                                                  | Example Value                                                |
| ------------------------------------------- | ------------------------------------------------------------ | ------------------------------------------------------------ |
| policy-sets                                 | List of one or more groups of policies.                      |                                                              |
| policy-sets.policy-set-name                 | The name of the policy group. This will be used as the display name of the policy set created in OCI | EmailPolicy                                                  |
| policy-sets.apply                           | Rather than adding and deleting policy sets, as suitable sets are developed we can simply switch them on or off from being deployed and applied. Value needs to be *true* or *false* | true                                                         |
| policy-sets.comment                         | This information gets incorporated into the policy description. Therefore should be short, but clear purpose of the policy group. | Allow users to use the service but not configure it.         |
| policy-sets.deployment-grouping             | This is currently just a place holder, within the quotas have a similar flag setting so we can create team quotas and individual limits as well. *Not currently used* | Individual or Team                                           |
| policy-sets.policies                        | This is the level at which each group of policies are defined |                                                              |
| policy-sets.policies.policy-expression      | This is the policy statement - values that can be substituted are enclosed with %. The list of substitutable values is described below | Allow group %group% to use logging-family in compartment %compartment% |
| policy-sets.policies.contains-substitutions | Boolean flag, indicating that the string needs to be parsed and have values substituted. We could scan all policy strings, but if we extend the substitution mechanism it is easier to actively flag the need to evaluation | true or false                                                |
| policy-sets.policies.apply                  | Like the apply on the set level we can switch individual policy statements on and off safely | true or false                                                |



## Defined Substitution Strings

- __%group%__ - the group that the policies should applied to
- __%compartment%__ -  this is also referred to as the parent compartment
- __%child_compartment%__ - this is the compartment made when we're using nesting

