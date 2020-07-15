import argparse
from python_freeipa import ClientMeta
import urllib3
import ruamel.yaml


def args():
    arg = argparse.ArgumentParser(description='ldap management')
    arg.add_argument('--domain', required=True, type=str, help='FreeIPA FQDN')
    arg.add_argument('-u', required=True, type=str, help='FreeIPA login')
    arg.add_argument('-p', required=True, type=str, help='FreeIPA password')
    arg.add_argument('-o', required=True, type=str, help='Output files to dir')
    return vars(arg.parse_args())


def client(domain, login, password):
    client = ClientMeta(domain, verify_ssl=False)
    client.login(login, password)
    return client


def getLdapUsers(client, output):
    users = client.user_find(o_sizelimit=2147483647)
    for i in users['result']:
        if i['uid'][0] == 'admin':
            continue
        template = {
            'login': i['uid'][0],
            'first_name': i['givenname'][0],
            'last_name': i['sn'][0],
            'params': {
                'state': "present",
                'email': i['mail'][0],
            },
            'groups': i['memberof_group']
        }
        try:
            discord_id = int(i['telephonenumber'][0])
        except KeyError:
            discord_id=0
        template['params']['discord_id']=discord_id
        f = open(output + i['uid'][0] + '.yaml', 'w')
        f.write(ruamel.yaml.dump(template, allow_unicode=True, Dumper=ruamel.yaml.RoundTripDumper))
        f.close()


if __name__ == "__main__":
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    args = args()
    output = args['o']
    client = client(args['domain'], args['u'], args['p'])
    getLdapUsers(client, output)
