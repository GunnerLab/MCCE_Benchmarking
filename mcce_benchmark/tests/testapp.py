#!/usr/bin/env python


# see: https://realpython.com/the-minimum-viable-test-suite/
#      https://pythontest.com/testing-argparse-apps/
#      https://goodresearch.dev/testing.html
#----------------------------------------------------------
import pytest


"""
#example
@pytest.fixture(params=['nodict', 'dict'])
def fixt_initial_transform_parameters(request):
    test_input = {
        'name': 'John Q. Public',
        'street': '123 Main St.',
        'city': 'Anytown',
        'state': 'FL',
        'zip': 99999,
    }
    expected_output = {
        'name': 'John Q. Public',
        'street': '123 Main St.',
        'city': 'Anytown',
        'state': 'FL',
        'zip': 99999,
    }

    if request.param == 'dict':
        test_input['relastionships'] = {
            'siblings': ['Michael R. Public', 'Suzy Q. Public'],
            'parents': ['John Q. Public Sr.', 'Mary S. Public'],
        }
        expected_output['siblings'] = ['Michael R. Public', 'Suzy Q. Public']
        expected_output['parents'] = ['John Q. Public Sr.', 'Mary S. Public']

    return test_input, expected_output


def test_initial_transform(fixt_initial_transform_parameters):
    test_input = fixt_initial_transform_parameters[0]
    expected_output = fixt_initial_transform_parameters[1]
    assert app.initial_transform(test_input) == expected_output


# fixture with mock:
@pytest.fixture(params=['nodict', 'dict'])
def fixtm_initial_transform_parameters(request, mocker):
    [...]
    mocker.patch.object(outside_module, 'do_something')
    mocker.do_something.return_value(1)
    [...]
"""
