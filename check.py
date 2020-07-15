from ruamel.yaml import YAML
from ruamel.yaml import YAMLError
import argparse
import glob
from marshmallow import Schema, fields, exceptions
import sys
import os
from python_freeipa import ClientMeta
from python_freeipa import exceptions as FreeipaExceptions
import urllib3
import logging
import re

class Args:

    def __init__(self):
        arg = argparse.ArgumentParser(description='yaml configuration validation')
        arg.add_argument('-d', required=True, help='users configuration directory path')
        arg.add_argument('--domain', required=True, type=str, help='FreeIPA FQDN')
        arg.add_argument('-u', required=True, type=str, help='FreeIPA login')
        arg.add_argument('-p', required=True, type=str, help='FreeIPA password')
        self.arguments = vars(arg.parse_args())


class Logger:

    def __init__(self):
        self.log = logging.getLogger()
        self.log.setLevel(logging.INFO)
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
        stream_handler.setFormatter(formatter)
        self.log.addHandler(stream_handler)


class Files:

    def __init__(self, dir):
        self.files = []
        self.dir = dir
        self.find_files_with_invalid_extension()
        self.extensions = ['yaml']
        for extension in self.extensions:
            self.find_files_by_extension(extension)
        if len(self.files) == 0:
            raise ValueError('Нет файлов с валидным расширением yaml в директории')

    def find_files_with_invalid_extension(self):
        files = glob.glob(self.dir + '/*')
        for file in files:
            name, ext = os.path.splitext(file)
            if ext in [".yaml", ".md"]:
                continue
            else:
                raise ValueError("Невалидное расширение файла {}".format(file))

    def find_files_by_extension(self, extension):
        files = glob.glob(self.dir + '/*.' + extension)
        for file in files:
            self.files.append(file)


class Yml:

    def __init__(self, yml_file):
        try:
            self.yml = YAML(typ='safe')
            self.content = self.yml.load(open(yml_file))
        except YAMLError as e:
            print(e)
            sys.exit(1)


class Ipa:

    def __init__(self, logger, domain, login, password):
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        self.logger = logger
        try:
            self.client = ClientMeta(domain, verify_ssl=False)
            self.client.login(login, password)
        except FreeipaExceptions.FreeIPAError as e:
            self.logger.log.exception(e)

    def check_group_exist(self, group):
        result = False
        group = self.client.group_find(o_cn=group)
        if group['count'] > 0:
            result = True
        return result


class Params(Schema):
    state = fields.Str()
    email = fields.Email()
    discord_id = fields.Int()


class User(Schema):
    login = fields.Str()
    first_name = fields.Str()
    last_name = fields.Str()
    params = fields.Nested(Params())
    groups = fields.List(fields.Str(), many=True, required=True)


if __name__ == '__main__':
    logger = Logger()
    args = Args()
    logger.log.info("Подключение к LDAP серверу")
    ipa = Ipa(logger, args.arguments['domain'], args.arguments['u'], args.arguments['p'])
    try:
        logger.log.info("Проверка файла на валидность")
        files = Files(args.arguments['d'])
    except ValueError as e:
        logger.log.exception(e)
        sys.exit(1)
    schema = User()
    for file in files.files:
        yaml = Yml(file)
        try:
            result = schema.load(yaml.content)
        except exceptions.ValidationError as e:
            logger.log.exception(e)
            sys.exit(1)
        fileName = os.path.basename(file).split('.yaml')[0]
        if fileName != result['login']:
            logger.log.error("Имя файла {0} и логин {1} не соответвуют друг другу".format(fileName, result['login']))
            exit(1)
        for group in result['groups']:
            if not ipa.check_group_exist(group):
                logger.log.error("Группа {0} не найдена".format(group))
                exit(1)
        if re.search('[a-zA-Z]',result['first_name']) is not None:
            logger.log.info("Поле first_name пользователя {} содержит не кириллические символы".format(result['login']))
            exit(1)
        if re.search('[a-zA-Z]',result['first_name']) is not None:
            logger.log.info("Поле last_name пользователя {} содержит не кириллические символы".format(result['login']))
            exit(1)

    logger.log.info("Проверка файла завершилась успешно")
    sys.exit(0)
