from ruamel.yaml import YAML
from ruamel.yaml import YAMLError
import glob
import argparse
import sys


class Files:

    def __init__(self, dir):
        self.files = []
        self.dir = dir
        self.extensions = ['yaml']
        for extension in self.extensions:
            self.find_files_by_extension(extension)

    def find_files_by_extension(self, extension):
        files = glob.glob(self.dir + '/*.' + extension)
        for file in files:
            self.files.append(file)


class Args:

    def __init__(self):
        arg = argparse.ArgumentParser(description='script checks users in yml for ldap entry')
        arg.add_argument('-d', required=True, help='user configuration directory path')
        arg.add_argument('-o', required=True, help='output directory')
        self.arguments = vars(arg.parse_args())


class Yaml:

    def __init__(self, files, output):
        all_users_list = {'user': []}
        self.yml = YAML(typ='safe')
        for file in files:
            content = self.load_content(file)
            all_users_list['user'].append(content)
        self.write_to_file(all_users_list, output)

    def load_content(self, file):
        try:
            content = self.yml.load(open(file))
            return content
        except YAMLError as e:
            print(e)
            sys.exit(1)

    def write_to_file(self, data, output):
        with open('{}/users_list.yml'.format(output), 'w') as fd:
            self.yml.dump(data, fd)


if __name__ == '__main__':
    args = Args()
    files = Files(args.arguments['d'])
    yaml = Yaml(files.files, args.arguments['o'])
