import shutil
import tempfile
from io import StringIO
from subprocess import PIPE
from subprocess import Popen as popen
from unittest import TestCase
from unittest.mock import patch

import responses
from packaging.utils import canonicalize_name

from pip_upgrader import __version__ as VERSION
from pip_upgrader import cli
from pip_upgrader.packages_detector import PackagesDetector
from pip_upgrader.requirements_detector import RequirementsDetector

DEFAULT_OPTIONS = {
    '--dry-run': False,
    '--prerelease': False,
    '--check-greater-equal': False,
    '--skip-virtualenv-check': False,
    '--skip-package-installation': False,
    '--use-default-index': False,
    '--timeout': None,
    '-p': [],
    '<requirements_file>': [],
}


def make_options(**overrides):
    opts = DEFAULT_OPTIONS.copy()
    opts.update(overrides)
    return opts


class TestHelp(TestCase):
    def test_returns_usage_information(self):
        output = popen(['pip-upgrade', '-h'], stdout=PIPE).communicate()[0]
        self.assertTrue('Usage:' in output.decode('utf-8'))

        output = popen(['pip-upgrade', '--help'], stdout=PIPE).communicate()[0]
        self.assertTrue('Usage:' in output.decode('utf-8'))


class TestVersion(TestCase):
    def test_returns_version_information(self):
        output = popen(['pip-upgrade', '--version'], stdout=PIPE).communicate()[0]
        self.assertEqual(output.strip().decode('utf-8'), VERSION)


@patch('pip_upgrader.packages_interactive_selector.user_input', return_value='all')
@patch('pip_upgrader.virtualenv_checker.is_virtualenv', return_value=True)
class TestCommand(TestCase):
    PACKAGE_NAMES = ['Django', 'celery', 'django-rest-auth', 'ipython']

    def _add_responses_mocks(self):
        for package in self.PACKAGE_NAMES:
            canonical = canonicalize_name(package)
            with open('tests/fixtures/{}.json'.format(package)) as fh:
                body = fh.read()

            responses.add(
                responses.GET,
                "https://pypi.python.org/pypi/{}/json".format(canonical),
                body=body,
                content_type="application/json",
            )

            with open('tests/fixtures/{}.html'.format(canonical)) as fh:
                body_html = fh.read()
            responses.add(responses.GET, "https://pypi.python.org/simple/{}/".format(canonical), body=body_html)

    def setUp(self):
        self._add_responses_mocks()

    @responses.activate
    @patch(
        'pip_upgrader.cli.get_options',
        return_value=make_options(**{'--dry-run': True, '<requirements_file>': ['requirements.txt']}),
    )
    @patch.dict('os.environ', {}, clear=False)
    @patch('pip_upgrader.packages_status_detector.PackagesStatusDetector.pip_config_locations', new=[])
    def test_command_basic_usage(self, options_mock, is_virtualenv_mock, user_input_mock):

        with patch('sys.stdout', new_callable=StringIO) as stdout_mock:
            cli.main()
            output = stdout_mock.getvalue()

        self.assertTrue(user_input_mock.called)

        self.assertIn('Available upgrades', output)
        self.assertIn('django-rest-auth ... upgrade available: 0.9.0 ==>', output)
        self.assertNotIn('ipdb', output)
        self.assertIn('Successfully upgraded', output)
        self.assertIn('this was a simulation using --dry-run', output)

    @responses.activate
    @patch(
        'pip_upgrader.cli.get_options',
        return_value=make_options(**{'--dry-run': True, '<requirements_file>': ['requirements.txt']}),
    )
    @patch.dict('os.environ', {}, clear=False)
    def test_command_simple_html_index_url(self, options_mock, is_virtualenv_mock, user_input_mock):

        with (
            patch('sys.stdout', new_callable=StringIO) as stdout_mock,
            patch(
                'pip_upgrader.packages_status_detector.PackagesStatusDetector.pip_config_locations',
                new=['pip.test.conf'],
            ),
        ):
            cli.main()
            output = stdout_mock.getvalue()

        self.assertTrue(user_input_mock.called)
        # checks if new index-url was discovered from config file
        self.assertIn('Setting API url', output)
        self.assertIn('https://pypi.python.org/simple/{package}', output)

        self.assertIn('Available upgrades', output)
        self.assertIn('django-rest-auth ... upgrade available: 0.9.0 ==>', output)
        self.assertNotIn('ipdb', output)
        self.assertIn('Successfully upgraded', output)
        self.assertIn('this was a simulation using --dry-run', output)

    @responses.activate
    @patch(
        'pip_upgrader.cli.get_options',
        return_value=make_options(**{'--dry-run': True, '<requirements_file>': ['requirements.txt']}),
    )
    @patch.dict('os.environ', {'PIP_INDEX_URL': 'https://pypi.python.org/simple/'})
    @patch('pip_upgrader.packages_status_detector.PackagesStatusDetector.pip_config_locations', new=[])
    def test_command_pip_index_url_environ(self, options_mock, is_virtualenv_mock, user_input_mock):

        with patch('sys.stdout', new_callable=StringIO) as stdout_mock:
            cli.main()
            output = stdout_mock.getvalue()

        self.assertTrue(user_input_mock.called)
        # checks if new index-url was discovered from config file
        self.assertIn('Setting API url', output)
        self.assertIn('https://pypi.python.org/simple/{package}', output)

        self.assertIn('Available upgrades', output)
        self.assertIn('django-rest-auth ... upgrade available: 0.9.0 ==>', output)
        self.assertNotIn('ipdb', output)
        self.assertIn('Successfully upgraded', output)
        self.assertIn('this was a simulation using --dry-run', output)

    @responses.activate
    @patch(
        'pip_upgrader.cli.get_options',
        return_value=make_options(
            **{'--dry-run': True, '--use-default-index': True, '<requirements_file>': ['requirements.txt']}
        ),
    )
    def test_command__use_default_index(self, options_mock, is_virtualenv_mock, user_input_mock):

        with (
            patch('sys.stdout', new_callable=StringIO) as stdout_mock,
            patch(
                'pip_upgrader.packages_status_detector.PackagesStatusDetector.pip_config_locations',
                new=['pip.test.conf'],
            ),
        ):
            cli.main()
            output = stdout_mock.getvalue()

        # checks if new index-url was discovered from config file
        self.assertNotIn('Setting API url', output)
        self.assertIn('Successfully upgraded', output)

    @responses.activate
    @patch(
        'pip_upgrader.cli.get_options',
        return_value=make_options(**{'--dry-run': True, '<requirements_file>': ['requirements.txt']}),
    )
    @patch.dict('os.environ', {}, clear=False)
    @patch('pip_upgrader.packages_status_detector.PackagesStatusDetector.pip_config_locations', new=[])
    def test_command_interactive_bad_choices(self, options_mock, is_virtualenv_mock, user_input_mock):

        user_input_mock.return_value = ''
        with patch('sys.stdout', new_callable=StringIO) as stdout_mock:
            cli.main()
            output = stdout_mock.getvalue()

        self.assertTrue(user_input_mock.called)
        self.assertIn('No choice selected', output)
        self.assertNotIn('Setting API url', output)

        user_input_mock.return_value = '5 6 7'
        with patch('sys.stdout', new_callable=StringIO) as stdout_mock:
            cli.main()
            output = stdout_mock.getvalue()

        self.assertTrue(user_input_mock.called)
        self.assertIn('No valid choice selected.', output)

    @responses.activate
    @patch(
        'pip_upgrader.cli.get_options',
        return_value=make_options(**{'--dry-run': True, '-p': ['all'], '<requirements_file>': ['requirements.txt']}),
    )
    @patch.dict('os.environ', {}, clear=False)
    @patch('pip_upgrader.packages_status_detector.PackagesStatusDetector.pip_config_locations', new=[])
    def test_command_not_interactive_all_packages(self, options_mock, is_virtualenv_mock, user_input_mock):

        with patch('sys.stdout', new_callable=StringIO) as stdout_mock:
            cli.main()
            output = stdout_mock.getvalue()

        # no user_input should be called
        self.assertFalse(user_input_mock.called)

        self.assertNotIn('Setting API url', output)
        self.assertNotIn('Available upgrades', output)
        self.assertIn('Django ... upgrade available: 1.10 ==>', output)
        self.assertIn('django-rest-auth ... upgrade available: 0.9.0 ==>', output)
        self.assertNotIn('ipdb', output)

        self.assertIn('Successfully upgraded', output)
        self.assertIn('this was a simulation using --dry-run', output)

    @responses.activate
    @patch(
        'pip_upgrader.cli.get_options',
        return_value=make_options(
            **{'--dry-run': True, '-p': ['^django$'], '<requirements_file>': ['requirements.txt']}
        ),
    )
    @patch.dict('os.environ', {}, clear=False)
    @patch('pip_upgrader.packages_status_detector.PackagesStatusDetector.pip_config_locations', new=[])
    def test_command_not_interactive_specific_package(self, options_mock, is_virtualenv_mock, user_input_mock):

        with patch('sys.stdout', new_callable=StringIO) as stdout_mock:
            cli.main()
            output = stdout_mock.getvalue()

        # no user_input should be called
        self.assertFalse(user_input_mock.called)

        self.assertNotIn('Setting API url', output)
        self.assertIn('Django ... upgrade available: 1.10 ==>', output)
        self.assertNotIn('django-rest-auth', output)
        self.assertNotIn('ipdb', output)

        self.assertIn('Successfully upgraded', output)

    @responses.activate
    @patch(
        'pip_upgrader.cli.get_options',
        return_value=make_options(
            **{'--dry-run': True, '-p': ['ipython'], '<requirements_file>': ['requirements.txt']}
        ),
    )
    @patch.dict('os.environ', {}, clear=False)
    @patch('pip_upgrader.packages_status_detector.PackagesStatusDetector.pip_config_locations', new=[])
    def test_command_not_interactive_all_packages_up_to_date(self, options_mock, is_virtualenv_mock, user_input_mock):

        with patch('sys.stdout', new_callable=StringIO) as stdout_mock:
            cli.main()
            output = stdout_mock.getvalue()

        # no user_input should be called
        self.assertFalse(user_input_mock.called)
        self.assertNotIn('Setting API url', output)
        # ipython is not in requirements.txt, so no packages are found
        self.assertIn('All packages are up-to-date.', output)

    @responses.activate
    @patch(
        'pip_upgrader.cli.get_options',
        return_value=make_options(
            **{'--dry-run': True, '-p': ['all'], '<requirements_file>': ['requirements/production.txt']}
        ),
    )
    @patch.dict('os.environ', {}, clear=False)
    @patch('pip_upgrader.packages_status_detector.PackagesStatusDetector.pip_config_locations', new=[])
    def test_command_not_interactive_explicit_requirements(self, options_mock, is_virtualenv_mock, user_input_mock):

        with patch('sys.stdout', new_callable=StringIO) as stdout_mock:
            cli.main()
            output = stdout_mock.getvalue()

        # no user_input should be called
        self.assertFalse(user_input_mock.called)

        self.assertNotIn('Setting API url', output)
        self.assertNotIn('Django ... upgrade available: 1.10 ==>', output)
        self.assertNotIn('django-rest-auth', output)
        self.assertNotIn('ipdb', output)
        self.assertIn('celery ... upgrade available: 3.1.1 ==>', output)

        self.assertIn('Successfully upgraded', output)

    @responses.activate
    @patch(
        'pip_upgrader.cli.get_options',
        return_value=make_options(
            **{'--dry-run': True, '-p': ['all'], '<requirements_file>': ['requirements/local.txt']}
        ),
    )
    @patch.dict('os.environ', {}, clear=False)
    @patch('pip_upgrader.packages_status_detector.PackagesStatusDetector.pip_config_locations', new=[])
    def test_command_not_recursive_requirements_include(self, options_mock, is_virtualenv_mock, user_input_mock):

        with patch('sys.stdout', new_callable=StringIO) as stdout_mock:
            cli.main()
            output = stdout_mock.getvalue()

        # no user_input should be called
        self.assertFalse(user_input_mock.called)
        self.assertIn('celery ... upgrade available: 3.1.1 ==>', output)
        self.assertIn('requirements/local.txt', output)
        self.assertIn('requirements/production.txt', output)
        self.assertIn('requirements/extra/debug.txt', output)
        self.assertIn('requirements/extra/debug2.txt', output)
        self.assertNotIn('requirements/extra/bad_file.txt', output)

        self.assertIn('Successfully upgraded', output)

    @responses.activate
    @patch(
        'pip_upgrader.cli.get_options',
        return_value=make_options(
            **{'--dry-run': True, '-p': ['^django$'], '--prerelease': True, '<requirements_file>': ['requirements.txt']}
        ),
    )
    @patch.dict('os.environ', {}, clear=False)
    @patch('pip_upgrader.packages_status_detector.PackagesStatusDetector.pip_config_locations', new=[])
    def test_command_not_specific_package_prerelease(self, options_mock, is_virtualenv_mock, user_input_mock):

        with patch('sys.stdout', new_callable=StringIO) as stdout_mock:
            cli.main()
            output = stdout_mock.getvalue()

        # no user_input should be called
        self.assertFalse(user_input_mock.called)

        self.assertNotIn('Setting API url', output)
        # With prerelease enabled, stable 1.11 > prerelease 1.11rc1, so stable wins
        self.assertIn('Django ... upgrade available: 1.10 ==> 1.11', output)
        self.assertNotIn('django-rest-auth', output)
        self.assertNotIn('ipdb', output)

        self.assertIn('Successfully upgraded', output)

    @responses.activate
    @patch(
        'pip_upgrader.cli.get_options',
        return_value=make_options(
            **{'--dry-run': True, '-p': ['^django$'], '--prerelease': True, '<requirements_file>': ['requirements.txt']}
        ),
    )
    @patch.dict('os.environ', {}, clear=False)
    def test_command_not_specific_package_prerelease_html_api(self, options_mock, is_virtualenv_mock, user_input_mock):

        with (
            patch('sys.stdout', new_callable=StringIO) as stdout_mock,
            patch(
                'pip_upgrader.packages_status_detector.PackagesStatusDetector.pip_config_locations',
                new=['pip.test.conf'],
            ),
        ):
            cli.main()
            output = stdout_mock.getvalue()

        # no user_input should be called
        self.assertFalse(user_input_mock.called)

        self.assertIn('Setting API url', output)
        self.assertIn('Django ... upgrade available: 1.10 ==> 1.11', output)
        self.assertNotIn('django-rest-auth', output)
        self.assertNotIn('ipdb', output)

        self.assertIn('Successfully upgraded', output)

    @responses.activate
    @patch(
        'pip_upgrader.cli.get_options',
        return_value=make_options(
            **{
                '--dry-run': True,
                '--skip-virtualenv-check': False,
                '-p': ['^django$'],
                '<requirements_file>': ['requirements.txt'],
            }
        ),
    )
    @patch.dict('os.environ', {}, clear=False)
    @patch('pip_upgrader.packages_status_detector.PackagesStatusDetector.pip_config_locations', new=[])
    def test_command_not_interactive_not_virtualenv(self, options_mock, is_virtualenv_mock, user_input_mock):
        is_virtualenv_mock.return_value = False

        with patch('sys.stdout', new_callable=StringIO) as stdout_mock:
            cli.main()
            output = stdout_mock.getvalue()

        self.assertNotIn('Setting API url', output)
        self.assertIn("It seems you haven't activated a virtualenv", output)
        self.assertNotIn('Successfully upgraded', output)

    @responses.activate
    @patch(
        'pip_upgrader.cli.get_options',
        return_value=make_options(
            **{
                '--dry-run': True,
                '--skip-virtualenv-check': True,
                '-p': ['^django$'],
                '<requirements_file>': ['requirements.txt'],
            }
        ),
    )
    @patch.dict('os.environ', {}, clear=False)
    @patch('pip_upgrader.packages_status_detector.PackagesStatusDetector.pip_config_locations', new=[])
    def test_command_not_interactive_not_virtualenv_skip(self, options_mock, is_virtualenv_mock, user_input_mock):
        is_virtualenv_mock.return_value = False

        with patch('sys.stdout', new_callable=StringIO) as stdout_mock:
            cli.main()
            output = stdout_mock.getvalue()

        self.assertFalse(user_input_mock.called)
        self.assertNotIn('Setting API url', output)
        self.assertIn('Django ... upgrade available: 1.10 ==>', output)
        self.assertNotIn('django-rest-auth', output)
        self.assertNotIn('ipdb', output)
        self.assertIn('Successfully upgraded', output)

    @responses.activate
    @patch(
        'pip_upgrader.cli.get_options',
        return_value=make_options(
            **{'--dry-run': True, '--timeout': '30', '<requirements_file>': ['requirements.txt']}
        ),
    )
    @patch.dict('os.environ', {}, clear=False)
    @patch('pip_upgrader.packages_status_detector.PackagesStatusDetector.pip_config_locations', new=[])
    def test_command_with_custom_timeout(self, options_mock, is_virtualenv_mock, user_input_mock):

        with patch('sys.stdout', new_callable=StringIO) as stdout_mock:
            cli.main()
            output = stdout_mock.getvalue()

        self.assertTrue(user_input_mock.called)
        self.assertIn('Successfully upgraded', output)

    @responses.activate
    @patch(
        'pip_upgrader.cli.get_options',
        return_value=make_options(
            **{
                '--dry-run': True,
                '-p': ['all'],
                '<requirements_file>': ['requirements/production.txt', 'requirements/extra/debug.txt'],
            }
        ),
    )
    @patch.dict('os.environ', {}, clear=False)
    @patch('pip_upgrader.packages_status_detector.PackagesStatusDetector.pip_config_locations', new=[])
    def test_command_multiple_files_same_package(self, options_mock, is_virtualenv_mock, user_input_mock):
        """Test that the same package across multiple files doesn't cause duplicate upgrades."""
        with patch('sys.stdout', new_callable=StringIO) as stdout_mock:
            cli.main()
            output = stdout_mock.getvalue()

        self.assertFalse(user_input_mock.called)
        self.assertIn('celery ... upgrade available: 3.1.1 ==>', output)
        self.assertIn('Successfully upgraded', output)
        # celery should only appear once in the success message
        success_line = [line for line in output.split('\n') if 'Successfully upgraded' in line][0]
        self.assertEqual(success_line.count('celery'), 1)

    @responses.activate
    @patch(
        'pip_upgrader.cli.get_options',
        return_value=make_options(**{'--dry-run': True, '-p': ['all'], '<requirements_file>': ['requirements.txt']}),
    )
    @patch.dict('os.environ', {}, clear=False)
    @patch('pip_upgrader.packages_status_detector.PackagesStatusDetector.pip_config_locations', new=[])
    def test_command_dash_package_names(self, options_mock, is_virtualenv_mock, user_input_mock):
        """Test that packages with dashes in their names are resolved correctly."""
        with patch('sys.stdout', new_callable=StringIO) as stdout_mock:
            cli.main()
            output = stdout_mock.getvalue()

        self.assertFalse(user_input_mock.called)
        self.assertIn('django-rest-auth ... upgrade available: 0.9.0 ==>', output)
        self.assertIn('Successfully upgraded', output)

    @responses.activate
    @patch(
        'pip_upgrader.cli.get_options',
        return_value=make_options(
            **{
                '--dry-run': True,
                '-p': ['all'],
                '<requirements_file>': ['requirements.txt'],
                '--check-greater-equal': True,
            }
        ),
    )
    @patch.dict('os.environ', {}, clear=False)
    @patch('pip_upgrader.packages_status_detector.PackagesStatusDetector.pip_config_locations', new=[])
    def test_command_check_greater_equal(self, options_mock, is_virtualenv_mock, user_input_mock):
        """Test that --check-greater-equal flag works correctly."""
        with patch('sys.stdout', new_callable=StringIO) as stdout_mock:
            cli.main()
            output = stdout_mock.getvalue()

        self.assertFalse(user_input_mock.called)
        self.assertIn('Django ... upgrade available: 1.10 ==>', output)
        self.assertIn('Successfully upgraded', output)

    @responses.activate
    @patch('pip_upgrader.cli.get_options', return_value=make_options(**{'--dry-run': True}))
    @patch.dict('os.environ', {}, clear=False)
    @patch('pip_upgrader.packages_status_detector.PackagesStatusDetector.pip_config_locations', new=[])
    def test_command_autodetect_requirements(self, options_mock, is_virtualenv_mock, user_input_mock):
        """Test that requirements files are auto-detected when none specified."""
        with patch('sys.stdout', new_callable=StringIO) as stdout_mock:
            cli.main()
            output = stdout_mock.getvalue()

        self.assertIn('Found valid requirements file(s)', output)
        self.assertIn('requirements.txt', output)
        self.assertIn('Successfully upgraded', output)

    @responses.activate
    @patch(
        'pip_upgrader.cli.get_options',
        return_value=make_options(
            **{'--dry-run': True, '-p': ['all'], '<requirements_file>': ['tests/fixtures/sample_pyproject.toml']}
        ),
    )
    @patch.dict('os.environ', {}, clear=False)
    @patch('pip_upgrader.packages_status_detector.PackagesStatusDetector.pip_config_locations', new=[])
    def test_command_pyproject_toml(self, options_mock, is_virtualenv_mock, user_input_mock):
        """Test upgrading packages from pyproject.toml."""
        with patch('sys.stdout', new_callable=StringIO) as stdout_mock:
            cli.main()
            output = stdout_mock.getvalue()

        self.assertFalse(user_input_mock.called)
        self.assertIn('Django ... upgrade available: 1.10 ==>', output)
        self.assertIn('django-rest-auth ... upgrade available: 0.9.0 ==>', output)
        self.assertIn('celery ... upgrade available: 3.1.1 ==>', output)
        self.assertIn('Successfully upgraded', output)

    @responses.activate
    @patch(
        'pip_upgrader.cli.get_options',
        return_value=make_options(
            **{'--dry-run': True, '-p': ['all'], '<requirements_file>': ['tests/fixtures/sample_pyproject.toml']}
        ),
    )
    @patch.dict('os.environ', {}, clear=False)
    @patch('pip_upgrader.packages_status_detector.PackagesStatusDetector.pip_config_locations', new=[])
    def test_command_pyproject_toml_version_replacement(self, options_mock, is_virtualenv_mock, user_input_mock):
        """Test that pyproject.toml versions are actually updated in the file."""
        # Work on a copy to avoid modifying the fixture
        tmpdir = tempfile.mkdtemp()
        tmp_pyproject = tmpdir + '/pyproject.toml'
        shutil.copy('tests/fixtures/sample_pyproject.toml', tmp_pyproject)

        options_mock.return_value = make_options(
            **{
                '--dry-run': False,
                '--skip-package-installation': True,
                '-p': ['all'],
                '<requirements_file>': [tmp_pyproject],
            }
        )

        with patch('sys.stdout', new_callable=StringIO):
            cli.main()

        with open(tmp_pyproject) as f:
            content = f.read()

        # Versions should be updated
        self.assertNotIn('Django==1.10', content)
        self.assertNotIn('django-rest-auth[with_social]==0.9.0', content)
        self.assertNotIn('celery==3.1.1', content)
        # New versions should be present
        self.assertIn('Django==', content)
        self.assertIn('celery==', content)

        shutil.rmtree(tmpdir)


class TestPyprojectDetection(TestCase):
    """Tests for pyproject.toml detection and parsing."""

    def test_requirements_detector_accepts_pyproject(self):
        """RequirementsDetector should accept a valid pyproject.toml."""
        detector = RequirementsDetector(['tests/fixtures/sample_pyproject.toml'])
        self.assertIn('tests/fixtures/sample_pyproject.toml', detector.get_filenames())

    def test_requirements_detector_rejects_pyproject_without_deps(self):
        """RequirementsDetector should reject pyproject.toml without [project.dependencies]."""
        detector = RequirementsDetector(['tests/fixtures/no_deps_pyproject.toml'])
        self.assertEqual(detector.get_filenames(), [])

    def test_packages_detector_parses_pyproject_dependencies(self):
        """PackagesDetector should extract pinned deps from pyproject.toml."""
        detector = PackagesDetector(['tests/fixtures/sample_pyproject.toml'])
        packages = detector.get_packages()
        self.assertIn('Django==1.10', packages)
        self.assertIn('django-rest-auth[with_social]==0.9.0', packages)
        self.assertIn('celery==3.1.1', packages)
        self.assertIn('ipython==6.0.0', packages)
        # pytest has no pin, should not be included
        self.assertNotIn('pytest', packages)

    def test_packages_detector_skips_env_markers(self):
        """PackagesDetector should strip environment markers from deps."""
        tmpdir = tempfile.mkdtemp()
        tmp_pyproject = tmpdir + '/pyproject.toml'
        with open(tmp_pyproject, 'w') as f:
            f.write('[project]\nname = "test"\ndependencies = [\n    "tomli>=1.0.0; python_version < \\"3.11\\"",\n]\n')
        detector = PackagesDetector([tmp_pyproject])
        packages = detector.get_packages()
        self.assertEqual(len(packages), 1)
        self.assertEqual(packages[0], 'tomli>=1.0.0')
        shutil.rmtree(tmpdir)

    def test_packages_detector_mixed_files(self):
        """PackagesDetector should handle a mix of requirements.txt and pyproject.toml."""
        detector = PackagesDetector(['requirements.txt', 'tests/fixtures/sample_pyproject.toml'])
        packages = detector.get_packages()
        # From requirements.txt
        self.assertIn('Django==1.10', packages)
        # From pyproject.toml optional-dependencies
        self.assertIn('celery==3.1.1', packages)
