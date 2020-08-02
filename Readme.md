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
##### 1) Use yml_combine.py for combined files
##### 2) Run ldap.py with this command: ```python(3.*) --domain ipa.test.local -l admin -p qwerty -i yml_combine.yaml ```
##### 3) check.py it's check validate for yaml file 
##### 4) converFiles.py it's give information about users and put in file