
# see also: https://realpython.com/the-minimum-viable-test-suite/

def initial_transform(data):
    """
    Flatten nested dicts
    """
    for item in list(data):
        if isinstance(item, dict):
            for key in item:
                data[key] = item[key]

    # call to mock:
    #outside_module.do_something()

    return data


def final_transform(transformed_data):
    """
    Transform address structures into a single structure
    """
    transformed_data['address'] = str.format(
        "{0}\n{1}, {2} {3}", transformed_data['street'], 
        transformed_data['state'], transformed_data['city'], 
        transformed_data['zip'])

    return transformed_data


def print_person(person_data):
    parents = "and".join(person_data['parents'])
    siblings = "and".join(person_data['siblings'])
    person_string = str.format(
        "Hello, my name is {0}, my siblings are {1}, "
        "my parents are {2}, and my mailing"
        "address is: \n{3}", person_data['name'], 
        parents, siblings, person_data['address'])
    print(person_string)


john_data = {
    'name': 'John Q. Public',
    'street': '123 Main St.',
    'city': 'Anytown',
    'state': 'FL',
    'zip': 99999,
    'relationships': {
        'siblings': ['Michael R. Public', 'Suzy Q. Public'],
        'parents': ['John Q. Public Sr.', 'Mary S. Public'],
    }
}

suzy_data = {
    'name': 'Suzy Q. Public',
    'street': '456 Broadway',
    'apt': '333',
    'city': 'Miami',
    'state': 'FL',
    'zip': 33333,
    'relationships': {
        'siblings': ['John Q. Public', 'Michael R. Public', 
                    'Thomas Z. Public'],
        'parents': ['John Q. Public Sr.', 'Mary S. Public'],
    }
}

inputs = [john_data, suzy_data]

for input_structure in inputs:
    initial_transformed = initial_transform(input_structure)
    final_transformed = final_transform(initial_transformed)
    print_person(final_transformed)


#--------------------------------
import pytest
import testapp as app


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


