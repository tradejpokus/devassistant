from flexmock import flexmock
import pytest

from devassistant.assistants import yaml_assistant
from devassistant.command_helpers import RPMHelper, YUMHelper

# hook app testing logging
from test.logger import TestLoggingHandler

class TestYamlAssistant(object):
    def setup_method(self, method):
        self.ya = yaml_assistant.YamlAssistant()
        self.ya._files = {'first': {'source': 'f/g'}, 'second': {'source': 's/t'}}
        self.tlh = TestLoggingHandler.create_fresh_handler()

    @pytest.mark.parametrize(('comm', 'arg_dict', 'result'), [
        ('ls -la', {}, 'ls -la'),
        ('touch $foo ${bar} $baz', {'foo': 'a', 'bar': 'b'}, 'touch a b $baz'),
        ('cp &first second', {}, 'cp f/g second'),
        ('cp &{first} &{nothing}', {}, 'cp f/g &{nothing}'),
        ('cp &{first} $foo', {'foo': 'a'}, 'cp f/g a'),
    ])
    def test_format_command(self, comm, arg_dict, result):
        assert self.ya.format_command(comm, **arg_dict) == result

    def test_format_command_handles_bool(self):
        # If command is false/true in yaml file, it gets coverted to False/True
        # which is bool object. format_command should handle this.
        assert self.ya.format_command(True) == 'true'
        assert self.ya.format_command(False) == 'false'

    def test_errors_pass(self):
        self.ya._fail_if = [{'cl': 'false'}, {'cl': 'grep'}]
        assert not self.ya.errors()

    def test_errors_fail(self):
        self.ya._fail_if = [{'cl': 'false'}, {'cl': 'true'}]
        assert self.ya.errors() == ['Cannot proceed because command returned 0: true']

    def test_errors_unknow_action(self):
        self.ya._fail_if = [{'foobar': 'not an action'}]
        assert not self.ya.errors()
        assert self.tlh.msgs == [('WARNING', 'Unkown action type foobar, skipping.')]

    def test_dependencies(self):
        self.ya._dependencies = {'rpm': ['foo', '@bar', 'baz']}
        flexmock(RPMHelper).should_receive('is_rpm_installed').and_return(False, True).one_by_one()
        flexmock(YUMHelper).should_receive('is_group_installed').and_return(False)
        flexmock(YUMHelper).should_receive('install').with_args('foo', '@bar')
        self.ya.dependencies()
