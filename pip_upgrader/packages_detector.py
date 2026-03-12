try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib


class PackagesDetector(object):
    """Takes list of requirements files and returns the list of packages from all of them"""

    packages = []

    def __init__(self, requirements_files):
        self.packages = []
        self.detect_packages(requirements_files)

    def get_packages(self):
        return self.packages

    def detect_packages(self, requirements_files):
        for filename in requirements_files:
            if filename.endswith('pyproject.toml'):
                self._detect_pyproject_packages(filename)
            else:
                self._detect_requirements_packages(filename)

    def _detect_requirements_packages(self, filename):
        with open(filename) as fh:
            for line in fh:
                self._process_req_line(line)

    def _detect_pyproject_packages(self, filename):
        with open(filename, 'rb') as f:
            data = tomllib.load(f)

        project = data.get('project', {})

        for dep in project.get('dependencies', []):
            self._process_pyproject_dep(dep)

        for group_deps in project.get('optional-dependencies', {}).values():
            for dep in group_deps:
                self._process_pyproject_dep(dep)

    def _process_pyproject_dep(self, dep):
        dep = dep.strip()
        if not dep or dep.startswith('#'):
            return
        # Strip environment markers (e.g. '; python_version < "3.11"')
        if ';' in dep:
            dep = dep.split(';')[0].strip()
        # Only include pinned dependencies (== or >=)
        if '==' in dep or '>=' in dep:
            self.packages.append(dep)

    def _process_req_line(self, line):

        if not line or not line.strip():
            return
        line = line.strip()

        if line.startswith('#'):
            return

        if (
            line.startswith('-f')
            or line.startswith('--find-links')
            or line.startswith('-i')
            or line.startswith('--index-url')
            or line.startswith('--extra-index-url')
            or line.startswith('--no-index')
            or line.startswith('-r')
            or line.startswith('-Z')
            or line.startswith('--always-unzip')
        ):
            # private repositories
            return

        if '#' in line:  # inline comment in file
            line = line.split('#')[0].strip()

        self.packages.append(line)
