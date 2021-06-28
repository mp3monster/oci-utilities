# oci-utilities about policies





An example configuration for the policies file is provided, called  [example-policy-set.json]().  Unlike the quotas example this is not an exhaustive list of all the possible policies



### Quota JSON File

| Property                                    | Description                                                  | Example Value |
| ------------------------------------------- | ------------------------------------------------------------ | ------------- |
| policy-sets                                 | List of one or more groups of policies                       |               |
| policy-sets.policy-set-name                 |                                                              |               |
| policy-sets.apply                           |                                                              |               |
| policy-sets.comment                         |                                                              |               |
| policy-sets.deployment-grouping             |                                                              |               |
| policy-sets.policies                        | This is the level at which each group of policies are defined |               |
| policy-sets.policies.policy-expression      | This is the policy statement - values that can be substituted are enclosed with %. The list of substitutable values is described below |               |
| policy-sets.policies.contains-substitutions |                                                              |               |
| policy-sets.policies.apply                  |                                                              |               |



## Defined Subsitution Strings

- __%group%__ - the group that the policies should applied to
- __%compartment%__ -  this is also refered to as the parent compartment
- __%child_compartment%__ - this is the compartment made when we're using nesting

