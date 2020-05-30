import argparse
import glob
import urllib3
import yaml
from python_freeipa import ClientLegacy

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def args():
    arg = argparse.ArgumentParser()
    arg.add_argument('-u', type=str, help='FreeIPA url')
    arg.add_argument('-l', type=str, help='FreeIPA login')
    arg.add_argument('-p', type=str, help='FreeIPA password')
    arg.add_argument('-d', type=str, help='Search in dir')
    argument = vars(arg.parse_args())
    return argument


def connect(ipa_host, ipa_user, ipa_password):
    client = ClientLegacy(ipa_host, version='2.215', verify_ssl=False)
    client.login(ipa_user, ipa_password)
    return client


arguments = args()
client = connect(arguments['u'], arguments['l'], arguments['p'])


# --Parsing of yml/yaml files


def parser_yml():
    list_user_info = []
    ext = ['yml', 'yaml']
    for ext in ext:
        for file_yml in glob.glob(arguments['d'] + '/*.' + ext):
            with open(file_yml, 'r') as f:
                pars = yaml.safe_load(f)
                list_user_info.append(pars)
            f.close()
    return list_user_info


# --Create users list


def list_ldap_users():
    list_ldap_users = []
    list_users_login = []
    list_ldap_users.append(client.user_find())
    for i in list_ldap_users:
        for login in i['result']:
            for x in login['uid']:
                list_users_login.append(x)
    return list_users_login


# --Create users and group list


def list_ldap():
    list_ldap = []
    list_users = []
    list_ldap.append(client.user_find())
    for i in list(list_ldap):
        for x in i['result']:
            try:
                del x['cn']
                del x['homedirectory']
                del x['sn']
                del x['gecos']
                del x['objectclass']
                del x['ipauniqueid']
                del x['displayname']
                del x['initials']
                del x['mepmanagedentry']
                del x['krbprincipalname']
                del x['loginshell']
                del x['gidnumber']
                del x['mail']
                del x['givenname']
                del x['krbcanonicalname']
                del x['uidnumber']
                del x['nsaccountlock']
                del x['preserved']
                del x['dn']
                del x['telephonenumber']
                list_users.append(x)
            except:
                None
    return list_users


# --Create user in ldap


def create_users(users, ldap_users):
    list_users_login = []
    for login in users:
        list_users_login.append(login['login'])
    list_for_add_users = list(
        set(list_users_login) - set(ldap_users))
    print(list_for_add_users)
    for i in list_for_add_users:
        for x in users:
            if i == x['login']:  
                client.user_add(
                    username=i,
                    first_name=x['first_name'],
                    last_name=x['last_name'],
                    full_name=x['first_name'] + ' ' + x['last_name']
                )
                for group in x['groups']:
                    client.group_add_member(
                        group=group,
                        users=i
                    )
                print("User: " + format(i) + " was created")
            else:
                None


# --Add modifications for users


def user_mod(users):
    for x in users:
        try:
            if x['params']['state'] == "present":
                client.user_mod(
                    username=x['login'],
                    first_name=x['first_name'],
                    last_name=x['last_name'],
                    telephone_number=x['params']['discord_id'],
                    mail=x['params']['email'],
                )
                print("Modifications add for user: " + format(x['login']))
            if x['params']['state'] == "absent":
                client.user_mod(
                    username=x['login'],
                    disabled=True
                )
                print("User: " + format(x['login'] + " disable"))
        except:
            None


# --Add users in groups and remove users from groups


def add_user_in_group(users, list_ldap):
    list_ldap_users = []
    list_users = []
    for i in list(list_ldap):
        i['login'] = i.pop('uid')
        i['groups'] = i.pop('memberof_group')
        for z in i['login']:
            i['login'] = z
            list_ldap_users.append(i)
    for i in users:
        del i['first_name']
        del i['last_name']
        del i['params']
        list_users.append(i)
    for i in list_ldap_users:
        for x in list_users:
            if i['login'] == x['login']:
                list_groups = list(set(x['groups']) - set(i['groups']))
                list_ldap_groups = list(set(i['groups']) - set(x['groups']))
                if list_groups:  # add users in group
                    for z in list_groups:
                        client.group_add_member(
                            users=i['login'],
                            group=z
                        )
                        print("User " + format(i['login'] + " was added to " + format(z)))
                if list_ldap_groups:  # Remove users from groups
                    for z in list_ldap_groups:
                        client.group_remove_member(
                            users=x['login'],
                            group=z
                        )
                        print("User " + format(i['login'] + " was removed from " + format(z)))


# Run
users = parser_yml()
ldap_users = list_ldap_users()
list_ldap = list_ldap()
create_users(users, ldap_users)
user_mod(users)
add_user_in_group(users, list_ldap)