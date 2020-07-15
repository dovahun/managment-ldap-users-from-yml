import argparse
from ruamel.yaml import YAML
from ruamel.yaml import YAMLError
from python_freeipa import ClientMeta
from python_freeipa import exceptions as FreeipaExceptions
import logging
import sys
import urllib3


# get cmd arguments
def args():
    arg = argparse.ArgumentParser(description='ldap management')
    arg.add_argument('--domain', required=True, type=str, help='FreeIPA FQDN')
    arg.add_argument('-u', required=True, type=str, help='FreeIPA login')
    arg.add_argument('-p', required=True, type=str, help='FreeIPA password')
    arg.add_argument('-i', required=True, type=str, help='Input file')
    return vars(arg.parse_args())


def logger():
    log = logging.getLogger()
    log.setLevel(logging.INFO)
    stream_handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    stream_handler.setFormatter(formatter)
    log.addHandler(stream_handler)
    return log


# make ipa client
def client(domain, login, password):
    try:
        Log.info("Подключение к ldap")
        client = ClientMeta(domain, verify_ssl=False)
        client.login(login, password)
        return client
    except FreeipaExceptions.FreeIPAError as e:
        Log.exception(e)
        sys.exit(1)


# read input yml file
def readInput(path):
    gitUsers = {}
    yml = YAML(typ='safe')
    try:
        Log.info("Парсинг yaml файлов")
        content = yml.load(open(path))
        # create map login: attributes
        for entry in content['user']:
            gitUsers[entry['login']] = entry
        return gitUsers
    except YAMLError as e:
        Log.exception(e)
        sys.exit(1)


# get users with attributes from ldap server
def getLdapUsers(client):
    ldapUsers = {}
    try:
        users_active = client.user_find(o_nsaccountlock=False, o_sizelimit=0)
        users_disabled = client.user_find(o_nsaccountlock=True, o_sizelimit=0)
        for user in users_active['result']:
            ldapUsers[user['uid'][0]] = user
        for user in users_disabled['result']:
            ldapUsers[user['uid'][0]] = user
        return ldapUsers
    except FreeipaExceptions.FreeIPAError as e:
        Log.exception(e)
        sys.exit(1)


# create users, that don't exists
def createUsers(gitUsers, ldapUsers, client):
    for gitUser in gitUsers:
        if gitUser not in ldapUsers and gitUsers[gitUser]['params']['state'] == 'present':
            Log.info("Создание пользователя {}".format(gitUser))
            try:
                client.user_add(
                    a_uid=gitUsers[gitUser]['login'],
                    o_sn=gitUsers[gitUser]['last_name'],
                    o_givenname=gitUsers[gitUser]['first_name'],
                    o_mail=gitUsers[gitUser]['params']['email'],
                    o_cn="{0} {1}".format(gitUsers[gitUser]['first_name'], gitUsers[gitUser]['last_name']),
                    o_telephonenumber=gitUsers[gitUser]['params']['discord_id']
                )
                Log.info("Процесс добвления пользователя в группы {} groups".format(gitUser))
                for group in gitUsers[gitUser]['groups']:
                    Log.info("Добавление пользователя {0} в группу {1}".format(gitUsers[gitUser]['login'], group))
                    client.group_add_member(a_cn=group, o_user=gitUsers[gitUser]['login'])
            except FreeipaExceptions.FreeIPAError as e:
                Log.exception(e)
                sys.exit(1)


# switch users on/off
def enableOrDisableUsers(gitUsers, ldapUsers, client):
    for gitUser in gitUsers:
        if gitUser in ldapUsers and gitUsers[gitUser]['params']['state'] == 'absent' and \
                ldapUsers[gitUser]['nsaccountlock'] == False:
            try:
                client.user_disable(a_uid=gitUsers[gitUser]['login'])
                Log.info("Пользователь {} был выключен".format(gitUsers[gitUser]['login']))
            except FreeipaExceptions.FreeIPAError as e:
                Log.exception(e)
        elif gitUser in ldapUsers and gitUsers[gitUser]['params']['state'] == 'present' and \
                ldapUsers[gitUser]['nsaccountlock'] == True:
            try:
                client.user_enable(a_uid=gitUsers[gitUser]['login'])
                Log.info("Пользователь {} был включен".format(gitUsers[gitUser]['login']))
            except FreeipaExceptions.FreeIPAError as e:
                Log.exception(e)


# add or remove user from group
def managementUserGroups(gitUsers, ldapUsers, client):
    for gitUser in gitUsers:
        if gitUser in ldapUsers:
            for gitGroup in gitUsers[gitUser]['groups']:
                if gitGroup not in ldapUsers[gitUser]['memberof_group']:
                    try:
                        client.group_add_member(
                            a_cn=gitGroup,
                            o_user=gitUser
                        )
                        Log.info(
                            "Добавление пользователя {0} в группу {1}".format(gitUsers[gitUser]['login'], gitGroup))
                    except FreeipaExceptions.FreeIPAError as e:
                        Log.exception(e)
                        sys.exit(1)
            for ldapGroup in ldapUsers[gitUser]['memberof_group']:
                if ldapGroup not in gitUsers[gitUser]['groups']:
                    try:
                        client.group_remove_member(
                            a_cn=ldapGroup,
                            o_user=gitUser
                        )
                        Log.info(
                            "Удаление пользователя {0} из группы {1}".format(gitUsers[gitUser]['login'], ldapGroup))
                    except FreeipaExceptions.FreeIPAError as e:
                        Log.exception(e)
                        sys.exit(1)


# Management email address, discord id and last or first names of users
def managementUserModifications(gitUsers, ldapUsers, client):
    for gitUser in gitUsers:
        if gitUser in ldapUsers:
            if gitUsers[gitUser]['params']['email'] != str(ldapUsers[gitUser]['mail'][0]):
                try:
                    client.user_mod(
                        a_uid=gitUser,
                        o_mail=gitUsers[gitUser]['params']['email']
                    )
                    Log.info("Email был изменен для {0}".format(gitUsers[gitUser]['login']))
                except FreeipaExceptions.FreeIPAError as e:
                    Log.exception(e)
                    sys.exit(1)
            try:
                ldapDiscordId = int(ldapUsers[gitUser]['telephonenumber'][0])
            except KeyError:
                ldapDiscordId = None
            if gitUsers[gitUser]['params']['discord_id'] != ldapDiscordId or ldapDiscordId is None:
                try:
                    client.user_mod(
                        a_uid=gitUser,
                        o_telephonenumber=gitUsers[gitUser]['params']['discord_id']
                    )
                    Log.info("Discord id был изменен для {0}".format(gitUsers[gitUser]['login']))
                except FreeipaExceptions.FreeIPAError as e:
                    Log.exception(e)
                    sys.exit(1)
            if gitUsers[gitUser]['first_name'] != str(ldapUsers[gitUser]['givenname'][0]) or \
                    gitUsers[gitUser]['last_name'] != str(ldapUsers[gitUser]['sn'][0]):
                try:
                    fullName = "{0} {1}".format(gitUsers[gitUser]['first_name'], gitUsers[gitUser]['last_name'])
                    client.user_mod(
                        a_uid=gitUser,
                        o_givenname=gitUsers[gitUser]['first_name'],
                        o_sn=gitUsers[gitUser]['last_name'],
                        o_cn=fullName,
                        o_displayname=fullName,
                        o_gecos=fullName
                    )
                    Log.info("Имя и фамилия пользователя {0} были изменены".format(gitUsers[gitUser]['login']))
                except FreeipaExceptions.FreeIPAError as e:
                    Log.exception(e)
                    sys.exit(1)


# disable ldap users if they are not found in Git
def checkGitUser(gitUsers, ldapUsers, client):
    for ldapUser in ldapUsers:
        if ldapUser not in gitUsers and not ldapUsers[ldapUser]['nsaccountlock']:
            if ldapUser == 'admin':
                continue
            try:
                client.user_disable(
                    a_uid=ldapUser
                )
                Log.info("Учетная запись {0} не была найдена в bitbucket и была отключена".format(ldapUser))
            except FreeipaExceptions.FreeIPAError as e:
                Log.exception(e)
                sys.exit(1)


if __name__ == "__main__":
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    Log = logger()
    args = args()
    client = client(args['domain'], args['u'], args['p'])
    gitUsers = readInput(args['i'])
    ldapUsers = getLdapUsers(client)
    createUsers(gitUsers, ldapUsers, client)
    enableOrDisableUsers(gitUsers, ldapUsers, client)
    managementUserModifications(gitUsers, ldapUsers, client)
    managementUserGroups(gitUsers, ldapUsers, client)
    checkGitUser(gitUsers, ldapUsers, client)
