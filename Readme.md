##### What about users files?
##### create yaml file with information about ldap-user
##### For example:
```yaml
login: iivanov
first_name: Ivan
last_name: Ivanov
params:
  state: present
  email: iivanov@gmail.com
  discord_id: 1234567890
groups:
  - all
```
##### How can i run it?
##### You can run it the next command: ```python(3.*) -u ipa.test.local -l admin -p qwerty -d ./```

##### What is '-d'? 
##### It is argument, which search  yml/yaml files in directory