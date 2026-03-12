import re


class PackagesUpgrader(object):
    selected_packages = None
    requirements_files = None
    upgraded_packages = None
    dry_run = False
    skip_gte = False

    def __init__(self, selected_packages, requirements_files, options):
        self.selected_packages = selected_packages
        self.requirements_files = requirements_files
        self.upgraded_packages = []
        self._upgraded_package_names = set()
        self.dry_run = options.get('--dry-run', False)
        self.skip_gte = options.get('--skip-greater-equal', False)

    def do_upgrade(self):
        for package in self.selected_packages:
            self._update_requirements_package(package)

        return self.upgraded_packages

    def _update_requirements_package(self, package):
        for filename in set(self.requirements_files):
            with open(filename, 'r') as frh:
                lines = frh.readlines()

            try:
                with open(filename, 'w') as fwh:
                    for line in lines:
                        line = self._maybe_update_line_package(line, package)
                        fwh.write(line)
            except Exception as e:  # pragma: nocover
                with open(filename, 'w') as fwh:
                    for line in lines:
                        fwh.write(line)
                raise e

    def _maybe_update_line_package(self, line, package):
        original_line = line
        pin_type = '==' if self.skip_gte else r'[>=]='

        pattern = r'\b({package}(?:\[\w*\])?{pin_type})[a-zA-Z0-9\.]+\b'.format(
            package=re.escape(package['name']), pin_type=pin_type
        )

        repl = r'\g<1>{}'.format(package['latest_version'])
        line = re.sub(pattern, repl, line)

        if line != original_line:
            if package['name'] not in self._upgraded_package_names:
                self._upgraded_package_names.add(package['name'])
                self.upgraded_packages.append(package)

            if self.dry_run:  # pragma: nocover
                print(
                    '[Dry Run]: skipping requirements replacement:',
                    original_line.replace('\n', ''),
                    ' / ',
                    line.replace('\n', ''),
                )
                return original_line
        return line
