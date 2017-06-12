import json
from collections import OrderedDict

from graphql.execution import execute
from graphql.language.parser import parse
from graphql.type import (GraphQLArgument, GraphQLField,
                          GraphQLInputObjectField, GraphQLInputObjectType,
                          GraphQLInt, GraphQLList, GraphQLNonNull,
                          GraphQLObjectType, GraphQLSchema, GraphQLString)


def _test_schema(test_field):
    return GraphQLSchema(
        query=GraphQLObjectType(
            name='Query',
            fields={
                'test': test_field
            }
        )
    )


async def test_default_function_accesses_properties():
    schema = _test_schema(GraphQLField(GraphQLString))

    class source:
        test = 'testValue'

    result = await execute(schema, parse('{ test }'), source)
    assert not result.errors
    assert result.data == {'test': 'testValue'}


async def test_default_function_calls_methods():
    schema = _test_schema(GraphQLField(GraphQLString))

    class source:
        _secret = 'testValue'

        def test(self):
            return self._secret

    result = await execute(schema, parse('{ test }'), source())
    assert not result.errors
    assert result.data == {'test': 'testValue'}


async def test_uses_provided_resolve_function():
    def resolver(source, args, *_):
        return json.dumps([source, args], separators=(',', ':'))

    schema = _test_schema(GraphQLField(
        GraphQLString,
        args=OrderedDict([
            ('aStr', GraphQLArgument(GraphQLString)),
            ('aInt', GraphQLArgument(GraphQLInt)),
        ]),
        resolver=resolver
    ))

    result = await execute(schema, parse('{ test }'), None)
    assert not result.errors
    assert result.data == {'test': '[null,{}]'}

    result = await execute(schema, parse('{ test(aStr: "String!") }'), 'Source!')
    assert not result.errors
    assert result.data == {'test': '["Source!",{"aStr":"String!"}]'}

    result = await execute(schema, parse('{ test(aInt: -123, aStr: "String!",) }'), 'Source!')
    assert not result.errors
    assert result.data in [
        {'test': '["Source!",{"aStr":"String!","aInt":-123}]'},
        {'test': '["Source!",{"aInt":-123,"aStr":"String!"}]'}
    ]


async def test_handles_resolved_promises():
    async def resolver(source, args, *_):
        return 'foo'

    schema = _test_schema(GraphQLField(
        GraphQLString,
        resolver=resolver
    ))

    result = await execute(schema, parse('{ test }'), None)
    assert not result.errors
    assert result.data == {'test': 'foo'}


async def test_maps_argument_out_names_well():
    def resolver(source, args, *_):
        return json.dumps([source, args], separators=(',', ':'))

    schema = _test_schema(GraphQLField(
        GraphQLString,
        args=OrderedDict([
            ('aStr', GraphQLArgument(GraphQLString, out_name="a_str")),
            ('aInt', GraphQLArgument(GraphQLInt, out_name="a_int")),
        ]),
        resolver=resolver
    ))

    result = await execute(schema, parse('{ test }'), None)
    assert not result.errors
    assert result.data == {'test': '[null,{}]'}

    result = await execute(schema, parse('{ test(aStr: "String!") }'), 'Source!')
    assert not result.errors
    assert result.data == {'test': '["Source!",{"a_str":"String!"}]'}

    result = await execute(schema, parse('{ test(aInt: -123, aStr: "String!",) }'), 'Source!')
    assert not result.errors
    assert result.data in [
        {'test': '["Source!",{"a_str":"String!","a_int":-123}]'},
        {'test': '["Source!",{"a_int":-123,"a_str":"String!"}]'}
    ]


async def test_maps_argument_out_names_well_with_input():
    def resolver(source, args, *_):
        return json.dumps([source, args], separators=(',', ':'))


    TestInputObject = GraphQLInputObjectType('TestInputObject', lambda: OrderedDict([
        ('inputOne', GraphQLInputObjectField(GraphQLString, out_name="input_one")),
        ('inputRecursive', GraphQLInputObjectField(TestInputObject, out_name="input_recursive")),
    ]))

    schema = _test_schema(GraphQLField(
        GraphQLString,
        args=OrderedDict([
            ('aInput', GraphQLArgument(TestInputObject, out_name="a_input"))
        ]),
        resolver=resolver
    ))

    result = await execute(schema, parse('{ test }'), None)
    assert not result.errors
    assert result.data == {'test': '[null,{}]'}

    result = await execute(schema, parse('{ test(aInput: {inputOne: "String!"} ) }'), 'Source!')
    assert not result.errors
    assert result.data == {'test': '["Source!",{"a_input":{"input_one":"String!"}}]'}

    result = await execute(schema, parse('{ test(aInput: {inputRecursive:{inputOne: "SourceRecursive!"}} ) }'), 'Source!')
    assert not result.errors
    assert result.data == {
        'test': '["Source!",{"a_input":{"input_recursive":{"input_one":"SourceRecursive!"}}}]'
    }
